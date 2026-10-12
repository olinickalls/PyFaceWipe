"""Publish verified build artifacts without replacing release assets by default."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import quote


ARTIFACTS = {
    "wheels-cpu-Linux": "*.whl",
    "wheels-cuda-Linux": "*.whl",
    "wheels-cpu-Windows": "*.whl",
    "wheels-cpu-macOS": "*.whl",
    "sdist": "*.tar.gz",
}

BUILD_WORKFLOWS = {
    ".github/workflows/build-wheels.yml",
    ".github/workflows/build-wheels-and-store-assets.yml",
}


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True)


def api(repo, path):
    return json.loads(gh("api", f"repos/{repo}/{path}"))


def tag_commit(repo, tag):
    subprocess.run(["git", "check-ref-format", f"refs/tags/{tag}"], check=True)
    if not tag.startswith("v"):
        raise ValueError("Release tag must start with v")
    obj = api(repo, f"git/ref/tags/{quote(tag, safe='/')}")["object"]
    while obj["type"] == "tag":
        obj = api(repo, f"git/tags/{obj['sha']}")["object"]
    if obj["type"] != "commit":
        raise ValueError("Release tag does not point to a commit")
    return obj["sha"]


def validate_run(run, run_id, current_run_id, source_sha):
    if run["path"].split("@", 1)[0] not in BUILD_WORKFLOWS:
        raise ValueError("Artifacts must come from a trusted wheel build workflow")
    if run["event"] not in {"push", "workflow_dispatch"}:
        raise ValueError("Artifacts must come from a push or manual build")
    current_build = (
        run_id == current_run_id and bool(source_sha) and run["status"] == "in_progress"
    )
    if not current_build and (
        run["status"] != "completed" or run["conclusion"] != "success"
    ):
        raise ValueError("Backfills require a successfully completed build")


def validate_source(run, commit, tag, provenance, source_sha):
    if source_sha and source_sha != commit:
        raise ValueError("Build source does not match the release tag")
    if provenance is not None:
        if provenance["sha"] != commit or provenance["tag"] not in {"", tag}:
            raise ValueError("Recorded build source does not match the release tag")
        if run["event"] != "workflow_dispatch" and run["head_sha"] != commit:
            raise ValueError("Build commit does not match the release tag")
    elif source_sha or run["head_sha"] != commit:
        raise ValueError("Build commit does not match the release tag")


def collect_assets(root):
    assets = []
    for name, pattern in ARTIFACTS.items():
        files = sorted((root / name).glob(pattern))
        if not files:
            raise ValueError(f"Missing distributions in artifact {name}")
        if any(not path.is_file() or path.stat().st_size == 0 for path in files):
            raise ValueError(f"Empty or invalid distribution in artifact {name}")
        assets.extend(files)
    names = [path.name for path in assets]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate distribution filenames across artifacts")
    return assets


def upload_assets(repo, tag, assets, release, replace_existing=False):
    existing = {asset["name"] for asset in release["assets"]}
    for path in assets:
        if path.name in existing and not replace_existing:
            print(f"Preserving existing asset: {path.name}")
            continue
        args = ["release", "upload", tag, str(path), "--repo", repo]
        if replace_existing:
            args.append("--clobber")
        gh(*args)


def publish(repo, tag, run_id, source_sha="", replace_existing=False, draft=False):
    if not run_id.isdecimal():
        raise ValueError("Build run ID must be numeric")
    commit = tag_commit(repo, tag)
    run = api(repo, f"actions/runs/{run_id}")
    validate_run(run, run_id, os.environ.get("GITHUB_RUN_ID", ""), source_sha)
    available = api(repo, f"actions/runs/{run_id}/artifacts?per_page=100")["artifacts"]
    names = {artifact["name"] for artifact in available if not artifact["expired"]}
    missing = ARTIFACTS.keys() - names
    if missing:
        raise ValueError(f"Missing or expired artifacts: {', '.join(sorted(missing))}")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        provenance = None
        if "release-source" in names:
            gh("run", "download", run_id, "--repo", repo, "--name", "release-source",
               "--dir", str(root / "release-source"))
            provenance = json.loads(
                (root / "release-source" / "release-source.json").read_text()
            )
        validate_source(run, commit, tag, provenance, source_sha)
        for name in ARTIFACTS:
            gh("run", "download", run_id, "--repo", repo, "--name", name,
               "--dir", str(root / name))
        assets = collect_assets(root)

        # Check again after downloading so a moved tag cannot silently target another commit.
        if tag_commit(repo, tag) != commit:
            raise ValueError("Release tag moved during publishing")
        releases = json.loads(gh(
            "api", "--paginate", "--slurp", f"repos/{repo}/releases?per_page=100"
        ))
        release = next(
            (release for page in releases for release in page if release["tag_name"] == tag),
            None,
        )
        if release is None:
            args = ["release", "create", tag, "--repo", repo, "--verify-tag",
                    "--title", tag, "--generate-notes"]
            if draft:
                args.append("--draft")
            gh(*args)
            release = {"assets": []}
        upload_assets(repo, tag, assets, release, replace_existing)


if __name__ == "__main__":
    publish(
        os.environ["GITHUB_REPOSITORY"],
        os.environ["RELEASE_TAG"],
        os.environ["BUILD_RUN_ID"],
        source_sha=os.environ.get("SOURCE_SHA", ""),
        replace_existing=os.environ.get("REPLACE_EXISTING") == "true",
        draft=os.environ.get("DRAFT") == "true",
    )
