"""Fresh full-system requirements must not be replaced by container/prepared evidence."""

import json
import runpy
from pathlib import Path

import pytest

CHECK = runpy.run_path(str(Path(__file__).parents[1] /
                          "scripts/check-tailscale-install-evidence.py"))["check"]


@pytest.mark.parametrize("key,value", [
    ("physical_devices", True), ("prepared_development_cache", True),
    ("resumed_development_guest", True), ("graphical_login", False),
    ("memory_mib", 4096), ("cpus", 1), ("architecture", "unknown"),
])
def test_other_environment_rejected_before_component_proof(tmp_path, key, value):
    environment = {
        "physical_devices": False, "prepared_development_cache": False,
        "resumed_development_guest": False, "graphical_login": True,
        "memory_mib": 1024, "cpus": 4, "architecture": "arm64",
    }
    environment[key] = value
    (tmp_path / "environment.json").write_text(json.dumps(environment))
    with pytest.raises(ValueError):
        CHECK(tmp_path)
