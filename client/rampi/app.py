"""Native Qt Quick entry point. Offline dashboard requires no host connection."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import cast

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    app = QGuiApplication(sys.argv[:1])
    app.setApplicationName("Rampi")
    app.setOrganizationName("Rampi")
    input_mode = InputMode(app)
    app.installEventFilter(input_mode)
    try:
        settings = Settings.load()
    except (OSError, ValueError, TypeError) as exc:
        print(f"Konfiguration konnte nicht geladen werden: {exc}", file=sys.stderr)
        return 2
    backend = Backend(settings)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("rampi", backend)
    engine.rootContext().setContextProperty("windowed", args.windowed or bool(args.screenshot))
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
    return result


if __name__ == "__main__":
    raise SystemExit(main())
