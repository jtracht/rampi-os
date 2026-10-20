import json
import shutil
import subprocess

import pytest
from rampi.config import Host
from rampi.kanban import store_token
from rampi.sshkeys import trust


def test_host_form_preserves_noneditable_host_settings():
    original = Host(name="Office", address="old.example", username="alice", resolution="1920x1080")
    changed = Host.from_form({"address": " new.example ", "port": "2222"}, original)
    assert changed.name == "Office" and changed.resolution == "1920x1080"
    assert changed.address == "new.example" and changed.port == 2222
    assert original.address == "old.example"


@pytest.mark.parametrize(
    "kind,account", [("github", ""), ("jira", "alice@example.test"), ("trello", "test-key")]
)
def test_secret_store_uses_stdin_not_process_arguments(monkeypatch, kind, account):
    calls = []
    monkeypatch.setattr("rampi.kanban.command", lambda args, **kwargs: calls.append((args, kwargs)))
    sample = "synthetic-access-value"
    store_token("personal", kind, account, sample)
    args, kwargs = calls[0]
    assert "synthetic-access-value" not in str(args)
    if account:
        assert json.loads(kwargs["input_text"])["token"] == sample
    else:
        assert kwargs["input_text"] == "synthetic-access-value"


def test_host_trust_preserves_other_hosts_and_rejects_rotation(tmp_path):
    if not shutil.which("ssh-keygen"):
        pytest.skip("OpenSSH required")
    public = []
    for name in ["first", "replacement"]:
        path = tmp_path / name
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(path)], check=True)
        public.append(" ".join(path.with_suffix(".pub").read_text().split()[:2]))
    directory = tmp_path / "personal-ssh"
    directory.mkdir()
    target = directory / "known_hosts"
    unrelated = f"other.example {public[0]}\n"
    target.write_text(unrelated)
    host = Host(address="work.example", username="alice", port=2222)
    candidate = {"address": host.address, "port": host.port, "keys": f"ignored {public[0]}"}
    trust(host, candidate, directory)
    saved = target.read_text()
    assert saved.startswith(unrelated)
    assert f"[work.example]:2222 {public[0]}" in saved
    trust(host, candidate, directory)
    assert target.read_text() == saved
    candidate["keys"] = f"ignored {public[1]}"
    with pytest.raises(ValueError, match="Andere Hostschlüssel"):
        trust(host, candidate, directory)
    assert target.read_text() == saved
    with pytest.raises(ValueError, match="Host wurde geändert"):
        trust(Host(address="changed.example", username="alice"), candidate, directory)
