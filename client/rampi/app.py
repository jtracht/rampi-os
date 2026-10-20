"""Native Qt Quick entry point. Offline dashboard requires no host connection."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import cast

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

from .backend import Backend
from .config import Settings


class InputMode(QObject):
    """Use Qt's existing event/focus routing to hide the cursor on any key press."""

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress and QGuiApplication.overrideCursor() is None:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)
        elif event.type() == QEvent.Type.MouseMove and QGuiApplication.overrideCursor() is not None:
            QGuiApplication.restoreOverrideCursor()
        return False


def create_application() -> QGuiApplication:
    # The Windows offscreen plugin has no platform font database by default.
    # Reuse installed system fonts; no Windows font files are redistributed.
    if os.name == "nt" and os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        directory = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        if directory.is_dir():
            os.environ.setdefault("QT_QPA_FONTDIR", str(directory))
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    app = QGuiApplication(sys.argv[:1])
    families = QFontDatabase.families()
    preferred = ["Segoe UI", "DejaVu Sans"] if os.name == "nt" else ["DejaVu Sans", "Noto Sans"]
    for family in preferred:
        if family in families:
            app.setFont(QFont(family))
            break
    for family in ["Consolas", "DejaVu Sans Mono", "Liberation Mono"]:
        if family in families:
            QFont.insertSubstitution("monospace", family)
            break
    return app


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    app = create_application()
    app.setApplicationName("Rampi")
    app.setOrganizationName("Rampi")
    app.setWindowIcon(QIcon(str(Path(__file__).parent / "branding" / "logo.png")))
    input_mode = InputMode(app)
    app.installEventFilter(input_mode)
    try:
        settings = Settings.load()
    except (OSError, ValueError, TypeError) as exc:
        print(f"Konfiguration konnte nicht geladen werden: {exc}", file=sys.stderr)
        return 2
    backend = Backend(settings)
    engine = QQmlApplicationEngine()
    warnings: list[str] = []
    engine.warnings.connect(lambda values: warnings.extend(str(value) for value in values))
    engine.rootContext().setContextProperty("rampi", backend)
    engine.rootContext().setContextProperty("windowed", args.windowed or bool(args.screenshot))
    engine.rootContext().setContextProperty("showSetup", not bool(args.screenshot))
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "qml" / "Main.qml")))
    if not engine.rootObjects():
        return 1
    if args.screenshot:

        def capture():
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            window = cast(QQuickWindow, engine.rootObjects()[0])
            success = window.grabWindow().save(str(args.screenshot))
            app.exit(0 if success else 1)

        QTimer.singleShot(1800, capture)
    if args.smoke_test:
        QTimer.singleShot(1500, app.quit)
    result = app.exec()
    backend.timer.stop()
    backend.jobs.pool.waitForDone(25000)
    # Destroy QML bindings while the context object is still alive (not during Python teardown).
    engine.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    if args.smoke_test and warnings:
        print("QML validation failed: " + "\n".join(warnings), file=sys.stderr)
        return 1
    return result


if __name__ == "__main__":
    raise SystemExit(main())
