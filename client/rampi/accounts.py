"""Native account administration via AccountsService, polkit, and system libcrypt."""

import os
import re

from .process import command


def validate_new_user(username: str, password: str) -> None:
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,30}", username):
        raise ValueError("Linux-Benutzername: 1–31 Kleinbuchstaben, Ziffern, _ oder -.")
    if len(password) < 12 or any(c in password for c in "\x00\r\n"):
        raise ValueError("Bitte ein Passwort mit mindestens 12 Zeichen ohne Zeilenumbruch wählen.")


def create_user(username: str, realname: str, password: str) -> str:
    validate_new_user(username, password)
    if os.name != "posix":
        raise RuntimeError("Linux-Benutzerverwaltung ist nur auf Linux verfügbar.")
    # mkpasswd invokes the operating system's libcrypt. No custom hashing or credential DB.
    hashed = command(["mkpasswd", "--method=yescrypt", "--stdin"], input_text=password + "\n")
    from PySide6.QtDBus import QDBus, QDBusConnection, QDBusMessage

    bus = QDBusConnection.systemBus()
    if not bus.isConnected():
        raise RuntimeError("AccountsService ist nicht erreichbar.")

    def authorized_call(path: str, interface: str, method: str, values: list):
        message = QDBusMessage.createMethodCall("org.freedesktop.Accounts", path, interface, method)
        message.setArguments(values)
        message.setInteractiveAuthorizationAllowed(True)
        return bus.call(message, QDBus.CallMode.Block, 60000)

    result = authorized_call(
        "/org/freedesktop/Accounts",
        "org.freedesktop.Accounts",
        "CreateUser",
        [username, realname, 0],
    )
    if result.errorMessage():
        raise RuntimeError(result.errorMessage())
    user_path = result.arguments()[0].path()
    result = authorized_call(
        user_path, "org.freedesktop.Accounts.User", "SetPassword", [hashed, ""]
    )
    if result.errorMessage():
        raise RuntimeError(
            "Konto wurde angelegt, bleibt aber ohne gesetztes Passwort gesperrt: "
            + result.errorMessage()
        )
    return f"Linux-Systemkonto {username} angelegt. Anmeldung über LightDM/PAM möglich."
