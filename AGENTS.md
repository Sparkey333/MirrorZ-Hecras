# Agent guide — MirrorZ-Hecras

Educational Python mirror of HEC-RAS 1-D steady flow. Inspired by the
automation workflow in *Breaking the HEC-RAS Code* (Goodell), but **no**
Windows COM / HECRASController dependency.

## Cloud agents on this repo

| Agent | URL | Role |
|---|---|---|
| Breaking HECRAS project environment | https://cursor.com/agents/bc-b6ce5c8d-f0ff-4a0c-8f73-395e1e863315 | This workstream: materials + forward plan |
| Development environment setup | https://cursor.com/agents/bc-d2e32d12-4e20-4f95-947c-5efa3abe75a1 | Sibling: deps, GUI demo, env bootstrap |

Both share `https://github.com/sparkey333/mirrorz-hecras`. Prefer continuing
from the feature branch that already has the Python engine
(`claude/hec-ras-modeling-tool-KNK6Y` / `cursor/breaking-hecras-setup-3315`)
rather than empty `main`.

## Bootstrap (cloud or local)

```bash
sudo apt-get update && sudo apt-get install -y python3-venv python3-tk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest reportlab   # tests + PDF reports
pytest -q
python main.py --run examples/simple_channel.json
```

GUI (needs display / VNC): `python main.py`

## Local reference materials

Your Mac Downloads bundle is **not** visible to cloud VMs:

```
/Users/ansom/Downloads/HECRAS-Breaking Hecras Code
```

Sync it with `./scripts/sync_local_reference.sh` on the Mac into
`docs/reference/` (gitignored except README). See
[`docs/reference/README.md`](docs/reference/README.md) and
[`docs/FORWARD_PLAN.md`](docs/FORWARD_PLAN.md).

Do **not** commit the book PDF, HEC-RAS installers, or wholesale USACE
example trees to the public repo.

## Key entry points

- `mirrorz/controller.py` — Goodell-style open → compute → output API
- `docs/automation.md` — book recipe translations
- `examples/*.json` — MirrorZ project files (human-readable)
- `main.py` — GUI / CLI / headless / reports
