"""
mirrorz/gui.py
================================================================================
Tkinter desktop GUI for MirrorZ-Hecras.

LAYOUT
--------------------------------------------------------------------------------
Menu bar: File / Run / Tools / Help
Left pane: project tree (reaches -> cross-sections, flow plans)
Right tabs:
    1. Cross-Section   - edit stations/elevations, live preview plot
    2. Profile         - run the solver and see water surface plot
    3. Summary         - CSV-style text output of last run
    4. Companion       - guided wizard + glossary

PERSISTENT SETTINGS (new in 0.2)
--------------------------------------------------------------------------------
The app loads mirrorz/settings.py's AppSettings at startup and applies them
to the numeric modules before anything runs. Tools -> Settings... opens a
dialog; saving applies immediately AND persists to the per-user config dir.
Window size and the recent-file list survive restarts the same way.

HIGHLIGHTED TWEAK AREAS
--------------------------------------------------------------------------------
  ### TWEAK: WINDOW ###     Window size, title.
  ### TWEAK: COLORS ###     Theme bits (mostly delegated to matplotlib).

This file is intentionally longer than the others because GUI code is
inherently wordy. Keep an eye on the big section banners (====...====) for
navigation.
================================================================================
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from typing import List, Optional

# Matplotlib embedding. We pick TkAgg BEFORE importing our plotting module
# (which respects an already-chosen backend - see plotting.py's WARN note).
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from . import __version__
from .project import Project, FlowPlan, default_project
from .geometry import CrossSection, Reach
from .solver import solve_profile, ProfileResult, clear_critical_cache
from .settings import AppSettings
from .admin import AdminState, EDITIONS, THEMES, EDITION_PRICES
from . import plotting as pl
from . import companion as helper
from . import analyzer
from . import hydraulics as hy


# ### TWEAK: WINDOW ###
WINDOW_TITLE   = f"MirrorZ-Hecras {__version__} — open-channel hydraulics, for learning"
WINDOW_SIZE    = "1180x740"   # used only when settings carry no saved geometry


class App(tk.Tk):
    """Main application window."""

    # =========================================================================
    # Construction
    # =========================================================================
    def __init__(self) -> None:
        super().__init__()
        self.title(WINDOW_TITLE)

        # Load persisted user preferences FIRST so tolerances/units are live
        # before the default project (which solves normal depth) is built.
        self.settings = AppSettings.load()
        self.settings.apply()
        # Admin state (edition, theme, branding) - separate file so personal
        # design choices don't pollute project portability.
        self.admin = AdminState.load()
        pl.apply_palette(self.admin.palette(), self.admin.header_caption())
        self.geometry(self.settings.window_geometry or WINDOW_SIZE)
        # Save settings (incl. window geometry) when the window closes.
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.project: Project = default_project()
        self.project.unit_system = self.settings.unit_system
        self.project.apply_units()
        self.last_result: Optional[ProfileResult] = None

        self._build_menu()
        self._build_body()
        self._refresh_tree()
        if self.settings.show_welcome:
            self._show_welcome()

    def _on_close(self) -> None:
        """Persist window geometry + recent files, then quit."""
        try:
            self.settings.window_geometry = self.geometry()
            self.settings.save()
        except Exception:
            pass   # never block exit over a preferences write
        self.destroy()

    # =========================================================================
    # Menu bar
    # =========================================================================
    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Project",       command=self.new_project)
        file_menu.add_command(label="Open…",             command=self.open_project)
        # Recent-files submenu is rebuilt every time a file is opened/saved.
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Open Recent",       menu=self.recent_menu)
        self._rebuild_recent_menu()
        file_menu.add_command(label="Save As…",          command=self.save_project)
        file_menu.add_separator()
        file_menu.add_command(label="Export Summary CSV…", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Quit",              command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="Compute Profile",    command=self.run_profile)
        run_menu.add_command(label="Rating Curve…",      command=self.run_rating)
        run_menu.add_command(label="Freeboard Check",    command=self.run_freeboard)
        menubar.add_cascade(label="Run", menu=run_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Settings…",        command=self.open_settings)
        tools_menu.add_command(label="Inspect Project",  command=self.run_inspect)
        tools_menu.add_command(label="Units: Toggle SI / US", command=self.toggle_units)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Companion: Welcome",    command=self._show_welcome)
        help_menu.add_command(label="Explain Manning",       command=lambda: self._explain("manning"))
        help_menu.add_command(label="Explain Froude",        command=lambda: self._explain("froude"))
        help_menu.add_command(label="Explain Critical Depth",command=lambda: self._explain("critical_depth"))
        help_menu.add_command(label="Explain Standard Step", command=lambda: self._explain("standard_step"))
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    # =========================================================================
    # Main body: sidebar + tabbed notebook
    # =========================================================================
    def _build_body(self) -> None:
        root = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        root.pack(fill=tk.BOTH, expand=True)

        # ---- Sidebar ------------------------------------------------------
        left = ttk.Frame(root, width=280)
        self.tree = ttk.Treeview(left)
        self.tree.heading("#0", text="Project")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        side_btns = ttk.Frame(left)
        ttk.Button(side_btns, text="Add XS",    command=self.add_xs).pack(side=tk.LEFT)
        ttk.Button(side_btns, text="Del XS",    command=self.del_xs).pack(side=tk.LEFT)
        ttk.Button(side_btns, text="Add Flow",  command=self.add_flow).pack(side=tk.LEFT)
        side_btns.pack(fill=tk.X)
        root.add(left, weight=1)

        # ---- Notebook -----------------------------------------------------
        nb = ttk.Notebook(root)
        self.tab_xs       = ttk.Frame(nb); nb.add(self.tab_xs,      text="Cross-Section")
        self.tab_profile  = ttk.Frame(nb); nb.add(self.tab_profile, text="Profile")
        self.tab_summary  = ttk.Frame(nb); nb.add(self.tab_summary, text="Summary")
        self.tab_helper   = ttk.Frame(nb); nb.add(self.tab_helper,  text="Companion")
        self.tab_admin    = ttk.Frame(nb); nb.add(self.tab_admin,   text="Admin")
        root.add(nb, weight=4)
        self.nb = nb

        self._build_xs_tab()
        self._build_profile_tab()
        self._build_summary_tab()
        self._build_helper_tab()
        self._build_admin_tab()

    # ---------------- Cross-section tab ---------------------------------------
    def _build_xs_tab(self) -> None:
        top = ttk.Frame(self.tab_xs)
        top.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(top, text="Name:").grid(row=0, column=0, sticky="w")
        self.xs_name_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.xs_name_var, width=18)\
            .grid(row=0, column=1, sticky="w")
        ttk.Label(top, text="River Station:").grid(row=0, column=2, sticky="w", padx=(10,0))
        self.xs_rs_var = tk.DoubleVar()
        ttk.Entry(top, textvariable=self.xs_rs_var, width=8)\
            .grid(row=0, column=3, sticky="w")
        ttk.Label(top, text="n channel:").grid(row=0, column=4, sticky="w", padx=(10,0))
        self.xs_n_var = tk.DoubleVar()
        ttk.Entry(top, textvariable=self.xs_n_var, width=7)\
            .grid(row=0, column=5, sticky="w")
        ttk.Button(top, text="Apply Header", command=self._apply_xs_header)\
            .grid(row=0, column=6, padx=8)

        # Table of points.
        mid = ttk.Frame(self.tab_xs)
        mid.pack(side=tk.TOP, fill=tk.BOTH, expand=False)
        self.point_tree = ttk.Treeview(mid, columns=("station","elev"), show="headings", height=8)
        self.point_tree.heading("station", text="Station")
        self.point_tree.heading("elev",    text="Elevation")
        self.point_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn = ttk.Frame(mid)
        ttk.Button(btn, text="Add Pt",    command=self._pt_add).pack(fill=tk.X)
        ttk.Button(btn, text="Edit Pt",   command=self._pt_edit).pack(fill=tk.X)
        ttk.Button(btn, text="Remove Pt", command=self._pt_remove).pack(fill=tk.X)
        ttk.Button(btn, text="Refresh",   command=self._refresh_xs_plot).pack(fill=tk.X, pady=(6,0))
        btn.pack(side=tk.LEFT, fill=tk.Y, padx=6)

        # Plot.
        self.xs_fig = Figure(figsize=pl.XS_FIGSIZE)
        self.xs_ax  = self.xs_fig.add_subplot(111)
        self.xs_canvas = FigureCanvasTkAgg(self.xs_fig, master=self.tab_xs)
        self.xs_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # ---------------- Profile tab ---------------------------------------------
    def _build_profile_tab(self) -> None:
        top = ttk.Frame(self.tab_profile)
        top.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(top, text="Flow:").grid(row=0, column=0, sticky="w")
        self.flow_combo = ttk.Combobox(top, state="readonly", width=28)
        self.flow_combo.grid(row=0, column=1, sticky="w")
        ttk.Button(top, text="Run", command=self.run_profile).grid(row=0, column=2, padx=8)
        self.profile_status = tk.StringVar(value="(not run)")
        ttk.Label(top, textvariable=self.profile_status).grid(row=0, column=3, sticky="w")

        self.prof_fig = Figure(figsize=pl.PROFILE_FIGSIZE)
        self.prof_ax  = self.prof_fig.add_subplot(111)
        self.prof_canvas = FigureCanvasTkAgg(self.prof_fig, master=self.tab_profile)
        self.prof_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # ---------------- Summary tab ---------------------------------------------
    def _build_summary_tab(self) -> None:
        self.summary_text = tk.Text(self.tab_summary, wrap=tk.NONE, font=("Courier", 10))
        sb = ttk.Scrollbar(self.tab_summary, orient=tk.VERTICAL, command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # ---------------- Companion tab -------------------------------------------
    def _build_helper_tab(self) -> None:
        self.helper_text = tk.Text(self.tab_helper, wrap=tk.WORD, font=("Helvetica", 11))
        self.helper_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        btn = ttk.Frame(self.tab_helper)
        for topic in ("manning", "froude", "critical_depth",
                      "normal_depth", "standard_step", "contraction_expansion"):
            ttk.Button(btn, text=topic, command=lambda t=topic: self._explain(t))\
                .pack(side=tk.LEFT, padx=2)
        btn.pack(side=tk.BOTTOM, fill=tk.X)

    # ---------------- Admin tab -----------------------------------------------
    # The admin tab is a vertically-stacked stack of LabelFrame "cards":
    #   1. Edition + License        -> commercial gating, telemetry consent
    #   2. Design Choices (Theme)   -> palette picker with live preview
    #   3. Branding (Classroom)     -> institution/instructor/course strings
    #   4. About                    -> version, config dir, legal links
    # Cards keep each concern visually self-contained.
    def _build_admin_tab(self) -> None:
        wrap = ttk.Frame(self.tab_admin, padding=12)
        wrap.pack(fill=tk.BOTH, expand=True)

        # -- 1. Edition card -------------------------------------------------
        ed = ttk.LabelFrame(wrap, text="Edition & License", padding=8)
        ed.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(ed, text=f"Current edition: ").grid(row=0, column=0, sticky="w")
        self._edition_label = ttk.Label(ed, text="—", font=("Helvetica", 11, "bold"))
        self._edition_label.grid(row=0, column=1, sticky="w")
        # Prices shown for transparency - users can see what each unlocks
        # without leaving the app, which improves conversion.
        for r, (eid, blurb) in enumerate(EDITION_PRICES.items(), start=1):
            ttk.Label(ed, text=f"  • {eid}:", foreground="#555")\
                .grid(row=r, column=0, sticky="w")
            ttk.Label(ed, text=blurb, foreground="#555")\
                .grid(row=r, column=1, sticky="w")

        key_row = ttk.Frame(ed)
        key_row.grid(row=len(EDITION_PRICES)+1, column=0, columnspan=3,
                     sticky="we", pady=(8, 0))
        ttk.Label(key_row, text="License key:").pack(side=tk.LEFT)
        self.license_var = tk.StringVar(value=self.admin.license_key)
        ttk.Entry(key_row, textvariable=self.license_var, width=22)\
            .pack(side=tk.LEFT, padx=4)
        ttk.Button(key_row, text="Activate",   command=self._activate_license)\
            .pack(side=tk.LEFT)
        ttk.Button(key_row, text="Deactivate", command=self._deactivate_license)\
            .pack(side=tk.LEFT, padx=4)
        ttk.Button(key_row, text="Buy…",       command=self._open_buy_link)\
            .pack(side=tk.LEFT)
        self._license_status = ttk.Label(ed, text="", foreground="#0a7")
        self._license_status.grid(row=len(EDITION_PRICES)+2, column=0,
                                  columnspan=3, sticky="w")

        # -- 2. Design choices -----------------------------------------------
        th = ttk.LabelFrame(wrap, text="Design Choices (Theme)", padding=8)
        th.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(th, text="Plot theme:").grid(row=0, column=0, sticky="w")
        self.theme_var = tk.StringVar(value=self.admin.theme)
        cb = ttk.Combobox(th, textvariable=self.theme_var, state="readonly",
                          values=list(THEMES.keys()), width=14)
        cb.grid(row=0, column=1, sticky="w", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._apply_theme())
        ttk.Label(th, text="(applies on next plot redraw)",
                  foreground="#777").grid(row=0, column=2, sticky="w")

        # -- 3. Branding (classroom edition only - widgets stay disabled
        #    until the user activates a classroom license) ------------------
        br = ttk.LabelFrame(wrap, text="Classroom Branding", padding=8)
        br.pack(fill=tk.X, pady=(0, 8))
        self.brand_institution = tk.StringVar(value=self.admin.institution)
        self.brand_instructor  = tk.StringVar(value=self.admin.instructor)
        self.brand_course      = tk.StringVar(value=self.admin.course_code)
        rows = (("Institution:", self.brand_institution),
                ("Instructor:",  self.brand_instructor),
                ("Course code:", self.brand_course))
        self._brand_entries = []
        for r, (label, var) in enumerate(rows):
            ttk.Label(br, text=label).grid(row=r, column=0, sticky="w", pady=2)
            e = ttk.Entry(br, textvariable=var, width=36)
            e.grid(row=r, column=1, sticky="w", padx=4)
            self._brand_entries.append(e)
        ttk.Button(br, text="Apply Branding",
                   command=self._apply_branding).grid(row=len(rows), column=1,
                                                       sticky="w", pady=(6,0))
        self._brand_locked_lbl = ttk.Label(br, text="", foreground="#a60")
        self._brand_locked_lbl.grid(row=len(rows)+1, column=0, columnspan=2,
                                     sticky="w")

        # -- 4. Telemetry consent (default OFF, even with the toggle) -------
        tel = ttk.LabelFrame(wrap, text="Privacy", padding=8)
        tel.pack(fill=tk.X, pady=(0, 8))
        self.tel_var = tk.BooleanVar(value=self.admin.telemetry_optin)
        ttk.Checkbutton(tel, variable=self.tel_var,
            text="Anonymous usage analytics (currently does NOTHING - "
                 "we have no endpoint; consent is stored for the future)",
            command=self._save_telemetry).pack(anchor="w")

        # -- 5. About / legal links -----------------------------------------
        ab = ttk.LabelFrame(wrap, text="About", padding=8)
        ab.pack(fill=tk.X, pady=(0, 8))
        from .settings import config_dir
        ttk.Label(ab, text=f"Version: {__version__}").pack(anchor="w")
        ttk.Label(ab, text=f"Config:  {config_dir()}",
                  foreground="#555").pack(anchor="w")
        ttk.Label(ab,
            text="Educational tool — NOT certified for regulatory or "
                 "life-safety engineering. See EULA.",
            foreground="#a40", wraplength=720).pack(anchor="w", pady=(6, 0))

        self._refresh_admin_view()

    def _refresh_admin_view(self) -> None:
        self._edition_label.config(text=self.admin.edition.upper())
        # Gate branding entries by edition.
        branding_unlocked = self.admin.feature_enabled("branding")
        state = ("normal" if branding_unlocked else "disabled")
        for e in self._brand_entries:
            e.config(state=state)
        self._brand_locked_lbl.config(
            text="" if branding_unlocked
                 else "Branding unlocks with the Classroom edition.")

    # ---- Admin actions ---------------------------------------------------
    def _activate_license(self) -> None:
        msg = self.admin.apply_license_key(self.license_var.get())
        ok = self.admin.edition != "free"
        self._license_status.config(text=msg,
            foreground="#0a7" if ok else "#c33")
        self._refresh_admin_view()

    def _deactivate_license(self) -> None:
        self.admin.clear_license()
        self.license_var.set("")
        self._license_status.config(text="Deactivated; using Free edition.",
                                     foreground="#555")
        self._refresh_admin_view()

    def _open_buy_link(self) -> None:
        # We don't ship a sales URL yet (rename pending - see docs/pricing.md),
        # so we keep the button honest and informative instead of pointing
        # nowhere. This swaps to a real URL on launch day.
        messagebox.showinfo("Buy",
            "The store URL will appear here on launch.\n\n"
            "Until then: build from source (MIT) or DM the maintainer.")

    def _apply_theme(self) -> None:
        self.admin.theme = self.theme_var.get()
        pl.apply_palette(self.admin.palette(), self.admin.header_caption())
        self.admin.save()
        # Force a redraw of whatever's currently visible.
        self._refresh_xs_plot()
        if self.last_result is not None and self.project.reaches:
            self.prof_ax.clear()
            pl.profile_figure(self.last_result,
                              self.project.reaches[0].cross_sections,
                              ax=self.prof_ax)
            self.prof_canvas.draw()

    def _apply_branding(self) -> None:
        self.admin.institution = self.brand_institution.get()
        self.admin.instructor  = self.brand_instructor.get()
        self.admin.course_code = self.brand_course.get()
        self.admin.save()
        pl.apply_palette(self.admin.palette(), self.admin.header_caption())
        self._refresh_xs_plot()

    def _save_telemetry(self) -> None:
        self.admin.telemetry_optin = bool(self.tel_var.get())
        self.admin.save()

    # =========================================================================
    # Project tree handling
    # =========================================================================
    def _refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        root = self.tree.insert("", tk.END, text=self.project.name, open=True,
                                values=("project",))
        for ri, reach in enumerate(self.project.reaches):
            rnode = self.tree.insert(root, tk.END, text=f"Reach: {reach.name}",
                                     open=True, values=(f"reach:{ri}",))
            for xi, xs in enumerate(reach.cross_sections):
                self.tree.insert(rnode, tk.END,
                    text=f"{xs.name}  (RS {xs.river_station:.1f})",
                    values=(f"xs:{ri}:{xi}",))
        fnode = self.tree.insert(root, tk.END, text="Flows", open=True, values=("flows",))
        for fi, fp in enumerate(self.project.flows):
            self.tree.insert(fnode, tk.END, text=f"{fp.name} (Q={fp.discharge})",
                             values=(f"flow:{fi}",))
        # refresh flow combo too
        self.flow_combo["values"] = [f.name for f in self.project.flows]
        if self.project.flows and not self.flow_combo.get():
            self.flow_combo.current(0)

    def _on_tree_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0]).get("values") or []
        if not vals:
            return
        tag = str(vals[0])
        if tag.startswith("xs:"):
            _, ri, xi = tag.split(":")
            self._load_xs(int(ri), int(xi))
            self.nb.select(self.tab_xs)

    # =========================================================================
    # Cross-section editing
    # =========================================================================
    def _load_xs(self, reach_idx: int, xs_idx: int) -> None:
        reach = self.project.reaches[reach_idx]
        xs = reach.cross_sections[xs_idx]
        self.selected_xs = (reach_idx, xs_idx)
        self.xs_name_var.set(xs.name)
        self.xs_rs_var.set(xs.river_station)
        self.xs_n_var.set(xs.n_channel)
        self._reload_points()
        self._refresh_xs_plot()

    def _reload_points(self) -> None:
        self.point_tree.delete(*self.point_tree.get_children())
        if not hasattr(self, "selected_xs"):
            return
        ri, xi = self.selected_xs
        xs = self.project.reaches[ri].cross_sections[xi]
        for i, (s, z) in enumerate(zip(xs.stations, xs.elevations)):
            self.point_tree.insert("", tk.END, iid=str(i),
                                   values=(f"{s:.3f}", f"{z:.3f}"))

    def _apply_xs_header(self) -> None:
        if not hasattr(self, "selected_xs"):
            return
        ri, xi = self.selected_xs
        xs = self.project.reaches[ri].cross_sections[xi]
        xs.name = self.xs_name_var.get() or xs.name
        xs.river_station = float(self.xs_rs_var.get())
        xs.n_channel = float(self.xs_n_var.get())
        clear_critical_cache()   # n/name changed; drop stale cached values
        self.project.reaches[ri].sort_upstream()
        self._refresh_tree()
        self._refresh_xs_plot()

    def _pt_add(self) -> None:
        s = simpledialog.askfloat("New point", "Station:", parent=self)
        if s is None: return
        z = simpledialog.askfloat("New point", "Elevation:", parent=self)
        if z is None: return
        ri, xi = self.selected_xs
        xs = self.project.reaches[ri].cross_sections[xi]
        xs.stations.append(s); xs.elevations.append(z)
        # Re-sort.
        pts = sorted(zip(xs.stations, xs.elevations))
        xs.stations  = [p[0] for p in pts]
        xs.elevations= [p[1] for p in pts]
        clear_critical_cache()   # shape changed -> cached critical depth is stale
        self._reload_points(); self._refresh_xs_plot()

    def _pt_edit(self) -> None:
        sel = self.point_tree.selection()
        if not sel: return
        ri, xi = self.selected_xs
        xs = self.project.reaches[ri].cross_sections[xi]
        i = int(sel[0])
        s = simpledialog.askfloat("Edit point", "Station:",
                                   initialvalue=xs.stations[i], parent=self)
        if s is None: return
        z = simpledialog.askfloat("Edit point", "Elevation:",
                                   initialvalue=xs.elevations[i], parent=self)
        if z is None: return
        xs.stations[i] = s; xs.elevations[i] = z
        pts = sorted(zip(xs.stations, xs.elevations))
        xs.stations  = [p[0] for p in pts]
        xs.elevations= [p[1] for p in pts]
        clear_critical_cache()
        self._reload_points(); self._refresh_xs_plot()

    def _pt_remove(self) -> None:
        sel = self.point_tree.selection()
        if not sel: return
        ri, xi = self.selected_xs
        xs = self.project.reaches[ri].cross_sections[xi]
        i = int(sel[0])
        if len(xs.stations) <= 3:
            messagebox.showwarning("Cannot remove",
                "A cross-section needs at least 3 points.")
            return
        xs.stations.pop(i); xs.elevations.pop(i)
        clear_critical_cache()
        self._reload_points(); self._refresh_xs_plot()

    def _refresh_xs_plot(self) -> None:
        if not hasattr(self, "selected_xs"):
            return
        ri, xi = self.selected_xs
        xs = self.project.reaches[ri].cross_sections[xi]
        self.xs_ax.clear()
        # Show WSE from the most-recent run if the section is in it.
        wse = None
        if self.last_result is not None:
            for s in self.last_result.sections:
                if s.name == xs.name:
                    wse = s.wse; break
        pl.cross_section_figure(xs, wse=wse, ax=self.xs_ax)
        self.xs_canvas.draw()

    # =========================================================================
    # Side buttons
    # =========================================================================
    def add_xs(self) -> None:
        if not self.project.reaches:
            self.project.add_reach(Reach("Main Reach"))
        reach = self.project.reaches[0]
        base = reach.cross_sections[-1] if reach.cross_sections else None
        name = simpledialog.askstring("New XS", "Name:", parent=self) or f"XS-{len(reach)+1}"
        rs = simpledialog.askfloat("New XS", "River station:",
                initialvalue=(base.river_station + 100.0) if base else 0.0,
                parent=self)
        if rs is None: return
        # Reasonable default shape: copy the last one, or a flat trapezoid.
        if base is not None:
            xs = CrossSection(
                name=name, river_station=rs,
                stations=list(base.stations), elevations=list(base.elevations),
                left_bank=base.left_bank, right_bank=base.right_bank,
                n_channel=base.n_channel, n_left=base.n_left, n_right=base.n_right,
                reach_length_channel=base.reach_length_channel,
            )
        else:
            xs = CrossSection(name=name, river_station=rs,
                              stations=[0, 5, 15, 20], elevations=[3, 0, 0, 3])
        reach.add(xs)
        self._refresh_tree()

    def del_xs(self) -> None:
        if not hasattr(self, "selected_xs"):
            return
        ri, xi = self.selected_xs
        if messagebox.askyesno("Delete XS", "Remove the selected cross-section?"):
            self.project.reaches[ri].cross_sections.pop(xi)
            self._refresh_tree()

    def add_flow(self) -> None:
        name = simpledialog.askstring("New flow", "Plan name:", parent=self)
        if not name: return
        q = simpledialog.askfloat("New flow", "Discharge:",
                                   initialvalue=20.0, parent=self)
        if q is None: return
        regime = simpledialog.askstring("New flow",
            "Regime (subcritical / supercritical):",
            initialvalue="subcritical", parent=self) or "subcritical"
        wse = helper.recommend_boundary(self.project, q, regime)
        self.project.add_flow(FlowPlan(name=name, discharge=q,
                                       boundary_wse=wse, regime=regime))
        self._refresh_tree()

    # =========================================================================
    # Menu actions
    # =========================================================================
    def new_project(self) -> None:
        if not messagebox.askyesno("New project",
                "Discard current project and start a new default one?"):
            return
        self.project = default_project()
        self.project.apply_units()
        self.last_result = None
        self._refresh_tree()

    def open_project(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON","*.json"), ("All","*.*")])
        if not path: return
        self._open_path(path)

    def _open_path(self, path: str) -> None:
        """Shared by Open… and the recent-files menu."""
        try:
            self.project = Project.load(path)
            self.project.apply_units()
        except Exception as e:
            messagebox.showerror("Open failed", str(e)); return
        clear_critical_cache()           # new geometry invalidates the cache
        self.last_result = None
        self.settings.remember_file(path)
        self.settings.save()
        self._rebuild_recent_menu()
        self._refresh_tree()

    def _rebuild_recent_menu(self) -> None:
        self.recent_menu.delete(0, tk.END)
        if not self.settings.recent_files:
            self.recent_menu.add_command(label="(empty)", state=tk.DISABLED)
            return
        for p in self.settings.recent_files:
            # Show just the file name, keep the full path in the callback.
            self.recent_menu.add_command(
                label=os.path.basename(p),
                command=lambda path=p: self._open_path(path))

    def save_project(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".json",
                filetypes=[("JSON","*.json")])
        if not path: return
        try:
            self.project.save(path)
            self.settings.remember_file(path)
            self.settings.save()
            self._rebuild_recent_menu()
            messagebox.showinfo("Saved", f"Project saved to\n{path}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def export_csv(self) -> None:
        """Write the last run's summary table to a CSV file."""
        if not self.admin.feature_enabled("csv_export"):
            messagebox.showinfo("Pro feature",
                "CSV export is included with the Pro edition.\n\n"
                "Open the Admin tab to enter a license key, or copy the "
                "Summary tab text manually in the free edition.")
            return
        if self.last_result is None:
            messagebox.showinfo("Run first", "Compute a profile first."); return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                filetypes=[("CSV","*.csv")])
        if not path: return
        try:
            with open(path, "w") as fh:
                fh.write(analyzer.summarize(self.last_result) + "\n")
            messagebox.showinfo("Exported", f"Summary written to\n{path}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def run_profile(self) -> None:
        if not self.project.flows:
            messagebox.showwarning("No flow", "Define a flow plan first (side panel → Add Flow)."); return
        fi = max(self.flow_combo.current(), 0)
        flow = self.project.flows[fi]
        reach = self.project.reaches[0]
        try:
            result = solve_profile(reach, flow.discharge, flow.boundary_wse,
                                   regime=flow.regime)
        except Exception as e:
            messagebox.showerror("Solver error", str(e)); return
        self.last_result = result
        # Redraw
        self.prof_ax.clear()
        pl.profile_figure(result, reach.cross_sections, ax=self.prof_ax)
        self.prof_canvas.draw()
        self._refresh_xs_plot()
        self.profile_status.set(
            f"{len(result.sections)} sections, "
            f"{sum(1 for s in result.sections if s.converged)} converged."
        )
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, analyzer.summarize(result) + "\n")
        if result.messages:
            self.summary_text.insert(tk.END, "\n-- solver messages --\n")
            for m in result.messages:
                self.summary_text.insert(tk.END, f"  * {m}\n")
        hints = helper.next_steps(result)
        self.summary_text.insert(tk.END, "\n-- companion --\n")
        for h in hints:
            self.summary_text.insert(tk.END, f"  [{h.level}] {h.message}\n")

    def run_rating(self) -> None:
        if not self.project.reaches or not self.project.flows:
            messagebox.showwarning("Need a project",
                "Add at least one reach and one flow plan first."); return
        q_min = simpledialog.askfloat("Rating", "Min Q:",  initialvalue=1.0, parent=self) or 1.0
        q_max = simpledialog.askfloat("Rating", "Max Q:",  initialvalue=50.0, parent=self) or 50.0
        points = analyzer.rating_curve(self.project, reach_index=0, xs_index=0,
                                       q_min=q_min, q_max=q_max)
        top = tk.Toplevel(self); top.title("Rating curve")
        fig = Figure(figsize=pl.XS_FIGSIZE)
        ax = fig.add_subplot(111)
        pl.rating_figure(points, xs_name=self.project.reaches[0].cross_sections[0].name, ax=ax)
        FigureCanvasTkAgg(fig, master=top).get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def run_freeboard(self) -> None:
        if self.last_result is None:
            messagebox.showinfo("Run first", "Compute a profile first."); return
        rows = analyzer.freeboard_check(self.last_result, self.project.reaches[0])
        top = tk.Toplevel(self); top.title("Freeboard check")
        tv = ttk.Treeview(top, columns=("wse","tob","fb","ok"), show="headings")
        for c, t in zip(("wse","tob","fb","ok"),
                        ("WSE","Top of bank","Freeboard","OK?")):
            tv.heading(c, text=t)
        for r in rows:
            tv.insert("", tk.END, text=r.xs_name,
                      values=(f"{r.wse:.2f}", f"{r.top_of_bank:.2f}",
                              f"{r.freeboard:.2f}", "yes" if r.ok else "NO"))
        tv.pack(fill=tk.BOTH, expand=True)

    def run_inspect(self) -> None:
        hints = helper.inspect_project(self.project)
        top = tk.Toplevel(self); top.title("Project inspection")
        txt = tk.Text(top, wrap=tk.WORD, width=80, height=20)
        if not hints:
            txt.insert(tk.END, "No issues found.")
        for h in hints:
            txt.insert(tk.END, f"[{h.level}] {h.message}\n")
        txt.pack(fill=tk.BOTH, expand=True)

    def toggle_units(self) -> None:
        new = "US" if self.project.unit_system == "SI" else "SI"
        self.project.unit_system = new
        self.project.apply_units()
        self.settings.unit_system = new      # persist the preference too
        self.settings.save()
        clear_critical_cache()               # g changed -> critical depth changed
        messagebox.showinfo("Units",
            f"Unit system set to {new}. NOTE: existing numeric geometry "
            f"was NOT converted; you're interpreting the same numbers in "
            f"new units. Convert manually if needed.")

    # =========================================================================
    # Settings dialog (Tools -> Settings…)
    # =========================================================================
    def open_settings(self) -> None:
        """
        Modal preferences dialog. Each row edits one AppSettings field; OK
        validates, applies to the live numeric modules, and persists to disk.

        ### LEARN ###: we deliberately validate on OK rather than on every
        keystroke - simpler code, and partially-typed numbers ("0.") never
        trigger spurious errors.
        """
        s = self.settings
        dlg = tk.Toplevel(self)
        dlg.title("Settings")
        dlg.transient(self)       # stay on top of the main window
        dlg.grab_set()            # modal: block main-window input until closed
        frame = ttk.Frame(dlg, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        # -- row helpers ----------------------------------------------------
        unit_var   = tk.StringVar(value=s.unit_system)
        tol_var    = tk.StringVar(value=str(s.wse_tolerance))
        iters_var  = tk.StringVar(value=str(s.max_step_iters))
        fric_var   = tk.StringVar(value=s.friction_method)
        fb_var     = tk.StringVar(value=str(s.freeboard_req))
        wel_var    = tk.BooleanVar(value=s.show_welcome)

        rows = [
            ("Unit system",
             ttk.Combobox(frame, textvariable=unit_var, state="readonly",
                          values=("SI", "US"), width=12),
             "k=1.0 & g=9.807 (SI) vs k=1.486 & g=32.174 (US)"),
            ("WSE tolerance",
             ttk.Entry(frame, textvariable=tol_var, width=12),
             "Energy-balance convergence, in m/ft (HEC-RAS: 0.01 ft)"),
            ("Max iterations / step",
             ttk.Entry(frame, textvariable=iters_var, width=12),
             "Per-section cap before flagging non-convergence"),
            ("Friction averaging",
             ttk.Combobox(frame, textvariable=fric_var, state="readonly",
                          values=("average", "harmonic",
                                  "geometric", "conveyance"), width=12),
             "How S_f is averaged between two sections"),
            ("Required freeboard",
             ttk.Entry(frame, textvariable=fb_var, width=12),
             "Pass/fail threshold for the Freeboard Check (m/ft)"),
            ("Show welcome at startup",
             ttk.Checkbutton(frame, variable=wel_var),
             "Open the Companion tab with the intro text"),
        ]
        for r, (label, widget, hint) in enumerate(rows):
            ttk.Label(frame, text=label + ":").grid(row=r, column=0,
                                                    sticky="w", pady=3)
            widget.grid(row=r, column=1, sticky="w", padx=6)
            ttk.Label(frame, text=hint, foreground="#666",
                      font=("Helvetica", 9)).grid(row=r, column=2, sticky="w")

        def on_ok() -> None:
            try:
                s.unit_system     = unit_var.get()
                s.wse_tolerance   = float(tol_var.get())
                s.max_step_iters  = int(iters_var.get())
                s.friction_method = fric_var.get()
                s.freeboard_req   = float(fb_var.get())
                s.show_welcome    = bool(wel_var.get())
            except ValueError as e:
                messagebox.showerror("Invalid value", str(e), parent=dlg)
                return
            s.sanitize()          # clamp anything out of range
            s.apply()             # live immediately, no restart needed
            s.save()              # persist to the per-user config dir
            self.project.unit_system = s.unit_system
            self.project.apply_units()
            clear_critical_cache()
            dlg.destroy()

        btns = ttk.Frame(frame)
        ttk.Button(btns, text="OK",     command=on_ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT)
        btns.grid(row=len(rows), column=0, columnspan=3, pady=(12, 0))

    # =========================================================================
    # Companion text
    # =========================================================================
    def _show_welcome(self) -> None:
        self.nb.select(self.tab_helper)
        self.helper_text.delete("1.0", tk.END)
        self.helper_text.insert(tk.END, helper.welcome())

    def _explain(self, topic: str) -> None:
        self.nb.select(self.tab_helper)
        self.helper_text.delete("1.0", tk.END)
        self.helper_text.insert(tk.END, f"# {topic}\n\n")
        self.helper_text.insert(tk.END, helper.explain(topic))


def launch() -> None:
    App().mainloop()
