"""Real Sunshine/Moonlight pairing and changing video frames in private Docker."""

from __future__ import annotations

import argparse
import array
import math
import os
import re
import subprocess
import time
import uuid
from pathlib import Path


def run(*args: str, input_text=None, check=True):
    result = subprocess.run(
        args,
        input=input_text.encode() if input_text is not None else None,
        capture_output=True,
        timeout=60,
        check=False,
    )
    output = result.stdout.decode(errors="replace")
    error = result.stderr.decode(errors="replace")
    if check and result.returncode:
        raise RuntimeError(f"{args[0]} failed: {error[-2500:]}")
    return subprocess.CompletedProcess(args, result.returncode, output, error)


def container_only():
    if not Path("/.dockerenv").exists() or os.environ.get("RAMPI_TEST_CONTAINER") != "1":
        raise SystemExit("Disposable container required")


def server():
    container_only()
    home = Path.home()
    os.umask(0o077)
    run("pulseaudio", "--start", "--exit-idle-time=-1")
    run(
        "pactl",
        "load-module",
        "module-null-sink",
        "sink_name=rampi_test",
        "rate=48000",
        "channels=2",
    )
    run("pactl", "set-default-sink", "rampi_test")
    run("pactl", "load-module", "module-sine", "sink=rampi_test", "frequency=997")
    pipe = home / "sunshine-pin"
    os.mkfifo(pipe, 0o600)
    config = home / "sunshine.conf"
    config.write_text(
        "capture = x11\nencoder = software\nsw_preset = ultrafast\n"
        "hevc_mode = 1\nav1_mode = 1\nstream_audio = enabled\n"
        "keyboard = disabled\nmouse = disabled\ncontroller = disabled\n"
        "system_tray = disabled\nupnp = disabled\norigin_web_ui_allowed = pc\n"
        + ("min_log_level = debug\n" if os.environ.get("RAMPI_TEST_INPUT_RECEIPTS") == "1" else "")
    )
    with (home / "sunshine.log").open("wb") as log:
        descriptor = os.open(pipe, os.O_RDWR)
        with subprocess.Popen(
            ["sunshine", str(config), "-0"], stdin=descriptor, stdout=log, stderr=log
        ) as process:
            os.close(descriptor)
            try:
                animation = None
                if os.environ.get("RAMPI_TEST_STREAM_SOAK") == "1":
                    animation = subprocess.Popen(
                        [
                            "ffplay",
                            "-loglevel",
                            "error",
                            "-nostats",
                            "-noborder",
                            "-f",
                            "lavfi",
                            "testsrc2=size=1280x720:rate=30",
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                for step in range(600 if animation else 120):
                    if process.poll() is not None:
                        raise RuntimeError(
                            "Sunshine exited: " + (home / "sunshine.log").read_text()
                        )
                    run("xsetroot", "-solid", "#267bbd" if step % 2 else "#d3356a")
                    # Follow Sunshine's virtual sink, as an application opened
                    # after it changes the default output would do.
                    for line in run("pactl", "list", "short", "sink-inputs").stdout.splitlines():
                        run("pactl", "move-sink-input", line.split()[0], "@DEFAULT_SINK@")
                    time.sleep(2)
            finally:
                if animation is not None:
                    animation.terminate()
                    animation.wait(timeout=10)
                process.terminate()


def client(address: str, action: str):
    container_only()
    from rampi.config import Host
    from rampi.launch import pair_args, stream_args, stream_profile

    host = Host(address=address, username="stream-user", resolution="1280x720")
    if action == "pair":
        with (Path.home() / "pair.log").open("wb") as log:
            return subprocess.run(pair_args(host), stdout=log, stderr=log, timeout=40).returncode
    if action == "unpaired":
        host.username = "different-account"
        result = run(
            "moonlight", "list", "-keydir", str(stream_profile(host)), address, check=False
        )
        if "You must pair" not in result.stderr:
            raise RuntimeError("A different, unpaired profile was not rejected")
        return 0
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication([])
    audio_path = Path.home() / "received-audio.raw"
    audio_path.unlink(missing_ok=True)
    log_path = Path.home() / "moonlight.log"
    with log_path.open("wb") as log:
        with subprocess.Popen(stream_args(host), stdout=log, stderr=log) as process:
            try:
                seen = set()
                for _attempt in range(160):
                    if process.poll() is not None:
                        raise RuntimeError("Moonlight exited: " + log_path.read_text())
                    app.processEvents()
                    screen = app.primaryScreen()
                    if screen is not None:
                        frame = screen.grabWindow(0).toImage()
                        if not frame.isNull():
                            pixel = frame.pixelColor(500, 350).getRgb()[:3]
                            for color in [(38, 123, 189), (211, 53, 106)]:
                                if max(abs(a - b) for a, b in zip(pixel, color, strict=True)) < 10:
                                    seen.add(color)
                            if len(seen) == 2 and verify_audio(audio_path):
                                frame.save(str(Path.home() / "streaming-frame.png"))
                                return 0
                    time.sleep(0.25)
                raise RuntimeError("Changing video and the expected remote tone did not arrive")
            finally:
                process.terminate()
                process.wait(timeout=10)


def verify_audio(path: Path) -> bool:
    """Verify decoded PCM from SDL's existing disk output, not a packet/log counter."""
    if not path.exists() or path.stat().st_size < 48000 * 4:
        return False
    raw = path.read_bytes()[-48000 * 4 :]
    samples = array.array("h")
    samples.frombytes(raw[: len(raw) // 4 * 4])
    if os.sys.byteorder != "little":
        samples.byteswap()
    mono = samples[::2]
    energy = sum(value * value for value in mono)
    if not mono or energy / len(mono) < 10000:
        return False

    # Tone correlation rejects silence, arbitrary nonzero output and other tones.
    def power(frequency):
        sine = sum(v * math.sin(2 * math.pi * frequency * i / 48000) for i, v in enumerate(mono))
        cosine = sum(v * math.cos(2 * math.pi * frequency * i / 48000) for i, v in enumerate(mono))
        return sine * sine + cosine * cosine

    return power(997) / (len(mono) * energy) > 0.20


def integration(image: str):
    import json

    network = ""
    containers = []
    suffix = uuid.uuid4().hex[:12]
    root = Path(__file__).resolve().parents[1]

    def execute(container, *args, **kwargs):
        return run("docker", "exec", "-i", container, *args, **kwargs)

    try:
        network = run(
            "docker", "network", "create", "--internal", f"rampi-stream-{suffix}"
        ).stdout.strip()
        for role in ["server", "client"]:
            containers.append(
                run(
                    "docker",
                    "run",
                    "--detach",
                    "--rm",
                    "--network",
                    network,
                    "--name",
                    f"rampi-stream-{suffix}-{role}",
                    "--memory=1g",
                    "--cpus=4",
                    "--mount",
                    f"type=bind,source={root},target=/app,readonly",
                    "-e",
                    "RAMPI_TEST_CONTAINER=1",
                    "-e",
                    "DISPLAY=:99",
                    "-e",
                    "QT_QPA_PLATFORM=xcb",
                    "-e",
                    "SDL_VIDEODRIVER=x11",
                    "-e",
                    "SDL_AUDIODRIVER=disk",
                    "-e",
                    "SDL_DISKAUDIOFILE=/home/rampi/received-audio.raw",
                    "-e",
                    "SDL_RENDER_DRIVER=software",
                    image,
                    "sleep",
                    "infinity",
                ).stdout.strip()
            )
        server_id, client_id = containers
        for container in containers:
            run(
                "docker",
                "exec",
                "--detach",
                container,
                "Xvfb",
                ":99",
                "-screen",
                "0",
                "1280x720x24",
                "-nolisten",
                "tcp",
            )
        time.sleep(1)
        run(
            "docker",
            "exec",
            "--detach",
            server_id,
            "python3",
            "scripts/test-streaming.py",
            "--server",
        )
        address = next(
            iter(
                json.loads(run("docker", "inspect", server_id).stdout)[0]["NetworkSettings"][
                    "Networks"
                ].values()
            )
        )["IPAddress"]
        for _attempt in range(120):
            if ":47989" in execute(server_id, "ss", "-ltn").stdout:
                break
            time.sleep(0.25)
        else:
            raise RuntimeError("Sunshine did not start listening")
        pair = subprocess.Popen(
            [
                "docker",
                "exec",
                client_id,
                "python3",
                "scripts/test-streaming.py",
                "--client",
                address,
                "--action",
                "pair",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _attempt in range(80):
                output = execute(client_id, "cat", "/home/rampi/pair.log", check=False).stdout
                pin = re.search(r"PIN on the target PC: (\d{4})", output)
                if pin:
                    break
                time.sleep(0.25)
            else:
                raise RuntimeError("Moonlight did not request a pairing PIN: " + output)
            execute(
                server_id, "sh", "-c", "cat > /home/rampi/sunshine-pin", input_text=pin[1] + "\n"
            )
            if pair.wait(timeout=40) != 0:
                raise RuntimeError("The Moonlight pairing process failed")
            if "Succesfully paired" not in execute(client_id, "cat", "/home/rampi/pair.log").stdout:
                raise RuntimeError("Moonlight pairing did not complete")
        finally:
            if pair.poll() is None:
                pair.terminate()
                pair.wait(timeout=10)
        for action in ["unpaired", "stream", "stream"]:
            execute(
                client_id,
                "python3",
                "scripts/test-streaming.py",
                "--client",
                address,
                "--action",
                action,
            )
        (root / "artifacts").mkdir(exist_ok=True)
        run(
            "docker",
            "cp",
            f"{client_id}:/home/rampi/streaming-frame.png",
            str(root / "artifacts/streaming-integration.png"),
        )
        print(
            "PASS: real Sunshine/Moonlight pairing, unpaired profile rejection and changing "
            "SDL/FFmpeg video plus decoded 997-Hz audio over two connections. Linux software only."
        )
    except Exception:
        diagnostics = root / "artifacts/streaming-diagnostics"
        diagnostics.mkdir(parents=True, exist_ok=True)
        for container in containers:
            for name in ["sunshine.log", "moonlight.log", "pair.log"]:
                output = execute(container, "cat", "/home/rampi/" + name, check=False)
                if output.returncode == 0:
                    (diagnostics / (container[:12] + "-" + name)).write_text(output.stdout)
            run(
                "docker",
                "cp",
                f"{container}:/home/rampi/received-audio.raw",
                str(diagnostics / (container[:12] + "-audio.raw")),
                check=False,
            )
        raise
    finally:
        for container in containers:
            run("docker", "rm", "--force", container, check=False)
        if network:
            run("docker", "network", "rm", network, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="rampi-streaming-test")
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--client")
    parser.add_argument("--action", choices=["pair", "stream", "unpaired"], default="stream")
    options = parser.parse_args()
    if options.server:
        server()
    elif options.client:
        raise SystemExit(client(options.client, options.action))
    else:
        integration(options.image)
