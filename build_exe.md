# Packaging Spotlight as a standalone executable

## Quick start (Windows)

From the project folder, with your venv activated:

```powershell
pip install -r requirements-build.txt
pyinstaller spotlight.spec
```

The built app lands in `dist\Spotlight\` — `Spotlight.exe` plus an
`_internal` folder it depends on. **Distribute the whole `Spotlight`
folder, not just the .exe** (see "onedir vs onefile" below for why).

Run it by double-clicking `dist\Spotlight\Spotlight.exe`.

## What's actually in spotlight.spec, and why it matters

The one line that makes this work correctly is:

```python
datas=[('assets', 'assets')]
```

Without it, **the app builds and runs without crashing** — but silently
loses its entire dark theme and bundled Inter font, because
`app/main.py` loads `assets/style.qss` and `assets/fonts/Inter.ttf` via a
runtime file-path lookup, which PyInstaller's static import analysis has
no way to discover on its own. This isn't theoretical — it was confirmed
with an actual test build: without `--add-data`/`datas`, the resulting
executable ran, but every single style rule and the custom font were
silently absent, with no error or warning anywhere. `app/main.py` also
now prints a `WARNING:` to the console if this ever happens again (e.g.
if you add a new asset file later and forget to update the spec), so
it's loud instead of silent.

`app/main.py`'s `_resolve_assets_dir()` function is the other half of
this fix — it checks `sys.frozen`/`sys._MEIPASS` to find the bundled
assets folder correctly in a frozen build, instead of assuming it's next
to the original source file (which is only true when running via
`python -m app.main`).

## Things confirmed to work

- **The dark theme and Inter font** load correctly in a frozen build —
  tested directly, not assumed.
- **PDF export / Print** (`QtPrintSupport`) — PyInstaller's built-in
  PySide6 hook automatically detects and bundles the print-support
  plugin your code actually imports, so this needed no extra
  configuration. Verified by generating a real PDF from a simulated
  frozen environment and checking it's a valid file, not just checking
  that files exist.
- **The SQLite database path** (`~/.spotlight/spotlight.db`) was already
  written using the user's home directory rather than a path relative to
  the script, so it was never at risk from this class of bug in the
  first place.

## Things I could not test from this environment (Windows-specific)

Built and tested on Linux, which catches *code-level* packaging bugs
(the asset-path issue above) but can't verify Windows-specific
distribution concerns. Worth knowing about before you ship this to
anyone else:

- **Antivirus / Windows SmartScreen**: unsigned PyInstaller executables
  are commonly flagged by Windows Defender and other antivirus software
  as suspicious, and SmartScreen will show a "Windows protected your PC"
  warning on first run from an unrecognized publisher. Neither means
  anything is actually wrong — it's a trust/signing issue, not a bug —
  but it's real friction for anyone you send this to. The real fix is a
  code-signing certificate, which costs money and isn't something that
  can be set up from here.
- **Microsoft Visual C++ Redistributable**: PySide6's compiled Qt
  libraries generally need this present on the target machine. Most
  Windows installs already have it (lots of software depends on it), but
  a bare-metal fresh Windows install might not.
- **File size**: expect roughly 80–150MB for the built app — PySide6
  bundles a lot of Qt. Not a bug, just worth knowing before you try to
  email it to someone.

## App icon

`spotlight.spec` embeds `assets/icon.ico` into the `.exe` file itself via
the `icon=` parameter. This is a Windows/Mac-specific mechanism (PE/Mach-O
resources) — building from a Linux dev environment produces a
`WARNING: Ignoring icon; supported only on Windows and macOS!` in the
PyInstaller log, which is expected and not a bug; it means the icon will
apply correctly once built on an actual Windows machine, just not
verifiable from Linux.

Separately, `app/main.py` sets the same icon on the running
`QApplication` via `setWindowIcon()`, which covers the taskbar/title-bar
icon on every platform regardless of which OS built the `.exe` — that
half was fully tested and confirmed working.

The icon itself (`assets/icon.png` / `assets/icon.ico`) was generated
programmatically with Pillow rather than external artwork, so it can be
regenerated or tweaked (colors, glyph, corner radius) by editing a short
script rather than needing a design tool.

## onedir vs onefile

This spec builds "onedir" style — a folder containing the `.exe` and an
`_internal` folder of dependencies, rather than a single `.exe` file.
This is intentional: onefile mode re-extracts everything to a temp
folder on *every single launch*, which is noticeably slower to start.
onedir starts fast because nothing needs to be extracted first.

The tradeoff: you're distributing a folder, not one file. If you need a
single file to send someone (at the cost of slower startup), add
`--onefile` to the PyInstaller command instead of using the spec file
as-is — but note the asset-bundling fix above still applies either way.

## Rebuilding after code changes

Re-run `pyinstaller spotlight.spec` any time you change the app. If you
add a new file under `assets/` (e.g. a new font weight or an icon), no
spec changes are needed — the whole `assets/` folder is bundled as a
unit, not file-by-file.
