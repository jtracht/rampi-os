"""Verify source-bound hosted Windows component evidence, without host mutation."""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(path: Path, revision: str) -> None:
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Expected an exact source revision")
    proof = json.loads(path.read_text(encoding="utf-8-sig"))
    if proof.get("schema_version") != 1 or proof.get("revision") != revision:
        raise ValueError("Windows evidence revision mismatch")
    for field, source in {
        "installer_sha256": "installer/windows/setup.ps1",
        "test_sha256": "tests/windows/host-components-ci.ps1",
        "rdp_test_sha256": "tests/windows/rdp-client-ci.ps1",
    }.items():
        digest = hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
        if proof.get(field) != digest:
            raise ValueError(f"Windows evidence source mismatch: {source}")
    if not isinstance(proof.get("runner"), str) or not proof["runner"].startswith("win"):
        raise ValueError("Windows runner identity missing")
    for field in [
        "unsupported_edition_rejected_by_default", "what_if_preserved",
        "real_openssh_service_running", "repeat_preserved_configuration",
        "official_sshd_configuration_valid", "rdp_enabled", "nla_required",
        "private_firewall_only", "two_real_standard_user_ssh_logins",
        "wrong_user_key_rejected", "two_real_private_profile_checks",
        "microsoft_rdp_login_complete", "microsoft_rdp_remote_interactive_sid",
        "microsoft_rdp_wrong_password_rejected",
    ]:
        if proof.get(field) is not True:
            raise ValueError(f"Actual Windows component check missing: {field}")
    # These checks do not yet include successful/failed RDP authentication.
    for field in ["authentication_acceptance", "complete_product_acceptance"]:
        if proof.get(field) is not False:
            raise ValueError("Component evidence must not claim complete Windows acceptance")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proof", type=Path)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    verify(args.proof, args.revision)
    print("Actual hosted Windows SSH/component evidence verified; RDP authentication remains open.")
