"""QML facade shared by setup, dashboard, and settings."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
from dataclasses import asdict, replace
from functools import partial
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from . import __version__, services, sshkeys
from .accounts import create_user
from .config import Host, Settings
from .kanban import Board, load_board, store_token
from .launch import (
    browser_args,
    pair_args,
    preview_args,
    rdp_args,
    session_args,
    ssh_args,
    stream_args,
    stream_profile,
    terminal_args,
)
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
        self._board_generation = 0
        self._query = ""
        self._board_filters = ("", "", "")
        self._vpn_profiles: list[dict] = []
        self._vpn_error = "Noch nicht geprüft"
        self._vpn_generation = 0
        self._host_key: dict = {"fingerprints": ""}
        self._host_generation = 0
        self._sessions = {name: "Ungeprüft" for name in ("codex", "claude", "antigravity")}
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
        view = self._board.view(
            self._query, *self._board_filters, columns=self.settings.board_columns
        )
        project, priority, status = self._board_filters
        view["filters"] = dict(project=project, priority=priority, status=status, query=self._query)
        return view

    @Property("QVariantMap", notify=changed)
    def vpnProfiles(self):
        return {
            "profiles": self._vpn_profiles,
            "error": self._vpn_error,
            "busy": self._vpn_busy(),
        }

    def _vpn_busy(self) -> bool:
        return any(name in self.jobs.pending for name in ("wg-up", "wg-down", "wg-import"))

    @Slot()
    def refreshVpnProfiles(self):
        self._vpn_generation += 1
        self.jobs.submit(
            f"vpn-profiles-{self._vpn_generation}", services.personal_wireguard_profiles
        )

    @Slot(str, str, str)
    def filterBoard(self, project, priority, status):
        self._board_filters = (project, priority, status)
        self.boardChanged.emit()

    @Property("QVariantMap", notify=changed)
    def previews(self):
        return self._previews

    @Property("QVariantMap", notify=changed)
    def hostKey(self):
        return self._host_key

    @Property("QVariantList", notify=changed)
    def sessions(self):
        labels = {"codex": "ChatGPT / Codex", "claude": "Claude Code", "antigravity": "Antigravity"}
        return [
            {"module": name, "title": labels[name], "state": state}
            for name, state in self._sessions.items()
        ]

    def _host_busy(self) -> bool:
        local = {"codex", "claude", "antigravity", "rdp", "stream", "stream-pair"}
        return any(
            name in local and process.poll() is None
            for name, process in self.children_processes.items()
        ) or any(name.startswith("session-stop-") for name in self.jobs.pending)

    def _commit_profile(self, candidate: Settings) -> None:
        old = self.settings.hosts[self.settings.active_host] if self.settings.hosts else None
        new = candidate.hosts[candidate.active_host] if candidate.hosts else None
        if old != new and self._host_busy():
            raise ValueError(
                "Zuerst die lokalen Verbindungen schließen. Windows-KI-Sitzungen bleiben erhalten."
            )
        candidate.save()
        self.settings = candidate
        if old != new:
            self._host_generation += 1
            self._host_key = {"fingerprints": ""}
            self._previews = dict.fromkeys(self._previews, "Noch keine Verbindung.")
            self._sessions = dict.fromkeys(self._sessions, "Ungeprüft")
        self.changed.emit()

    @Slot("QVariantMap", int, result=bool)
    def saveHost(self, values, index):
        try:
            if not -1 <= index < len(self.settings.hosts):
                raise ValueError("Das Hostprofil existiert nicht.")
            base = self.settings.hosts[index] if index >= 0 else None
            host = Host.from_form(values, base)
            if (
                not host.name.strip()
                or len(host.name) > 80
                or any(c in host.name for c in "\r\n\x00")
            ):
                raise ValueError("Einen Profilnamen mit 1 bis 80 Zeichen angeben.")
            host.validate()
            hosts = list(self.settings.hosts)
            if index == -1:
                hosts.append(host)
            else:
                hosts[index] = host
            self._commit_profile(replace(self.settings, hosts=hosts))
            return True
        except (ValueError, OSError, TypeError) as exc:
            self.message.emit(str(exc))
            return False

    @Slot(int, result=bool)
    def selectHost(self, index):
        try:
            if not 0 <= index < len(self.settings.hosts):
                raise ValueError("Das Hostprofil existiert nicht.")
            self._commit_profile(replace(self.settings, active_host=index))
            return True
        except (ValueError, OSError, TypeError) as exc:
            self.message.emit(str(exc))
            return False

    @Slot(int, result=bool)
    def removeHost(self, index):
        try:
            if not 0 <= index < len(self.settings.hosts):
                raise ValueError("Das Hostprofil existiert nicht.")
            hosts = list(self.settings.hosts)
            hosts.pop(index)
            active = self.settings.active_host
            if index < active:
                active -= 1
            elif index == active:
                active = min(active, max(0, len(hosts) - 1))
            self._commit_profile(replace(self.settings, hosts=hosts, active_host=active))
            return True
        except (ValueError, OSError, TypeError) as exc:
            self.message.emit(str(exc))
            return False

    @Slot()
    def disconnectClients(self):
        clients = [
            process
            for name, process in self.children_processes.items()
            if name in {"codex", "claude", "antigravity", "rdp", "stream", "stream-pair"}
        ]

        def disconnect():
            for process in clients:
                if process.poll() is None:
                    if os.name == "posix":
                        try:
                            os.killpg(process.pid, signal.SIGTERM)  # type: ignore[attr-defined]
                        except ProcessLookupError:
                            pass
                    else:
                        process.terminate()
                    process.wait(timeout=8)
            return "Lokale Verbindungen geschlossen. Windows-KI-Prozesse laufen weiter."

        self.jobs.submit("disconnect-clients", disconnect)

    @Slot()
    def refreshSessions(self):
        try:
            host = self.settings.host
            for module in self._sessions:
                self._sessions[module] = "Prüfung läuft …"
                self.jobs.submit(
                    f"session-{self._host_generation}-{module}",
                    partial(command, session_args(host, module, "Status"), timeout=15),
                )
            self.changed.emit()
        except (ValueError, OSError) as exc:
            self.message.emit(str(exc))

    @Slot(str)
    def stopSession(self, module):
        try:
            args = session_args(self.settings.host, module, "Stop")
            self.jobs.submit(
                f"session-stop-{self._host_generation}-{module}", partial(command, args, timeout=15)
            )
        except (ValueError, OSError) as exc:
            self.message.emit(str(exc))

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
                    self.jobs.submit(
                        f"preview-{self._host_generation}-{module}",
                        partial(command, args, timeout=12),
                    )
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
        self.jobs.submit(f"board-{self._board_generation}", lambda: load_board(kind, source, key))

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

    @Slot(str, str, str)
    def createUser(self, username: str, realname: str, password: str):
        self.jobs.submit("create-user", partial(create_user, username, realname, password))

    @Slot(str, str, str, str)
    def storeToken(self, profile: str, kind: str, account: str, token: str):
        self.jobs.submit("secret-store", partial(store_token, profile, kind, account, token))

    @Slot("QVariantMap")
    def scanHost(self, values):
        try:
            host = Host.from_form(values)
            host.validate()
            self.jobs.submit(f"host-key-{self._host_generation}", partial(sshkeys.scan, host))
        except (ValueError, TypeError) as exc:
            self.message.emit(str(exc))

    @Slot("QVariantMap")
    def trustHost(self, values):
        try:
            host = Host.from_form(values)
            self.jobs.submit("host-trust", partial(sshkeys.trust, host, self._host_key.copy()))
        except (ValueError, TypeError) as exc:
            self.message.emit(str(exc))

    @Slot(str, object)
    def _result(self, name, value):
        if name.startswith("board-"):
            if name != f"board-{self._board_generation}":
                return
            self._board = value
            choices = self._board.view(columns=self.settings.board_columns)
            project, priority, status = (
                selected if selected in choices[key] else ""
                for selected, key in zip(
                    self._board_filters, ("projects", "priorities", "statuses"), strict=True
                )
            )
            self._board_filters = (project, priority, status)
            self.boardChanged.emit()
        elif name.startswith("host-key-"):
            if name != f"host-key-{self._host_generation}":
                return
            self._host_key = value
            self.changed.emit()
        elif name.startswith("session-stop-"):
            if name.removeprefix("session-stop-").split("-", 1)[0] != str(self._host_generation):
                return
            self._sessions[name.rsplit("-", 1)[1]] = "Keine Sitzung"
            self.changed.emit()
            self.message.emit("Windows-KI-Sitzung beendet.")
        elif name.startswith("session-"):
            _, generation, module = name.split("-", 2)
            if generation != str(self._host_generation):
                return
            try:
                status = json.loads(value)
                if (
                    status.get("schema") != 1
                    or status.get("module") != module
                    or not isinstance(status.get("running"), bool)
                ):
                    raise ValueError("Ungültiger Sitzungsstatus")
                self._sessions[module] = (
                    "Läuft auf Windows" if status["running"] else "Keine Sitzung"
                )
            except (ValueError, TypeError, AttributeError):
                self._sessions[module] = "Windows-Adapter aktualisieren"
            self.changed.emit()
        elif name in self._status:
            if name == "bluetooth":
                value = "Bereit" if "Powered: yes" in value else "Aus"
            self._status[name] = str(value)
            self.changed.emit()
        elif name.startswith("vpn-profiles-"):
            if name != f"vpn-profiles-{self._vpn_generation}":
                return
            self._vpn_profiles = value
            self._vpn_error = "" if value else "Keine persönlichen WireGuard-Profile gefunden."
            self.changed.emit()
        elif name in {"wg-import", "wg-up", "wg-down"}:
            self.message.emit(str(value))
            self.refreshVpnProfiles()
            self.changed.emit()
        elif name.startswith("preview-"):
            _, generation, module = name.split("-", 2)
            if generation != str(self._host_generation):
                return
            self._previews[module] = str(value)[-8000:] or "Sitzung ohne sichtbare Ausgabe."
            self.changed.emit()
        else:
            self.message.emit(str(value) or "Vorgang abgeschlossen.")

    @Slot(str, str)
    def _failed(self, name, error):
        if name.startswith("board-") and name != f"board-{self._board_generation}":
            return
        if name.startswith("vpn-profiles-"):
            if name != f"vpn-profiles-{self._vpn_generation}":
                return
            self._vpn_profiles = []
            self._vpn_error = str(error)
            self.changed.emit()
        elif name in {"wg-import", "wg-up", "wg-down"}:
            self.message.emit(error)
            self.refreshVpnProfiles()
            self.changed.emit()
        elif name.startswith("preview-"):
            _, generation, module = name.split("-", 2)
            if generation != str(self._host_generation):
                return
            self._previews[module] = "Host nicht erreichbar oder noch keine Sitzung."
            self.changed.emit()
        elif name.startswith("session-") and not name.startswith("session-stop-"):
            _, generation, module = name.split("-", 2)
            if generation != str(self._host_generation):
                return
            self._sessions[module] = "Nicht verfügbar · SSH/Host-Adapter prüfen"
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
            base = self.settings.hosts[self.settings.active_host] if self.settings.hosts else None
            host = Host.from_form(values, base)
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
            if "board_columns" in values:
                if not isinstance(values["board_columns"], list):
                    raise ValueError("Kanban-Spalten müssen eine Liste sein.")
                candidate.board_columns = values["board_columns"]
            candidate.reduce_motion = bool(values.get("reduce_motion", False))
            source_changed = (
                candidate.board_kind,
                candidate.board_source,
                candidate.board_token_key,
            ) != (
                self.settings.board_kind,
                self.settings.board_source,
                self.settings.board_token_key,
            )
            candidate.setup_complete = True
            self._commit_profile(candidate)
            if source_changed:
                self._board_generation += 1
                self._board = Board()
                self._query = ""
                self._board_filters = ("", "", "")
            self.boardChanged.emit()
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
                try:
                    command(["wmctrl", "-F", "-a", f"Rampi · {name}"])
                except RuntimeError:
                    pass  # The application may have set its own dynamic window title.
            self.message.emit("Die Anwendung läuft bereits. Wechsel mit Alt+Tab.")
            return
        environment = os.environ.copy()
        if name == "stream":
            environment.update(SDL_GRAB_KEYBOARD="0", SDL_VIDEODRIVER="x11")
        self.children_processes[name] = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=(os.name != "nt"),
            env=environment,
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
                profile = stream_profile(self.settings.host)
                if not all((profile / name).is_file() for name in ("client.pem", "key.pem")):
                    raise RuntimeError(
                        "Diesen Host mit diesem Windows-Konto zuerst über "
                        "„Streaming-Host koppeln“ koppeln."
                    )
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
        if action in {"wg-import", "wg-up", "wg-down"} and self._vpn_busy():
            self.message.emit("Eine WireGuard-Änderung läuft bereits.")
            return

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
                return services.tailscale_action("up")
            if action == "tailscale-down":
                return services.tailscale_action("down")
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
                "stream-pair": terminal_args(pair_args(self.settings.host), "stream-pair")
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
                if action in {"wg-import", "wg-up", "wg-down"}:
                    self._vpn_generation += 1
                self.jobs.submit(action, execute)
                if action in {"wg-import", "wg-up", "wg-down"}:
                    self.changed.emit()
        except (ValueError, OSError, RuntimeError) as exc:
            self.message.emit(str(exc))

    @Slot(str)
    def openUrl(self, url: str):
        from .config import safe_url

        try:
            QDesktopServices.openUrl(QUrl(safe_url(url)))
        except ValueError as exc:
            self.message.emit(str(exc))
