"""Exercise actual QML keyboard navigation in a separate native GUI process."""

import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
personal_files = tempfile.TemporaryDirectory(prefix="rampi-ui-")
os.environ["XDG_CONFIG_HOME"] = personal_files.name
os.environ["XDG_CACHE_HOME"] = personal_files.name

from PySide6.QtCore import (  # noqa: E402
    QEvent,
    QEventLoop,
    QMetaObject,
    QObject,
    Qt,
    QTimer,
    QUrl,
)
from PySide6.QtGui import QFont, QFontDatabase, QFontInfo, QFontMetrics  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402, F401
from PySide6.QtTest import QTest  # noqa: E402
from rampi.app import create_application  # noqa: E402
from rampi.backend import Backend  # noqa: E402
from rampi.config import Settings  # noqa: E402

app = create_application()
missing = [
    character for character in "Rampi äöü"
    if not QFontMetrics(app.font()).inFontUcs4(ord(character))
]
if missing:
    raise SystemExit(
        f"The real platform font {QFontInfo(app.font()).family()!r} cannot render {missing!r}; "
        f"available families: {QFontDatabase.families()}"
    )
metrics = QFontMetrics(QFont("monospace", 12))
if metrics.horizontalAdvance("iii") != metrics.horizontalAdvance("WWW"):
    raise SystemExit("Terminal previews do not use an actual monospace font")
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


def item(name):
    value = window.findChild(QObject, name)
    if value is None:
        raise SystemExit(f"Missing actual QML control: {name}")
    return value


dialog = item("settingsDialog")
QMetaObject.invokeMethod(dialog, "open")
app.processEvents()
QMetaObject.invokeMethod(item("newHost"), "clicked")
for name, value in [
    ("hostName", "Software-Test"),
    ("hostAddress", "windows.test"),
    ("hostUsername", "developer"),
]:
    item(name).setProperty("text", value)
QMetaObject.invokeMethod(item("saveHost"), "clicked")
app.processEvents()
if len(backend.settings.hosts) != 1 or backend.settings.hosts[0].name != "Software-Test":
    raise SystemExit("The real QML host editor did not persist its profile")
QMetaObject.invokeMethod(dialog, "close")
QMetaObject.invokeMethod(dialog, "open")
app.processEvents()
if item("hostAddress").property("text") != "windows.test":
    raise SystemExit("The real QML host editor did not restore its profile")
item("settingsTabs").setProperty("currentIndex", 4)
app.processEvents()
QTest.qWait(100)
output = Path(os.environ.get("RAMPI_TEST_ARTIFACTS", personal_files.name)) / "session-settings.png"
output.parent.mkdir(parents=True, exist_ok=True)
if not window.grabWindow().save(str(output.resolve())):
    raise SystemExit("Could not capture the actual session settings")
QTest.keyClick(window, Qt.Key.Key_Tab)
QTest.keyClick(window, Qt.Key.Key_Escape)
if dialog.property("visible"):
    raise SystemExit("Keyboard Escape did not close session settings")
if warnings:
    raise SystemExit("QML warnings: " + "\n".join(warnings))
backend.jobs.pool.waitForDone(25000)
engine.deleteLater()
app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
personal_files.cleanup()
print("PASS: actual QML keyboard navigation, host profile save/restore and session dialog.")
