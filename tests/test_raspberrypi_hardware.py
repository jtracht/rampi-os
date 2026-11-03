"""Execute the installer model gate, including low-memory and carrierboard variants."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")


@pytest.mark.skipif(os.name == "nt" or not BASH, reason="Actual Linux Bash required")
@pytest.mark.parametrize("model,accepted", [
    ("Raspberry Pi 3 Model B Rev 1.2", True),
    ("Raspberry Pi 3 Model B Plus Rev 1.3", True),
    ("Raspberry Pi 3 Model A Plus Rev 1.0", True),
    ("Raspberry Pi 4 Model B Rev 1.5", True),
    ("Raspberry Pi 5 Model B Rev 1.0", True),
    ("Raspberry Pi 400 Rev 1.0", True),
    ("Raspberry Pi 500 Rev 1.0", True),
    ("Raspberry Pi 500 Plus Rev 1.0", True),
    ("Raspberry Pi Compute Module 3 Plus Rev 1.0", True),
    ("Raspberry Pi Compute Module 4S Rev 1.0", True),
    ("Raspberry Pi Compute Module 5 Rev 1.0", True),
    ("Raspberry Pi Zero 2 W Rev 1.0", True),
    ("Raspberry Pi 2 Model B Rev 1.1", False),
    ("Raspberry Pi Zero W Rev 1.1", False),
    ("Raspberry Pi Pico", False),
    ("Raspberry Pi 6 Model B", False),
    ("", False),
])
def test_actual_model_gate(model, accepted):
    result = subprocess.run(
        [BASH, "-c", 'source "$1"; rampi_supported_model "$2"',
         "hardware-test", str(ROOT / "installer/raspberrypi/hardware.sh"), model],
        check=False, timeout=10,
    )
    assert result.returncode == (0 if accepted else 1)
