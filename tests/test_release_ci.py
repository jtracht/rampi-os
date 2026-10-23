"""Release authorization contracts against explicit GitHub API response fixtures."""

import copy
import runpy
from pathlib import Path

import pytest

gate = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/check-release-ci.py"))
SHA = "a" * 40
REPOSITORY = "jtracht/rampi-os"


def evidence():
    run = {
        "id": 123, "head_sha": SHA, "head_branch": "main", "event": "push",
        "path": ".github/workflows/rust.yml", "status": "completed", "conclusion": "success",
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY}, "run_attempt": 1,
    }
    jobs = [
        {"id": index, "name": name, "head_sha": SHA,
         "status": "completed", "conclusion": "success"}
        for index, name in enumerate([
            "native (ubuntu-24.04, amd64)", "native (ubuntu-24.04-arm, arm64)"
        ], 1)
    ]
    return {"total_count": 1, "workflow_runs": [run]}, {"total_count": 2, "jobs": jobs}


def verify(runs, jobs):
    return gate["verify_workflow"](REPOSITORY, SHA, "rust.yml", runs, lambda _: jobs)


def test_native_requires_both_successful_architectures_for_same_revision():
    runs, jobs = evidence()
    proof = verify(runs, jobs)
    assert proof["run_id"] == 123 and len(proof["jobs"]) == 2
    assert proof["revision"] == SHA


@pytest.mark.parametrize("field,value", [
    ("head_sha", "b" * 40), ("head_branch", "feature"), ("event", "pull_request"),
    ("path", ".github/workflows/other.yml"), ("status", "in_progress"),
    ("conclusion", "failure"), ("conclusion", "cancelled"), ("conclusion", "skipped"),
    ("head_repository", {"full_name": "someone/fork"}),
    ("repository", {"full_name": "someone/fork"}),
])
def test_foreign_unfinished_and_unsuccessful_runs_cannot_authorize_release(field, value):
    runs, jobs = evidence()
    runs["workflow_runs"][0][field] = value
    with pytest.raises(ValueError):
        verify(runs, jobs)


def test_older_success_cannot_hide_newer_failure_or_pending_retry():
    runs, jobs = evidence()
    newest = copy.deepcopy(runs["workflow_runs"][0])
    newest.update(id=124, status="in_progress", conclusion=None)
    runs["workflow_runs"].append(newest)
    runs["total_count"] = 2
    with pytest.raises(ValueError):
        verify(runs, jobs)


@pytest.mark.parametrize("field,value", [
    ("head_sha", "b" * 40), ("status", "queued"), ("conclusion", "skipped"),
    ("conclusion", "failure"), ("name", "unexpected architecture"),
])
def test_job_level_failures_and_missing_architecture_are_rejected(field, value):
    runs, jobs = evidence()
    jobs["jobs"][1][field] = value
    with pytest.raises(ValueError):
        verify(runs, jobs)


def test_incomplete_api_pages_and_absent_workflows_are_rejected():
    runs, jobs = evidence()
    for absent in [{"total_count": 0, "workflow_runs": []}, {**runs, "total_count": 2}]:
        with pytest.raises(ValueError):
            verify(absent, jobs)
    jobs["total_count"] = 3
    with pytest.raises(ValueError):
        verify(runs, jobs)


def test_general_ci_alone_is_insufficient(monkeypatch):
    def api(_repository, endpoint, **_query):
        if "rust.yml" in endpoint:
            return {"total_count": 0, "workflow_runs": []}
        runs, jobs = evidence()
        if "workflows" in endpoint:
            runs["workflow_runs"][0]["path"] = ".github/workflows/ci.yml"
            return runs
        jobs["jobs"] = [
            {"id": index, "name": name, "head_sha": SHA,
             "status": "completed", "conclusion": "success"}
            for index, name in enumerate([
                "client (ubuntu-24.04)", "client (windows-latest)", "trixie-arm64",
                "windows-host", "scripts", "security",
            ], 1)
        ]
        jobs["total_count"] = 6
        return jobs

    monkeypatch.setitem(gate["check"].__globals__, "api", api)
    with pytest.raises(ValueError, match="rust.yml"):
        gate["check"](REPOSITORY, SHA)


def test_offline_proof_cannot_claim_a_different_source_or_omit_native_ci():
    proof = {"schema": 1, "repository": REPOSITORY, "revision": SHA, "workflows": []}
    with pytest.raises(ValueError):
        gate["validate_proof"](proof, SHA)
    with pytest.raises(ValueError):
        gate["validate_proof"](proof, "b" * 40)


def test_release_proof_preserves_successful_jobs_source_and_repository():
    runs, jobs = evidence()
    native = verify(runs, jobs)
    general = copy.deepcopy(native)
    general["workflow"] = "ci.yml"
    general["jobs"] = [
        {**native["jobs"][0], "id": index, "name": name}
        for index, name in enumerate([
            "client (ubuntu-24.04)", "client (windows-latest)", "trixie-arm64",
            "windows-host", "scripts", "security",
        ], 1)
    ]
    proof = {"schema": 1, "repository": REPOSITORY, "revision": SHA,
             "workflows": [general, native]}
    gate["validate_proof"](proof, SHA, REPOSITORY)
    for field, value in [("revision", "b" * 40), ("conclusion", "skipped")]:
        altered = copy.deepcopy(proof)
        altered["workflows"][1]["jobs"][1][field] = value
        with pytest.raises(ValueError):
            gate["validate_proof"](altered, SHA, REPOSITORY)
    with pytest.raises(ValueError):
        gate["validate_proof"](proof, SHA, "someone/fork")
