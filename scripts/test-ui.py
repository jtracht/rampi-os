"""Exercise actual QML keyboard navigation in a separate native GUI process."""

import json
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
    character
    for character in "Rampi äöü"
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


def wait_until(condition):
    for _ in range(200):
        if condition():
            return
        loop = QEventLoop()
        QTimer.singleShot(25, loop.quit)
        loop.exec()
    raise SystemExit("Actual QML/connector action did not finish")


source = Path(personal_files.name) / "board.json"
source.write_text(
    json.dumps(
        {
            "cards": [
                {"title": "VPN", "project": "Infra", "priority": "high", "status": "Review"},
                {"title": "Layout", "project": "UI", "priority": "normal", "status": "Offen"},
                {"title": "Keys", "project": "Infra", "priority": "normal", "status": "Offen"},
            ]
        }
    ),
    encoding="utf-8",
)
if not backend.save({"board_kind": "json", "board_source": str(source)}):
    raise SystemExit("Could not configure the actual JSON connector")
wait_until(lambda: backend.board["total"] == 3)
window.setProperty("page", "kanban")
app.processEvents()
item("projectFilter").forceActiveFocus()
QTest.keyClick(window, Qt.Key.Key_Down)
wait_until(lambda: backend.board["count"] == 2)
if item("projectFilter").property("currentText") != "Infra":
    raise SystemExit("Filter choice was lost when the model refreshed")
item("priorityFilter").forceActiveFocus()
QTest.keyClick(window, Qt.Key.Key_Down)
wait_until(lambda: backend.board["count"] == 1)
if item("projectFilter").property("currentText") != "Infra":
    raise SystemExit("Combined filters lost the selected project")
backend.refreshBoard()
backend.jobs.pool.waitForDone(25000)
app.processEvents()
if backend.board["count"] != 1:
    raise SystemExit("Refreshing the real JSON source lost filters")
item("statusFilter").forceActiveFocus()
QTest.keyClick(window, Qt.Key.Key_Down)
wait_until(lambda: backend.board["count"] == 0)
QTest.keyClick(window, Qt.Key.Key_Home)
wait_until(lambda: backend.board["count"] == 1)
QMetaObject.invokeMethod(item("clearBoardFilters"), "clicked")
wait_until(lambda: backend.board["count"] == 3)
item("boardSearch").forceActiveFocus()
for key in [Qt.Key.Key_K, Qt.Key.Key_E, Qt.Key.Key_Y, Qt.Key.Key_S]:
    QTest.keyClick(window, key)
wait_until(lambda: backend.board["count"] == 1)
QMetaObject.invokeMethod(item("clearBoardFilters"), "clicked")
wait_until(lambda: backend.board["count"] == 3)
activations = []
reset = item("clearBoardFilters")
reset.clicked.connect(lambda: activations.append(True))
for expected_count, key in enumerate(
    [Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space], start=1
):
    reset.forceActiveFocus()
    QTest.keyClick(window, key)
    if len(activations) != expected_count:
        raise SystemExit("A focused Rampi button did not activate exactly once per key")
if source.read_text(encoding="utf-8").count('"title"') != 3:
    raise SystemExit("Read-only filters changed their source")
window.setProperty("page", "dashboard")


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
item("settingsTabs").setProperty("currentIndex", 3)
item("boardColumns").setProperty("text", "Review\nOffen")
QMetaObject.invokeMethod(item("saveGeneral"), "clicked")
app.processEvents()
if Settings.load().board_columns != ["Review", "Offen"]:
    raise SystemExit("The actual QML column configuration did not persist")
if backend.board["columns"][0]["name"] != "Review":
    raise SystemExit("The real board did not apply the configured column order")
QMetaObject.invokeMethod(dialog, "open")
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
print("PASS: QML keyboard filters, JSON refresh, column persistence, host and session settings.")
