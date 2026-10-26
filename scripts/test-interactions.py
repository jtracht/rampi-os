"""Exercise page routing and rendered motion through real Qt input events."""

import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QEventLoop, QObject, Qt, QTimer, QUrl  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from rampi.app import create_application  # noqa: E402
from rampi.backend import Backend  # noqa: E402
from rampi.config import Settings  # noqa: E402


def require(value, message):
    if not value:
        raise AssertionError(message)


def wait(milliseconds):
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


with tempfile.TemporaryDirectory(prefix="rampi-interactions-") as home:
    os.environ["XDG_CONFIG_HOME"] = home
    os.environ["XDG_CACHE_HOME"] = home
    app = create_application()
    backend = Backend(Settings(setup_complete=True, sound_effects=False))
    backend.timer.stop()
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda values: warnings.extend(str(v) for v in values))
    for name, value in [("rampi", backend), ("windowed", True), ("showSetup", False)]:
        engine.rootContext().setContextProperty(name, value)
    engine.load(
        QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / "client/rampi/qml/Main.qml"))
    )
    require(engine.rootObjects(), "Actual QML could not load: " + str(warnings))
    window = engine.rootObjects()[0]
    window.requestActivate()

    def visual_items(root):
        yield root
        for child in root.childItems():
            yield from visual_items(child)

    def item(name):
        found = next(
            (v for v in visual_items(window.contentItem()) if v.objectName() == name), None
        ) or window.findChild(QObject, name)
        require(found is not None, "Missing real control: " + name)
        return found

    artifacts = Path(os.environ.get("RAMPI_TEST_ARTIFACTS", "artifacts/interactions"))
    artifacts.mkdir(parents=True, exist_ok=True)
    tiles = [
        item("liquid-" + icon)
        for icon in ["columns-3", "monitor", "globe"]
    ]
    wait(65)
    require(any(abs(tile.property("wave")) > 1 for tile in tiles), "No actual startup deformation")
    require(
        window.grabWindow().save(str((artifacts / "startup-wave.png").resolve())),
        "Startup capture failed",
    )
    wait(500)
    tile = tiles[2]
    tile.forceActiveFocus()
    wait(40)
    require(abs(tile.property("wave")) > 1, "Focus did not animate the selected tile")
    require(
        window.grabWindow().save(str((artifacts / "focus-wave.png").resolve())),
        "Focus capture failed",
    )
    wait(250)
    first_phase = tile.property("phase")
    wait(100)
    require(tile.property("phase") != first_phase, "Focused surface does not keep flowing")
    point = tiles[1].mapToScene(tiles[1].boundingRect().center()).toPoint()
    QTest.mouseMove(window, point)
    wait(40)
    require(tiles[1].property("activeFocus"), "Mouse hover did not select a tile")
    require(abs(tiles[1].property("wave")) > 1, "Mouse hover did not animate the tile")
    feedback = item("interactionFeedback")
    require(feedback.property("selectionCount") > 0, "Focus/hover feedback did not run")
    # Reduced motion must stop every tile immediately, including in-flight bursts.
    backend.settings.reduce_motion = True
    backend.changed.emit()
    wait(50)
    require(
        all(tile.property("wave") == 0 and tile.property("phase") == 0 for tile in tiles),
        "Reduced motion leaves deformation running",
    )
    # These are the only dashboard entries for the two radio services.
    settings = item("settingsDialog")
    for key, index in [("network", 2), ("bluetooth", 3)]:
        require(
            sum(v.objectName() == "dashboard-" + key for v in visual_items(window.contentItem()))
            == 1,
            "Duplicate dashboard radio entry",
        )
        button = item("dashboard-" + key)
        button.forceActiveFocus()
        before = feedback.property("activationCount")
        QTest.keyClick(window, Qt.Key.Key_Return)
        wait(40)
        require(
            settings.property("visible") and settings.property("current"),
            "Radio entry did not open settings",
        )
        require(
            item("settingsTabs").property("currentIndex") == index, "Radio opened the wrong tab"
        )
        require(
            settings.width() == window.width() and settings.height() == window.height(),
            "Settings is a floating panel rather than a whole page",
        )
        require(
            feedback.property("activationCount") == before + 1,
            "Activation feedback did not run exactly once",
        )
        # Repeated Tab navigation must not reach the disabled dashboard.
        for _ in range(30):
            QTest.keyClick(window, Qt.Key.Key_Tab)
            focus = window.activeFocusItem()
            parent = focus
            while parent and parent != settings:
                parent = parent.parentItem()
            require(parent == settings, "Tab escaped the current settings page")
        backend.message.emit("Testmeldung ohne Fensterwechsel")
        require(settings.property("current"), "Status feedback interrupted settings")
        require(
            not item("notificationDialog").property("visible"), "A status notification popped up"
        )
        QTest.keyClick(window, Qt.Key.Key_Escape)
        require(not settings.property("visible"), "Escape did not return from settings")
    require(not backend.children_processes, "Settings started an external program")
    require(len(app.allWindows()) == 1, "Settings created a second native window")
    require(not warnings, "QML warnings: " + "\n".join(warnings))
    (artifacts / "result.json").write_text(
        json.dumps(
            {
                "whole_page_wifi_bluetooth": True,
                "single_native_window": True,
                "startup_focus_hover_wave": True,
                "reduced_motion": True,
                "feedback_events": True,
                "keyboard_focus_contained": True,
            },
            indent=2,
        )
        + "\n"
    )
    backend.jobs.pool.waitForDone(25000)
    backend.bt_agent.close()
    engine.deleteLater()
    app.processEvents()
    print(
        "PASS: real startup/hover/focus motion, reduced motion, click events, "
        "separate radio pages, contained keyboard focus and one native window."
    )
