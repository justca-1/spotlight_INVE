"""Spotlight entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication, QDialog

from app.database.engine import init_db
from app.database.seed import seed_if_empty
from app.services.auth_service import seed_accounts_if_empty
from app.ui.change_password_dialog import ChangePasswordDialog
from app.ui.login_view import LoginDialog
from app.ui.main_window import MainWindow
from app.widgets.hover_effects import HoverLiftFilter
from app import session


def _resolve_assets_dir() -> Path:
    """Find the assets/ folder in both normal (python -m app.main) and
    PyInstaller-frozen execution.

    Frozen apps extract bundled data files next to sys._MEIPASS (onefile)
    or next to the executable (onedir) -- NOT next to this file's original
    source location, which is what a plain Path(__file__) lookup assumes.
    A real PyInstaller build confirmed this concretely: without this
    check, ASSETS_DIR pointed at a location that doesn't exist in the
    frozen bundle, and the app silently ran with no theme and no bundled
    font -- no crash, no warning, just a completely different-looking app
    than what was tested. See build_exe.md for the matching --add-data
    flag this depends on.
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base / "assets"
    return Path(__file__).resolve().parent.parent / "assets"


ASSETS_DIR = _resolve_assets_dir()


def install_excepthook() -> None:
    """Qt's event loop silently swallows exceptions raised inside slots.
    Without this hook, bugs in signal handlers fail invisibly instead of
    surfacing anywhere.
    """

    def hook(exc_type, exc_value, exc_tb):
        import traceback

        traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = hook


def load_fonts() -> str:
    """Load the bundled Inter font (SIL OFL licensed, assets/fonts/Inter.ttf)
    so the app looks the same everywhere rather than depending on whatever
    happens to be installed on a given machine. Returns the family name to
    use, falling back to a sensible system default if the font file is
    missing or fails to load for any reason.
    """
    font_path = ASSETS_DIR / "fonts" / "Inter.ttf"
    fallback = "Segoe UI"

    if not font_path.exists():
        print(f"WARNING: bundled font not found at {font_path} -- using {fallback} instead.")
        return fallback

    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id == -1:
        print(f"WARNING: failed to load font from {font_path} -- using {fallback} instead.")
        return fallback

    families = QFontDatabase.applicationFontFamilies(font_id)
    return families[0] if families else fallback


def load_stylesheet(app: QApplication, font_family: str) -> None:
    qss_path = ASSETS_DIR / "style.qss"
    if not qss_path.exists():
        print(f"WARNING: stylesheet not found at {qss_path} -- app will use default Qt styling.")
        return
    # The QSS ships with a placeholder so the loaded font family (which
    # can only be known at runtime, after addApplicationFont) is
    # injected here rather than hardcoded.
    stylesheet = qss_path.read_text().replace("__FONT_FAMILY__", font_family)
    app.setStyleSheet(stylesheet)


def load_app_icon() -> QIcon:
    """The .exe's file icon (set via spotlight.spec's icon= parameter) and
    the *running window's* taskbar/title-bar icon are two separate things
    in Qt -- the spec file only handles the former. Setting this on the
    QApplication covers every window the app creates (login, main window,
    dialogs) without needing to set it individually on each one.
    """
    icon_path = ASSETS_DIR / "icon.png"
    if not icon_path.exists():
        print(f"WARNING: app icon not found at {icon_path}.")
        return QIcon()
    return QIcon(str(icon_path))


def run_session(app: QApplication) -> None:
    """One login -> MainWindow -> (logout | quit) cycle. Logout closes
    MainWindow and loops back to a fresh login screen; quitting the app
    (closing the window normally, or cancelling login) exits the loop.

    Each phase (LoginDialog.exec(), then a QEventLoop per MainWindow
    session) runs its own blocking Qt event loop rather than requiring one
    top-level app.exec() -- Qt supports this without issue, and it keeps
    the login/logout cycle a plain Python while-loop instead of threading
    show/hide state through signal handlers.
    """
    while True:
        login = LoginDialog()
        if login.exec() != QDialog.DialogCode.Accepted:
            return  # cancelled login -- exit the app

        info = session.get_current()
        if info is not None and info.must_change_password:
            change_dlg = ChangePasswordDialog(account_id=info.account_id, forced=True)
            if change_dlg.exec() != QDialog.DialogCode.Accepted:
                # "Log Out Instead" or closing the dialog -- don't let the
                # session continue on the default password.
                session.clear_current()
                continue
            # Reflect the change in the live session object so nothing
            # downstream re-checks a now-stale must_change_password flag.
            info.must_change_password = False

        window = MainWindow()
        window.show()

        loop = QEventLoop()
        window.logoutRequested.connect(loop.quit)
        window.destroyed.connect(loop.quit)
        loop.exec()

        if not window.logged_out:
            return  # window was closed normally, not via Logout -- exit


def main() -> int:
    install_excepthook()

    init_db()
    seed_if_empty()
    seed_accounts_if_empty()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(load_app_icon())

    # Parented to app so it stays alive for the app's lifetime; see
    # hover_effects.py for why this is a single global filter rather than
    # per-widget wiring scattered across every UI file.
    hover_filter = HoverLiftFilter(app)
    app.installEventFilter(hover_filter)

    font_family = load_fonts()
    load_stylesheet(app, font_family)

    run_session(app)

    return 0


if __name__ == "__main__":
    sys.exit(main())
