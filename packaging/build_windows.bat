@echo off
REM ===========================================================================
REM packaging\build_windows.bat - build the Windows app + installer.
REM ===========================================================================
REM RUN THIS ON WINDOWS from the repo root:
REM     packaging\build_windows.bat
REM
REM Produces:
REM   dist\MirrorZ-Hecras\           the frozen app folder
REM   dist\MirrorZ-Hecras-Setup.exe  installer (only if Inno Setup installed)
REM
REM Prerequisites: Python 3.10+, and optionally Inno Setup 6
REM (https://jrsoftware.org/isinfo.php) for the installer step.
REM For Microsoft Store distribution you will package as MSIX instead -
REM see docs\packaging.md section "Microsoft Store".
REM ===========================================================================
setlocal
cd /d "%~dp0\.."

echo ==^> Creating build virtualenv
python -m venv .build-venv || goto :fail
call .build-venv\Scripts\activate.bat
pip install --upgrade pip >NUL
pip install -e ".[package]" >NUL || goto :fail

echo ==^> Generating icons
python packaging\make_icons.py

echo ==^> Freezing with PyInstaller
pyinstaller --noconfirm packaging\mirrorz.spec || goto :fail

echo ==^> Building installer (requires Inno Setup's ISCC on PATH)
where ISCC >NUL 2>NUL
if %ERRORLEVEL%==0 (
    ISCC packaging\windows_installer.iss || goto :fail
    echo ==^> DONE: dist\MirrorZ-Hecras-Setup.exe
) else (
    echo ISCC not found - skipped installer. App folder: dist\MirrorZ-Hecras
)
exit /b 0

:fail
echo BUILD FAILED
exit /b 1
