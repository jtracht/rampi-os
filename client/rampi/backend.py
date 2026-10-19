"""QML facade shared by setup, dashboard, and settings."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import asdict
from functools import partial
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from . import __version__, services
from .config import Host, Settings
from .kanban import Board, load_board
from .launch import browser_args, preview_args, rdp_args, ssh_args, stream_args, terminal_args
from .process import Jobs, command


class Backend(QObject):
    changed = Signal()
    message = Signal(str)
    boardChanged = Signal()

    def __init__(self, settings: Settings, parent: QObject | None = None):
        super().__init__(parent)
        self.settings = settings
        self.jobs = Jobs(self)
        self.jobs.result.connect(self._result)
        self.jobs.failed.connect(self._failed)
        self._status = {"network": "Ungeprüft", "bluetooth": "Ungeprüft", "vpn": "Ungeprüft"}
        self._board = Board()
        self._query = ""
        self._previews = {
            name: "Noch keine Verbindung." for name in ("codex", "claude", "antigravity")
        }
        self.children_processes: dict[str, subprocess.Popen] = {}
        self.timer = QTimer(self)
        self.timer.setInterval(30000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        QTimer.singleShot(100, self.refresh)
        QTimer.singleShot(150, self.refreshBoard)

    @Property(str, constant=True)
    def version(self):
        return __version__

    @Property("QVariantMap", notify=changed)
    def status(self):
        return self._status

    @Property("QVariantMap", notify=changed)
    def configuration(self):
        return asdict(self.settings)

    @Property("QVariantMap", notify=boardChanged)
    def board(self):
        return self._board.view(self._query)

    @Property("QVariantMap", notify=changed)
    def previews(self):
        return self._previews

    @Property(str, constant=True)
    def logoUrl(self):
        local = Path(__file__).parent / "branding" / "logo.png"
        return QUrl.fromLocalFile(str(local)).toString() if local.exists() else ""

    @Slot()
    def refresh(self):
        for name, check in [
            ("network", services.network_status),
            ("bluetooth", services.bluetooth_status),
            ("vpn", services.tailscale_status),
        ]:
            self.jobs.submit(name, check)
        if self.settings.hosts:
            for module in self._previews:
                try:
                    args = preview_args(self.settings.host, module)
                    self.jobs.submit("preview-" + module, partial(command, args, timeout=12))
                except (ValueError, OSError) as exc:
                    self._previews[module] = str(exc)
            self.changed.emit()

    @Slot()
    def refreshBoard(self):
        kind, source, key = (
            self.settings.board_kind,
            self.settings.board_source,
            self.settings.board_token_key,
        )
        self.jobs.submit("board", lambda: load_board(kind, source, key))

    @Slot(str)
    def search(self, query: str):
        self._query = query
        self.boardChanged.emit()

    @Slot()
    def finishSetup(self):
        try:
            self.settings.setup_complete = True
            self.settings.save()
            self.changed.emit()
        except (ValueError, OSError) as exc:
            self.message.emit(str(exc))

    @Slot(str, object)
    def _result(self, name, value):
        if name == "board":
            self._board = value
            self.boardChanged.emit()
        elif name in self._status:
            if name == "bluetooth":
                value = "Bereit" if "Powered: yes" in value else "Aus"
            self._status[name] = str(value)
            self.changed.emit()
        elif name.startswith("preview-"):
            self._previews[name[8:]] = str(value)[-8000:] or "Sitzung ohne sichtbare Ausgabe."
            self.changed.emit()
        else:
            self.message.emit(str(value) or "Vorgang abgeschlossen.")

    @Slot(str, str)
    def _failed(self, name, error):
        if name.startswith("preview-"):
            self._previews[name[8:]] = "Host nicht erreichbar oder noch keine Sitzung."
            self.changed.emit()
        elif name in self._status:
            self._status[name] = "Nicht verfügbar"
            self.changed.emit()
        else:
            self.message.emit(error)

    @Slot("QVariantMap", result=bool)
    def save(self, values):
        try:
            # QJSValue conversion is handled by the QVariantMap slot.
            host = Host(
                address=str(values.get("address", "")).strip(),
                username=str(values.get("username", "")).strip(),
                port=int(values.get("port", 22)),
                identity=str(values.get("identity", "")).strip(),
                project=str(values.get("project", "")),
            )
            raw = asdict(self.settings)
            raw["hosts"] = [Host(**h) for h in raw["hosts"]]
            candidate = Settings(**raw)
            if host.address or host.username:
                host.validate()
                if candidate.hosts:
                    candidate.hosts[candidate.active_host] = host
                else:
                    candidate.hosts = [host]
            candidate.browser_url = str(values.get("browser_url", candidate.browser_url))
            candidate.board_source = str(values.get("board_source", ""))
            candidate.board_kind = str(values.get("board_kind", "json"))
            candidate.board_token_key = str(values.get("board_token_key", ""))
            candidate.reduce_motion = bool(values.get("reduce_motion", False))
            candidate.setup_complete = True
            candidate.save()
            self.settings = candidate
            self.changed.emit()
            self.refreshBoard()
            self.message.emit("Persönliche Einstellungen gespeichert.")
            return True
        except (ValueError, OSError, TypeError) as exc:
            self.message.emit(str(exc))
            return False

    def _launch(self, name: str, args: list[str]):
        current = self.children_processes.get(name)
        if current is not None and current.poll() is None:
            if shutil.which("wmctrl"):
                command(["wmctrl", "-a", f"Rampi · {name}"])
            self.message.emit("Die Anwendung läuft bereits. Wechsel mit Alt+Tab.")
            return
        self.children_processes[name] = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=(os.name != "nt"),
        )

    @Slot(str)
    def launch(self, module: str):
        try:
            if module in {"codex", "claude", "antigravity"}:
                args = terminal_args(ssh_args(self.settings.host, module), module)
            elif module == "browser":
                args = browser_args(self.settings)
            elif module == "rdp":
                args = terminal_args(rdp_args(self.settings.host), "rdp")
            elif module == "stream":
                args = stream_args(self.settings.host)
            elif module == "console":
                args = terminal_args([os.environ.get("SHELL", "/bin/bash")], "console")
            else:
                raise ValueError("Unbekanntes Modul.")
            self._launch(module, args)
        except (ValueError, OSError, RuntimeError) as exc:
            self.message.emit(str(exc))

    @Slot(str, str)
    def action(self, action: str, value: str = ""):
        def execute():
            if action == "wifi-scan":
                return (
                    "\n".join(
                        f"{n['ssid']} · {n['signal']}% · {n['security']}"
                        for n in services.wifi_list()
                    )
                    or "Keine WLANs gefunden."
                )
            if action == "wifi-connect":
                # nmcli prompts in VTE, so passwords never enter argv or the dashboard.
                self.message.emit("WLAN-Zugang bitte im geöffneten Systemdialog bestätigen.")
                return "WLAN-Verwaltung geöffnet."
            if action.startswith("wg-"):
                return services.network_action(action[3:], value)
            if action == "tailscale-status":
                return services.tailscale_status()
            if action == "tailscale-up":
                return command(["tailscale", "up"], timeout=60)
            if action == "tailscale-down":
                return command(["tailscale", "down"], timeout=30)
            if action == "diagnostics":
                import json

                return json.dumps(services.inventory(), indent=2, ensure_ascii=False)
            raise ValueError("Unbekannte Systemaktion.")

        try:
            tools = {
                "wifi-connect": ["nm-connection-editor"],
                "bluetooth": ["blueman-manager"],
                "display": ["arandr"],
                "users": ["gnome-system-tools"],
                "keyboard": ["lxinput"],
                "stream-pair": terminal_args(
                    ["moonlight", "pair", self.settings.host.address], "stream-pair"
                )
                if action == "stream-pair"
                else [],
                "ssh-key": terminal_args(["ssh-keygen", "-t", "ed25519"], "ssh-key")
                if action == "ssh-key"
                else [],
            }
            if action in tools:
                args = tools[action]
                if not args or not shutil.which(args[0]):
                    raise RuntimeError("Der benötigte Systemdialog ist nicht installiert.")
                self._launch(action, args)
            else:
                self.jobs.submit(action, execute)
        except (ValueError, OSError, RuntimeError) as exc:
            self.message.emit(str(exc))

    @Slot(str)
    def openUrl(self, url: str):
        from .config import safe_url

        try:
            QDesktopServices.openUrl(QUrl(safe_url(url)))
        except ValueError as exc:
            self.message.emit(str(exc))
