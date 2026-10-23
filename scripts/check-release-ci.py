"""Require successful general and native push workflows for one exact main SHA."""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

WORKFLOWS = {
    "ci.yml": {
        "client (ubuntu-24.04)", "client (windows-latest)", "trixie-arm64",
        "windows-host", "scripts", "security",
    },
    "rust.yml": {"native (ubuntu-24.04, amd64)", "native (ubuntu-24.04-arm, arm64)"},
}


def api(repository, endpoint, **query):
    command = ["gh", "api", "--hostname", "github.com", "--method", "GET",
               f"repos/{repository}/{endpoint}"]
    for name, value in query.items():
        command.extend(["-f", f"{name}={value}"])
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=45)
    if result.returncode or len(result.stdout) > 4 * 1024 * 1024:
        raise ValueError("GitHub workflow evidence unavailable; publication remains blocked")
    return json.loads(result.stdout)


def verify_workflow(repository, sha, workflow, runs, jobs_for_run):
    entries = runs.get("workflow_runs", [])
    if not entries or runs.get("total_count") != len(entries):
        raise ValueError(f"{workflow}: workflow missing or result set incomplete")
    latest = max(entries, key=lambda run: run["id"])
    if (
        latest.get("head_sha") != sha or latest.get("head_branch") != "main"
        or latest.get("event") != "push"
        or latest.get("path") != f".github/workflows/{workflow}"
        or latest.get("repository", {}).get("full_name") != repository
        or latest.get("head_repository", {}).get("full_name") != repository
        or latest.get("status") != "completed" or latest.get("conclusion") != "success"
        or not isinstance(latest.get("id"), int) or latest["id"] <= 0
    ):
        raise ValueError(f"{workflow}: latest run is not a successful matching main push")
    jobs = jobs_for_run(latest["id"])
    entries = jobs.get("jobs", [])
    if (
        jobs.get("total_count") != len(entries)
        or not WORKFLOWS[workflow].issubset({job.get("name") for job in entries})
        or any(job.get("head_sha") != sha or job.get("status") != "completed"
               or job.get("conclusion") != "success" for job in entries)
    ):
        raise ValueError(f"{workflow}: required jobs missing, incomplete or unsuccessful")
    return {
        "workflow": workflow, "run_id": latest["id"], "revision": sha,
        "run_attempt": latest.get("run_attempt"),
        "status": "completed", "conclusion": "success",
        "jobs": [{"name": job["name"], "id": job["id"], "revision": sha,
                  "status": job["status"], "conclusion": job["conclusion"]} for job in entries],
    }


def validate_proof(proof, sha, repository=None):
    """Validate offline provenance structure; the publisher still queries GitHub live."""
    if proof.get("schema") != 1 or proof.get("revision") != sha:
        raise ValueError("CI proof source revision mismatch")
    if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", proof.get("repository", ""))
            or (repository is not None and proof["repository"] != repository)):
        raise ValueError("CI proof repository mismatch")
    workflows = proof.get("workflows", [])
    if len(workflows) != len(WORKFLOWS) or {p.get("workflow") for p in workflows} != set(WORKFLOWS):
        raise ValueError("General or native CI proof missing")
    for item in workflows:
        if (item.get("revision") != sha or item.get("status") != "completed"
                or item.get("conclusion") != "success"
                or not isinstance(item.get("run_id"), int) or item["run_id"] <= 0):
            raise ValueError("Unsuccessful or mismatching CI proof")
        jobs = item.get("jobs", [])
        if (not WORKFLOWS[item["workflow"]].issubset({job.get("name") for job in jobs})
                or any(job.get("revision") != sha or job.get("status") != "completed"
                       or job.get("conclusion") != "success" for job in jobs)):
            raise ValueError("Required CI job proof missing or unsuccessful")


def check(repository, sha):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("A public GitHub OWNER/REPOSITORY is required")
    if not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise ValueError("A complete source revision is required")
    proofs = []
    for workflow in WORKFLOWS:
        runs = api(repository, f"actions/workflows/{workflow}/runs",
                   head_sha=sha, event="push", branch="main", per_page=100)
        proofs.append(verify_workflow(
            repository, sha, workflow, runs,
            lambda run_id: api(repository, f"actions/runs/{run_id}/jobs",
                               filter="latest", per_page=100),
        ))
    return {"schema": 1, "repository": repository, "revision": sha, "workflows": proofs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"), required=False)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        proof = check(args.repository or "", args.sha)
        validate_proof(proof, args.sha, args.repository)
    except (ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        raise SystemExit(f"Release CI withheld: {error}") from error
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: general and native CI succeeded for {args.sha}; all required jobs verified.")


if __name__ == "__main__":
    main()
