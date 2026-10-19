"""Exercise actual QML keyboard navigation in a separate native GUI process."""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QEventLoop, Qt, QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402, F401
from PySide6.QtTest import QTest  # noqa: E402
from rampi.backend import Backend  # noqa: E402
from rampi.config import Settings  # noqa: E402

app = QGuiApplication([])
backend = Backend(Settings())
backend.timer.stop()
engine = QQmlApplicationEngine()
warnings = []
engine.warnings.connect(lambda values: warnings.extend(str(v) for v in values))
engine.rootContext().setContextProperty("rampi", backend)
engine.rootContext().setContextProperty("windowed", True)
engine.rootContext().setContextProperty("showSetup", False)
engine.load(
    QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / "client/rampi/qml/Main.qml"))
)
if not engine.rootObjects():
    raise SystemExit("QML failed to load")
window = engine.rootObjects()[0]
window.requestActivate()
loop = QEventLoop()
QTimer.singleShot(100, loop.quit)
loop.exec()
for expected in [1, 2, 3, 4, 5, 0]:
    QTest.keyClick(window, Qt.Key.Key_Right)
    if window.property("selected") != expected:
        raise SystemExit(f"Arrow key navigation failed at {expected}")
QTest.keyClick(window, Qt.Key.Key_Return)
if window.property("page") != "kanban":
    raise SystemExit("Enter did not open the actual Kanban module")
QTest.keyClick(window, Qt.Key.Key_Escape)
if window.property("page") != "dashboard":
    raise SystemExit("Escape did not return to dashboard")
if warnings:
    raise SystemExit("QML warnings: " + "\n".join(warnings))
backend.jobs.pool.waitForDone(25000)
print("PASS: actual QML loaded; six keyboard focus moves, Enter and Escape verified.")
