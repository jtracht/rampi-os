"""Real Bluetooth HID to GTK, six XKB layouts and two PAM users; isolated QEMU only."""

import errno
import hashlib
import importlib.util
import ipaddress
import json
import os
import pwd
import re
import runpy
import secrets
import select
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

if os.geteuid() != 0 or not Path("/etc/rampi-acceptance-vm").is_file():
    raise SystemExit("Designated QEMU fixture required")
subprocess.run(["systemd-detect-virt", "--vm", "--quiet"], check=True)
# Public Google Bumble source commit, pinned independently by the evidence checker.
SDK_REVISION = "e1fe43c9b44be0d974a6fd533ac6d494fc50510a"  # pragma: allowlist secret
source = Path("/opt/rampi-source")
rdp_accounts = None
rdp_config = Path("/run/rampi-rdp-test.json")
if rdp_config.exists():
    info = rdp_config.lstat()
    if rdp_config.is_symlink() or info.st_uid != 0 or info.st_mode & 0o777 != 0o600:
        raise RuntimeError("Disposable RDP configuration must remain private to guest root")
    configuration = json.loads(rdp_config.read_text())
    rdp_accounts = configuration.get("accounts", {})
    if (
        configuration.get("scope") != "rampi-isolated-hid-rdp"
        or configuration.get("internal_network") is not True
        or set(rdp_accounts) != {"rampi-hid-one", "rampi-hid-two"}
    ):
        raise RuntimeError("Invalid isolated RDP/HID fixture configuration")
    for fixture in rdp_accounts.values():
        address = ipaddress.IPv4Address(fixture["address"])
        if (
            not address.is_private
            or address.is_loopback
            or address.is_link_local
            or not re.fullmatch(r"[0-9a-f]{64}", fixture["fingerprint"])
            or not re.fullmatch(r"[0-9a-f]{32}", fixture["nonce"])
            or not re.fullmatch(r"[A-Za-z0-9_-]{20,128}", fixture["password"])
        ):
            raise RuntimeError("Invalid generated RDP fixture endpoint or identity")
out = Path("/opt/rampi-captures/hid")
out.mkdir(mode=0o755, exist_ok=True)
out.chmod(0o755)
if shutil.which("wlr-randr") is None:
    subprocess.run(
        ["apt-get", "install", "-y", "--no-install-recommends", "wlr-randr"],
        env=dict(os.environ, DEBIAN_FRONTEND="noninteractive"),
        check=True,
        timeout=180,
    )
if shutil.which("evtest") is None:
    subprocess.run(
        ["apt-get", "install", "-y", "--no-install-recommends", "evtest"],
        env=dict(os.environ, DEBIAN_FRONTEND="noninteractive"),
        check=True,
        timeout=180,
    )
subprocess.run(["systemctl", "stop", "greetd"], check=True)
if subprocess.run(
    ["python3", "-c", "import pyatspi"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
).returncode:
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
    subprocess.run(
        ["apt-get", "install", "-y", "--no-install-recommends", "python3-pyatspi", "at-spi2-core"],
        env=env,
        check=True,
        timeout=300,
    )
spec = importlib.util.spec_from_file_location(
    "rampi_login", source / "scripts/virtual/test-login-guest.py"
)
login = importlib.util.module_from_spec(spec)
spec.loader.exec_module(login)
if (
    not hashlib.sha256(Path("/opt/rampi/current/rampi-native").read_bytes()).hexdigest()
    == hashlib.sha256((source / "rampi-native").read_bytes()).hexdigest()
):
    raise RuntimeError("Installed source ELF mismatch")
login.configure_test_session()
if subprocess.run(
    ["modinfo", "hci_vhci"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
).returncode:
    subprocess.run(["bash", str(source / "scripts/virtual/ensure-vhci.sh")], check=True)
else:
    subprocess.run(["modprobe", "hci_vhci"], check=True)
# Register the emulated controllers before the existing daemon starts probing
# them. Preserve its startup log so a kernel HCI reset failure is diagnosable.
subprocess.run(["systemctl", "stop", "bluetooth"], check=True)
emulator_log = (out / "peer-emulator.log").open("w")
(out / "peer-emulator.log").chmod(0o644)
peer_emulator = subprocess.Popen(["btvirt", "-l2"], stdout=emulator_log, stderr=emulator_log)
subprocess.run(["systemctl", "start", "bluetooth"], check=True)
for adapter, address in [("hci0", "00:AA:01:00:00:00"), ("hci1", "00:AA:01:01:00:01")]:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if peer_emulator.poll() is not None:
            raise RuntimeError("Virtual controller emulator exited")
        result = subprocess.run(
            [
                "busctl",
                "--system",
                "--timeout=5",
                "get-property",
                "org.bluez",
                "/org/bluez/" + adapter,
                "org.bluez.Adapter1",
                "Address",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and address in result.stdout:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("Actual BlueZ fixture adapter not ready: " + adapter)
subprocess.run(["rfkill", "unblock", "bluetooth"], check=True)


def require_power_state(adapter, powered):
    # The adapter object can appear while BlueZ's automatic enable is pending.
    # A conflicting Set may fail even though that operation reaches our target.
    # Actual state, not a successful method return, is the fixture prerequisite.
    prefix = ["busctl", "--system", "--timeout=15"]
    target = "/org/bluez/" + adapter
    desired = "b true" if powered else "b false"

    def observed():
        result = subprocess.run(
            prefix + ["get-property", "org.bluez", target, "org.bluez.Adapter1", "Powered"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return result.returncode == 0 and result.stdout.strip() == desired

    if observed():
        return
    changed = subprocess.run(
        prefix
        + [
            "set-property",
            "org.bluez",
            target,
            "org.bluez.Adapter1",
            "Powered",
            "b",
            "true" if powered else "false",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if peer_emulator.poll() is not None:
            raise RuntimeError("Virtual controller emulator exited during power initialization")
        if observed():
            return
        time.sleep(0.2)
    raise RuntimeError(
        "Actual BlueZ power state not reached: " + adapter + " " + desired + ": " + changed.stderr
    )


require_power_state("hci0", True)
subprocess.run(["modprobe", "uhid"], check=True)
# The SDK needs the peer down. Do not first power it on unnecessarily.
require_power_state("hci1", False)
if not Path("/opt/rampi-bumble-venv/bin/python").is_file():
    subprocess.run(
        ["apt-get", "install", "-y", "--no-install-recommends", "python3-venv", "git"],
        env=dict(os.environ, DEBIAN_FRONTEND="noninteractive"),
        check=True,
        timeout=300,
    )
    subprocess.run(["python3", "-m", "venv", "/opt/rampi-bumble-venv"], check=True)
    subprocess.run(
        [
            "/opt/rampi-bumble-venv/bin/pip",
            "install",
            "--no-input",
            "--disable-pip-version-check",
            "bumble @ git+https://github.com/google/bumble@e1fe43c9b44be0d974a6fd533ac6d494fc50510a",
        ],
        check=True,
        timeout=600,
    )
result = subprocess.check_output(
    [
        "/opt/rampi-bumble-venv/bin/python",
        "-c",
        (
            "import importlib.metadata,json; "
            "data=importlib.metadata.distribution('bumble').read_text('direct_url.json'); "
            "print(json.loads(data)['vcs_info']['commit_id'])"
        ),
    ],
    text=True,
)
if not result.strip() == SDK_REVISION:
    raise RuntimeError("Actual HID fixture precondition failed")
with urllib.request.urlopen(
    "https://raw.githubusercontent.com/google/bumble/e1fe43c9b44be0d974a6fd533ac6d494fc50510a/examples/hid_keyboard.json",
    timeout=30,
) as response:
    configuration = json.load(response)
configuration["name"] = "Rampi Virtual HID Joined"
Path("/run/rampi-bumble-device.json").write_text(json.dumps(configuration))
private = Path("/run/rampi-hid-private")
private.mkdir(mode=0o700, exist_ok=True)
peer_log = (private / "peer.log").open("w")
peer = subprocess.Popen(
    ["/opt/rampi-bumble-venv/bin/python", str(source / "scripts/virtual/bluetooth-hid-peer.py")],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=peer_log,
    text=True,
    bufsize=1,
)


def reply(command=None):
    if command is not None:
        peer.stdin.write(json.dumps(command) + "\n")
        peer.stdin.flush()
    if not select.select([peer.stdout], [], [], 45)[0]:
        raise RuntimeError("SDK peer timed out")
    line = peer.stdout.readline()
    if not line:
        raise RuntimeError(f"SDK peer exited without a reply (exit {peer.poll()})")
    result = json.loads(line)
    if "error_type" in result:
        raise RuntimeError(f"SDK peer failure: {result}")
    return result


ready = reply()
if not (ready["ready"] and ready["address"].upper() == "00:AA:01:01:00:01"):
    raise RuntimeError("Actual HID fixture precondition failed")
oracle = runpy.run_path(str(source / "scripts/virtual/hid-layout-oracle.py"))["expected"]
user = None
sessions = []
accounts = {}
trace = None
trace_file = None
bond = Path("/var/lib/bluetooth/00:AA:01:00:00:00/00:AA:01:01:00:01/info")


def kernel_events(path, start, end=None):
    try:
        with path.open("rb") as stream:
            stream.seek(start)
            data = stream.read(-1 if end is None else end - start).decode("utf-8", errors="replace")
    except OSError as error:
        # A growing 9p trace can temporarily report ENODATA on Docker's host
        # share. No events satisfy the predicate; the existing deadline still
        # requires the complete press/release bytes and final independent read.
        if error.errno == errno.ENODATA:
            return set()
        raise
    return {
        (int(code), int(value))
        for code, value in re.findall(
            r"type 1 \(EV_KEY\), code ([0-9]+) \([^)]+\), value ([012])", data
        )
    }


def click(x, y):
    login.as_user(user, "wlrctl", "pointer", "move", "-10000", "-10000")
    login.as_user(user, "wlrctl", "pointer", "move", str(x), str(y))
    login.as_user(user, "wlrctl", "pointer", "click", "left")
    time.sleep(0.5)


def capture(name):
    path = Path(pwd.getpwnam(user).pw_dir) / (name + ".png")
    login.as_user(user, "grim", str(path))
    shutil.copyfile(path, out / path.name)
    (out / path.name).chmod(0o644)


def cursor_capture(user, name, bounds):
    """Compare cursor overlay with the same empty part of the actual entry."""
    from PIL import Image

    stem = user + "-" + name
    paths = []
    for overlay in (False, True):
        path = Path(pwd.getpwnam(user).pw_dir) / (
            stem + ("-cursor.png" if overlay else "-plain.png")
        )
        login.as_user(user, "grim", *(["-c"] if overlay else []), str(path))
        target = out / path.name
        shutil.copyfile(path, target)
        target.chmod(0o644)
        paths.append(path)
    center = bounds["x"] + bounds["width"] // 2
    area = [center - 64, bounds["y"] + 8, center + 64, bounds["y"] + bounds["height"] - 8]
    with Image.open(paths[0]) as first, Image.open(paths[1]) as second:
        a, b = first.convert("RGB"), second.convert("RGB")
        if a.size != b.size or not (
            0 <= area[0] < area[2] <= a.width and 0 <= area[1] < area[3] <= a.height
        ):
            raise RuntimeError("Actual cursor image bounds mismatch")
        pixels = sum(
            sum(abs(x - y) for x, y in zip(a.getpixel((px, py)), b.getpixel((px, py)), strict=True))
            > 60
            for px in range(area[0], area[2])
            for py in range(area[1], area[3])
        )
    # Headless outputs can already composite a software cursor in both PNGs.
    # Check the actual empty field pixels as well; do not infer hidden from
    # two identical screenshots. The cursor-visible mouse control must pass.
    reference = area[2] + 32
    with Image.open(paths[1]) as source_image:
        image = source_image.convert("RGB")
        visible = sum(
            sum(
                abs(x - y)
                for x, y in zip(
                    image.getpixel((px, py)), image.getpixel((reference, py)), strict=True
                )
            )
            > 60
            for px in range(area[0], area[2])
            for py in range(area[1], area[3])
        )
    return {
        "plain": paths[0].name,
        "overlay": paths[1].name,
        "area": area,
        "pixels": visible,
        "overlay_difference_pixels": pixels,
    }


def prop(name):
    p = subprocess.run(
        [
            "busctl",
            "--system",
            "--timeout=5",
            "get-property",
            "org.bluez",
            "/org/bluez/hci0/dev_00_AA_01_01_00_01",
            "org.bluez.Device1",
            name,
        ],
        capture_output=True,
        text=True,
    )
    return p.stdout.strip() if p.returncode == 0 else ""


def input_devices():
    nodes = {}
    for event in Path("/sys/class/input").glob("event*"):
        bus_type = event / "device/id/bustype"
        if not bus_type.is_file() or bus_type.read_text().strip() != "0005":
            continue
        node = "/dev/input/" + event.name
        properties = subprocess.check_output(
            ["udevadm", "info", "--query=property", "--name=" + node], text=True
        ).splitlines()
        for kind, tag in [("keyboard", "ID_INPUT_KEYBOARD=1"), ("mouse", "ID_INPUT_MOUSE=1")]:
            if tag in properties:
                nodes[kind] = node
    return nodes


def visible_nodes():
    started = time.monotonic()
    result = login.as_user(user, "python3", str(source / "scripts/virtual/hid-accessible-state.py"))
    rows = json.loads(result.stdout)
    timing = out / "a11y-query-times.jsonl"
    reasons = {"read-budget", "depth-limit", "node-limit", "stale-object"}
    read_status = next(
        (
            line.split(" ", 1)[1]
            for line in result.stderr.decode(errors="replace").splitlines()
            if line.startswith("A11Y_READ_UNAVAILABLE ") and line.split(" ", 1)[1] in reasons
        ),
        "complete" if rows else "no-current-frame",
    )
    with timing.open("a") as stream:
        stream.write(
            json.dumps(
                {
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "row_count": len(rows),
                    "read_status": read_status,
                }
            )
            + "\n"
        )
    timing.chmod(0o644)
    (out / "last-accessible.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    (out / "last-accessible.json").chmod(0o644)
    return rows


def visible_names():
    return [r["name"] for r in visible_nodes()]


def action_ready(name):
    return any(
        r["role"] in {"button", "push button"} and r["name"] == name and r["sensitive"]
        for r in visible_nodes()
    )


def activate(caption):
    login.wait(lambda: action_ready(caption), "actual visible action: " + caption)
    # Exactly one acknowledged GTK action; never replay an uncertain activation.
    login.as_user(
        user,
        "python3",
        str(source / "scripts/virtual/hid-accessible-state.py"),
        "--fixture-activate",
        caption,
    )


def open_bluetooth():
    def caption():
        matches = [
            r["name"]
            for r in visible_nodes()
            if r["role"] == "button" and r["name"].startswith("Bluetooth · ") and r["sensitive"]
        ]
        return matches[0] if len(matches) == 1 else None

    login.wait(lambda: bool(caption()), "actual dashboard Bluetooth control")
    activate(caption())


def select_peer():
    address = "00:AA:01:01:00:01"
    login.wait(
        lambda: any(address in name for name in visible_names()),
        "actual visible pinned SDK HID row",
    )
    bounds = json.loads(
        login.as_user(
            user,
            "python3",
            str(source / "scripts/virtual/hid-accessible-state.py"),
            "--fixture-peer-bounds",
            address,
        ).stdout
    )
    click(bounds["x"] + bounds["width"] // 2, bounds["y"] + bounds["height"] // 2)


def categories():
    names = visible_names()
    return (
        any("Wähle einen Bereich" in n for n in names)
        and "WLAN" in names
        and ("Bluetooth" in names)
    )


def logout():
    login.as_user(user, "wlrctl", "toplevel", "close", "app_id:org.rampi.Workstation")
    login.greeter_ready()


try:
    for name in ["rampi-hid-one", "rampi-hid-two"]:
        try:
            pwd.getpwnam(name)
        except KeyError:
            pass
        else:
            raise RuntimeError("Unexpected existing HID fixture user")
        subprocess.run(["useradd", "--create-home", "--shell", "/bin/bash", name], check=True)
        account = pwd.getpwnam(name)
        home = Path(account.pw_dir)
        if not (home == Path("/home") / name and (not home.is_symlink())):
            raise RuntimeError("Actual HID fixture precondition failed")
        for path in [home / ".config", home / ".config/rampi", home / ".config/rampi/labwc"]:
            path.mkdir(mode=0o700, exist_ok=True)
            os.chown(path, account.pw_uid, account.pw_gid)
            path.chmod(0o700)
        settings = home / ".config/rampi/settings.json"
        settings.write_text(
            json.dumps(
                {
                    "language": "de",
                    "setup_complete": True,
                    "sound_effects": False,
                    "hosts": [
                        {
                            "name": "Isolated XRDP fixture",
                            "address": rdp_accounts[name]["address"],
                            "username": "rdpuser",
                            "resolution": "1280x720",
                        }
                    ]
                    if rdp_accounts is not None
                    else [],
                }
            )
        )
        os.chown(settings, account.pw_uid, account.pw_gid)
        settings.chmod(0o600)
        unit = home / ".config/systemd/user/rampi.service.d/90-rampi-hid-accessibility.conf"
        unit.parent.mkdir(parents=True, exist_ok=True)
        for directory in [home / ".config/systemd", home / ".config/systemd/user", unit.parent]:
            os.chown(directory, account.pw_uid, account.pw_gid)
            directory.chmod(0o700)
        unit.write_text("[Service]\nEnvironment=GTK_A11Y=atspi\n")
        os.chown(unit, account.pw_uid, account.pw_gid)
        unit.chmod(0o600)
        password = secrets.token_urlsafe(24)
        subprocess.run(["chpasswd"], input=(name + ":" + password + "\n").encode(), check=True)
        accounts[name] = (account, password)
    subprocess.run(["systemctl", "restart", "greetd"], check=True)
    for user, layouts in [
        ("rampi-hid-one", ["de", "us", "gb"]),
        ("rampi-hid-two", ["fr", "es", "it"]),
    ]:
        account, password = accounts[user]
        home = Path(account.pw_dir)
        for layout in layouts:
            keyboard = home / ".config/rampi/labwc/environment"
            keyboard.write_text("XKB_DEFAULT_LAYOUT=" + layout + "\n")
            os.chown(keyboard, account.pw_uid, account.pw_gid)
            keyboard.chmod(0o600)
            login.greeter_ready()
            login.login(user, password)
            login.wait(
                lambda user=user: (
                    b"org.rampi.Workstation"
                    in login.as_user(user, "wlrctl", "toplevel", "list", check=False).stdout
                ),
                "actual HID user's mapped native session",
            )
            if not int((home / ".rampi-login-uid").read_text()) == account.pw_uid:
                raise RuntimeError("Actual HID fixture precondition failed")
            pid = int(
                login.as_user(
                    user,
                    "systemctl",
                    "--user",
                    "show",
                    "rampi.service",
                    "--property=MainPID",
                    "--value",
                ).stdout
            )
            actual_binary = hashlib.sha256(Path(f"/proc/{pid}/exe").read_bytes()).hexdigest()
            if (
                pid <= 1
                or Path(f"/proc/{pid}").stat().st_uid != account.pw_uid
                or actual_binary
                != hashlib.sha256((source / "rampi-native").read_bytes()).hexdigest()
            ):
                raise RuntimeError("Actual authenticated HID process identity/program mismatch")
            process_environment = dict(
                item.split(b"=", 1)
                for item in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
                if b"=" in item
            )
            if process_environment.get(b"GTK_A11Y") != b"atspi":
                raise RuntimeError(
                    "Actual fixture did not enable the existing GTK accessibility backend"
                )
            output = json.loads(login.as_user(user, "wlr-randr", "--json").stdout)
            current = [m for o in output for m in o["modes"] if m.get("current")]
            if not (
                len(current) == 1 and current[0]["width"] == 1280 and (current[0]["height"] == 720)
            ):
                raise RuntimeError("Actual HID fixture precondition failed")
            open_bluetooth()
            if not sessions:
                activate("Geräte suchen")
                login.wait(lambda: bool(prop("Address")), "GUI discovers pinned SDK HID peer")
                select_peer()
                activate("Suche beenden")
                activate("Koppeln")
                login.wait(lambda: prop("Paired") == "b true", "GUI HID pairing")
                login.wait(lambda: action_ready("Dauerhaft vertrauen"), "GUI finishes pairing")
                activate("Dauerhaft vertrauen")
                capture("trust-confirmation")
                login.as_user(
                    user,
                    "python3",
                    "/opt/rampi-source/scripts/virtual/hid-accessible-state.py",
                    "--fixture-activate",
                    "Bewusst bestätigen",
                )
                login.wait(lambda: prop("Trusted") == "b true", "explicit GUI trust")
                login.wait(lambda: action_ready("Verbinden"), "GUI finishes explicit trust")
                activate("Verbinden")
            login.wait(lambda: reply({"action": "state"})["channels"], "real HID channels")
            login.wait(
                lambda: set(input_devices()) == {"keyboard", "mouse"},
                "initial kernel HID devices classified by udev",
            )
            if not (bond.is_file() and "[LinkKey]" in bond.read_text()):
                raise RuntimeError("Actual HID fixture precondition failed")
            select_peer()
            activate("Trennen")
            login.wait(
                lambda: reply({"action": "state"})["disconnected"],
                "GUI disconnects both HID channels",
            )
            login.wait(lambda: not input_devices(), "disconnected kernel HID devices removed")
            login.wait(lambda: prop("Connected") == "b false", "BlueZ completes ACL disconnection")
            login.wait(
                lambda: action_ready("Verbinden"), "GUI releases the completed Bluetooth action"
            )
            activate("Verbinden")
            login.wait(lambda: reply({"action": "state"})["channels"], "GUI reconnects HID")
            login.wait(
                lambda: set(input_devices()) == {"keyboard", "mouse"},
                "reconnected kernel HID devices classified by udev",
            )
            nodes = input_devices()
            # This is preparation, not the later real HID Escape/shortcut proof.
            # A reconnect can change seat focus: use the acknowledged GTK back
            # action, then require its actual category page before proceeding.
            activate("← Einstellungen")
            login.wait(categories, "Bluetooth back action maps settings categories")
            activate("Host & SSH")
            bounds = json.loads(
                login.as_user(
                    user,
                    "python3",
                    str(source / "scripts/virtual/hid-accessible-state.py"),
                    "--fixture-control-bounds",
                    "Profilname",
                ).stdout
            )
            click(bounds["x"] + bounds["width"] // 2, bounds["y"] + bounds["height"] // 2)
            # Position with the existing tool, then hand pointer ownership to
            # the persistent real kernel Bluetooth mouse before keyboard input.
            reply({"action": "mouse", "dx": 1, "dy": 1})
            print(
                "RAMPI_HID_STATE_BEFORE_TEXT "
                + json.dumps(
                    {
                        "sdk": reply({"action": "state"}),
                        "connected": prop("Connected"),
                        "nodes": input_devices(),
                    }
                ),
                flush=True,
            )
            kernel_log = out / (user + "-" + layout + "-kernel-keyboard.txt")
            trace_file = kernel_log.open("w")
            kernel_log.chmod(0o644)
            trace = subprocess.Popen(
                ["stdbuf", "-oL", "evtest", nodes["keyboard"]], stdout=trace_file, stderr=trace_file
            )
            login.wait(
                lambda kernel_log=kernel_log: "Testing" in kernel_log.read_text(errors="replace"),
                "existing evtest attached to synthetic Bluetooth keyboard",
            )
            observed = []
            for usage, keycode, modifiers in [
                (4, 30, 0),
                (28, 21, 0),
                (29, 44, 0),
                (31, 3, 2),
                (8, 18, 64),
            ]:
                login.as_user(
                    user,
                    "wtype",
                    "-s",
                    "100",
                    "-M",
                    "ctrl",
                    "-k",
                    "a",
                    "-m",
                    "ctrl",
                    "-k",
                    "BackSpace",
                )

                def profile_text(user=user):
                    return json.loads(
                        login.as_user(
                            user,
                            "python3",
                            str(source / "scripts/virtual/hid-accessible-state.py"),
                            "--fixture-profile-text",
                        ).stdout
                    )

                login.wait(lambda: profile_text() == "", "actual synthetic HID field cleared")
                print(
                    f"RAMPI_HID_CASE user={user} layout={layout} "
                    f"usage={usage} modifiers={modifiers}",
                    flush=True,
                )
                kernel_start = kernel_log.stat().st_size
                reply({"action": "keyboard", "usage": usage, "modifiers": modifiers})
                codes = {keycode} | (
                    {42} if modifiers == 2 else {100} if modifiers == 64 else set()
                )
                required_events = {(code, value) for code in codes for value in (0, 1)}

                def kernel_received(required=required_events, path=kernel_log, start=kernel_start):
                    return required <= kernel_events(path, start)

                login.wait(kernel_received, "actual kernel HID key and modifier press/release")
                kernel_end = kernel_log.stat().st_size
                expected = oracle(layout, keycode, modifiers)
                if expected:
                    login.wait(
                        lambda expected=expected: profile_text() == expected,
                        "actual HID text reached GTK",
                    )
                else:
                    # A delivered, unconsumed Alt shortcut must remain non-text.
                    time.sleep(1)
                    if profile_text() != "":
                        raise RuntimeError("Alt shortcut unexpectedly inserted text")
                    time.sleep(1)
                value = profile_text()
                if not value == expected:
                    raise RuntimeError(
                        ("Actual HID layout mismatch", layout, usage, modifiers, value, expected)
                    )
                observed.append(
                    {
                        "usage": usage,
                        "modifiers": modifiers,
                        "actual": value,
                        "expected": expected,
                        "kernel_offset_start": kernel_start,
                        "kernel_offset_end": kernel_end,
                    }
                )
            accessible = visible_nodes()
            if not any(
                r["role"] in {"text", "entry"} and r["name"] == "Profilname" for r in accessible
            ):
                raise RuntimeError("Actual GTK entry has no accessible form name")
            metadata = out / (user + "-" + layout + "-accessible.json")
            metadata.write_text(json.dumps(accessible, ensure_ascii=False, indent=2) + "\n")
            metadata.chmod(0o644)
            capture(user + "-" + layout + "-hid-text")
            hidden_cursor = cursor_capture(user, layout + "-keyboard", bounds)
            if hidden_cursor["pixels"]:
                raise RuntimeError(
                    "Persistent Bluetooth pointer remains visible after keyboard input"
                )
            reply({"action": "mouse", "dx": 8, "dy": 5, "click": False})
            time.sleep(0.3)
            restored_cursor = cursor_capture(user, layout + "-mouse", bounds)
            if restored_cursor["pixels"] < 5:
                raise RuntimeError("Bluetooth mouse movement did not restore the pointer")
            login.as_user(user, "wlrctl", "pointer", "move", "-10000", "-10000")
            login.as_user(user, "wlrctl", "pointer", "move", "100", "44")
            reply({"action": "mouse"})
            login.wait(categories, "actual HID mouse back action")
            capture(user + "-" + layout + "-hid-mouse")
            reply({"action": "keyboard", "usage": 74, "modifiers": 5})

            def dashboard_ready():
                rows = visible_nodes()
                names = [r["name"] for r in rows if r["role"] == "button"]
                return (
                    "Kanban Board" in names
                    and any(n.startswith("WLAN") for n in names)
                    and any(
                        n.replace("\u2068", "").replace("\u2069", "") == "Bluetooth · 1 verbunden"
                        for n in names
                    )
                )

            login.wait(dashboard_ready, "HID reserved shortcut and named dashboard controls")
            metadata = out / (user + "-" + layout + "-dashboard-accessible.json")
            metadata.write_text(json.dumps(visible_nodes(), ensure_ascii=False, indent=2) + "\n")
            metadata.chmod(0o644)
            capture(user + "-" + layout + "-hid-shortcut")
            remote_proof = None
            if rdp_accounts is not None:
                stage = runpy.run_path(str(source / "scripts/virtual/hid-rdp-stage.py"))
                remote_proof = stage["run"](
                    login,
                    user,
                    layout,
                    rdp_accounts[user],
                    reply,
                    visible_nodes,
                    capture,
                    kernel_log,
                    observed,
                )
            if not (
                keyboard.stat().st_mode & 0o777 == 0o600
                and keyboard.stat().st_uid == account.pw_uid
            ):
                raise RuntimeError("Actual HID fixture precondition failed")
            sessions.append(
                {
                    "user": user,
                    "uid": account.pw_uid,
                    "native_pid": pid,
                    "gtk_accessibility_backend": "atspi",
                    "native_elf_sha256": actual_binary,
                    "layout": layout,
                    "keys": observed,
                    "mouse_back": True,
                    "keyboard_cursor": hidden_cursor,
                    "mouse_cursor": restored_cursor,
                    "accessible_field_name": True,
                    "reserved_shortcut": True,
                    "actual_reconnect": True,
                    "kernel_bluetooth_input_nodes": nodes,
                    "rdp": remote_proof,
                }
            )
            if layout == "it":
                open_bluetooth()
                select_peer()
                activate("Kopplung entfernen")
                capture("forget-confirmation")
                login.as_user(
                    user,
                    "python3",
                    "/opt/rampi-source/scripts/virtual/hid-accessible-state.py",
                    "--fixture-activate",
                    "Bewusst bestätigen",
                )
                login.wait(
                    lambda: not prop("Address") and (not bond.exists()),
                    "GUI removes actual HID bond",
                )
                login.wait(lambda: not input_devices(), "forgotten HID input nodes removed")
            trace.terminate()
            trace.wait(timeout=5)
            trace_file.close()
            trace = None
            trace_file = None
            logout()
    for user in accounts:
        other = next(name for name in accounts if name != user)
        private_file = Path(accounts[other][0].pw_dir) / ".config/rampi/labwc/environment"
        if not login.as_user(user, "cat", str(private_file), check=False).returncode != 0:
            raise RuntimeError("Actual HID fixture precondition failed")
    proof = {
        "schema": 1,
        "sdk_revision": SDK_REVISION,
        "source_hashes": {
            name: hashlib.sha256((source / name).read_bytes()).hexdigest()
            for name in [
                "scripts/virtual/test-hid-guest.py",
                "scripts/virtual/bluetooth-hid-peer.py",
                "scripts/virtual/hid-layout-oracle.py",
                "scripts/virtual/hid-accessible-state.py",
                "scripts/virtual/hid-rdp-stage.py",
            ]
        },
        "sessions": sessions,
        "two_personal_layout_files_private": True,
        "actual_ui_pair_trust_connect_reconnect_forget": True,
        "native_elf_sha256": hashlib.sha256(
            Path("/opt/rampi/current/rampi-native").read_bytes()
        ).hexdigest(),
        "peer_sha256": hashlib.sha256(
            (source / "scripts/virtual/bluetooth-hid-peer.py").read_bytes()
        ).hexdigest(),
        "complete_product_acceptance": False,
    }
    (out / "hid-proof.json").write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n")
    (out / "hid-proof.json").chmod(0o644)
    print("RAMPI_ACTUAL_HID_GUI_SIX_LAYOUTS_TWO_USERS_OK", flush=True)
except Exception:
    if user is not None:
        capture("failed-state")
    raise
finally:
    if trace is not None:
        trace.terminate()
        trace.wait(timeout=5)
    if trace_file is not None:
        trace_file.close()
    peer.terminate()
    peer.wait(timeout=5)
    peer_log.close()
    peer_emulator.terminate()
    peer_emulator.wait(timeout=5)
