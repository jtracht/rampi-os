import os
from dataclasses import replace

from rampi.config import Host
from rampi.launch import pair_args, stream_args, stream_profile


def test_pairing_profiles_separate_accounts_hosts_and_linux_users(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "alice"))
    monkeypatch.setattr("rampi.launch.executable", lambda *names: "moonlight")
    host = Host(address="workstation", username="alice")
    profile = stream_profile(host)
    pair = pair_args(host)
    stream = stream_args(host)
    assert pair[pair.index("-keydir") + 1] == str(profile)
    assert stream[stream.index("-keydir") + 1] == str(profile)
    assert stream_profile(replace(host, name="Renamed", project="C:\\Other")) == profile
    assert stream_profile(replace(host, username="bob")) != profile
    assert stream_profile(replace(host, address="other")) != profile
    assert stream_profile(replace(host, port=2222)) != profile
    assert stream_profile(replace(host, username="ALICE", address="WORKSTATION")) == profile
    if os.name != "nt":
        for directory in [profile, profile.parent, profile.parent.parent]:
            assert directory.stat().st_mode & 0o777 == 0o700
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "bob"))
    assert stream_profile(host) != profile
