import json
from pathlib import Path

import pytest

from scripts import publish_release as publisher


def build_run(**overrides):
    run = {
        "path": ".github/workflows/build-wheels.yml",
        "event": "push",
        "head_sha": "commit",
        "status": "completed",
        "conclusion": "success",
    }
    return {**run, **overrides}


def test_successful_legacy_run():
    publisher.validate_run(build_run(), "123", "456", "")
    publisher.validate_source(build_run(), "commit", "v0.1.2", None, "")


@pytest.mark.parametrize("overrides", [
    {"path": ".github/workflows/other.yml"},
    {"event": "pull_request"},
    {"status": "in_progress"},
    {"conclusion": "failure"},
])
def test_backfill_rejects_invalid_run(overrides):
    with pytest.raises(ValueError):
        publisher.validate_run(build_run(**overrides), "123", "456", "")


def test_dependent_job_can_publish_current_running_build():
    publisher.validate_run(build_run(status="in_progress", conclusion=None),
                           "123", "123", "commit")
    with pytest.raises(ValueError):
        publisher.validate_run(build_run(status="in_progress", conclusion=None),
                               "123", "456", "commit")


def test_manual_build_uses_recorded_source_not_workflow_branch():
    publisher.validate_source(
        build_run(event="workflow_dispatch", head_sha="main"),
        "commit", "v0.1.2", {"sha": "commit", "tag": "v0.1.2"}, "commit",
    )


@pytest.mark.parametrize("run,provenance,sha", [
    (build_run(head_sha="other"), None, ""),
    (build_run(), {"sha": "other", "tag": "v0.1.2"}, ""),
    (build_run(), {"sha": "commit", "tag": "v0.1.1"}, ""),
    (build_run(), {"sha": "commit", "tag": "v0.1.2"}, "other"),
    (build_run(head_sha="other"), {"sha": "commit", "tag": "v0.1.2"}, ""),
    (build_run(), None, "commit"),
])
def test_source_mismatch_is_rejected(run, provenance, sha):
    with pytest.raises(ValueError):
        publisher.validate_source(run, "commit", "v0.1.2", provenance, sha)


def make_assets(root):
    for name, pattern in publisher.ARTIFACTS.items():
        directory = root / name
        directory.mkdir()
        (directory / pattern.replace("*", name)).write_bytes(b"distribution")


def test_all_distribution_groups_required(tmp_path):
    make_assets(tmp_path)
    assert len(publisher.collect_assets(tmp_path)) == 5
    next((tmp_path / "wheels-cpu-Linux").iterdir()).unlink()
    with pytest.raises(ValueError, match="Missing distributions"):
        publisher.collect_assets(tmp_path)


def test_empty_and_duplicate_assets_rejected(tmp_path):
    make_assets(tmp_path)
    file = next((tmp_path / "wheels-cpu-Linux").iterdir())
    file.write_bytes(b"")
    with pytest.raises(ValueError, match="Empty"):
        publisher.collect_assets(tmp_path)
    file.write_bytes(b"wheel")
    next((tmp_path / "wheels-cuda-Linux").iterdir()).rename(
        tmp_path / "wheels-cuda-Linux" / file.name
    )
    with pytest.raises(ValueError, match="Duplicate"):
        publisher.collect_assets(tmp_path)


@pytest.mark.parametrize("replace", [False, True])
def test_upload_preserves_assets_unless_replacement_requested(monkeypatch, replace):
    calls = []
    monkeypatch.setattr(publisher, "gh", lambda *args: calls.append(args))
    publisher.upload_assets(
        "owner/repo", "v0.1.2", [Path("existing.whl"), Path("missing.whl")],
        {"assets": [{"name": "existing.whl"}, {"name": "model.pt"}]}, replace,
    )
    assert len(calls) == (2 if replace else 1)
    assert all(("--clobber" in call) == replace for call in calls)
    assert "missing.whl" in calls[-1]


def test_annotated_tag_resolves_to_commit(monkeypatch):
    objects = iter([
        {"object": {"type": "tag", "sha": "annotated"}},
        {"object": {"type": "commit", "sha": "commit"}},
    ])
    monkeypatch.setattr(publisher, "api", lambda *args: next(objects))
    assert publisher.tag_commit("owner/repo", "v0.1.2") == "commit"


@pytest.mark.parametrize("tag", ["main", "vbad tag", "v../invalid"])
def test_invalid_tag_rejected(tag):
    with pytest.raises((ValueError, publisher.subprocess.CalledProcessError)):
        publisher.tag_commit("owner/repo", tag)


@pytest.mark.parametrize("expired", [False, True])
def test_missing_or_expired_artifact_fails_before_upload(monkeypatch, expired):
    calls = []
    monkeypatch.setattr(publisher, "tag_commit", lambda *args: "commit")
    monkeypatch.setattr(publisher, "gh", lambda *args: calls.append(args))
    artifacts = [
        {"name": name, "expired": expired}
        for name in publisher.ARTIFACTS if name != "sdist" or expired
    ]
    monkeypatch.setattr(publisher, "api", lambda repo, path:
                        {"artifacts": artifacts} if "artifacts?" in path else build_run())
    with pytest.raises(ValueError, match="Missing or expired"):
        publisher.publish("owner/repo", "v0.1.2", "123")
    assert not calls


@pytest.mark.parametrize("existing_release", [False, True])
def test_publish_downloads_verified_run_and_handles_draft(monkeypatch, existing_release):
    calls = []
    monkeypatch.setattr(publisher, "tag_commit", lambda *args: "commit")
    artifacts = [{"name": name, "expired": False} for name in publisher.ARTIFACTS]
    monkeypatch.setattr(publisher, "api", lambda repo, path:
                        {"artifacts": artifacts} if "artifacts?" in path else build_run())

    def gh(*args):
        calls.append(args)
        if args[:2] == ("run", "download"):
            name = args[args.index("--name") + 1]
            root = Path(args[args.index("--dir") + 1])
            root.mkdir()
            (root / publisher.ARTIFACTS[name].replace("*", name)).write_bytes(b"wheel")
        if args[0] == "api":
            release = {"tag_name": "v0.1.2", "assets": [{"name": "sdist.tar.gz"}]}
            return json.dumps([[release] if existing_release else []])
        return ""

    monkeypatch.setattr(publisher, "gh", gh)
    publisher.publish("owner/repo", "v0.1.2", "123", draft=True)
    downloads = [call for call in calls if call[:2] == ("run", "download")]
    assert len(downloads) == 5
    assert all(call[2] == "123" for call in downloads)
    creates = [call for call in calls if call[:2] == ("release", "create")]
    assert len(creates) == (0 if existing_release else 1)
    if creates:
        assert "--draft" in creates[0] and "--verify-tag" in creates[0]
    uploads = [call for call in calls if call[:2] == ("release", "upload")]
    assert len(uploads) == (4 if existing_release else 5)


def test_moved_tag_fails_before_release_changes(monkeypatch):
    commits = iter(["commit", "moved"])
    monkeypatch.setattr(publisher, "tag_commit", lambda *args: next(commits))
    monkeypatch.setattr(publisher, "api", lambda repo, path:
                        {"artifacts": [{"name": name, "expired": False}
                                       for name in publisher.ARTIFACTS]}
                        if "artifacts?" in path else build_run())
    calls = []

    def gh(*args):
        calls.append(args)
        name = args[args.index("--name") + 1]
        root = Path(args[args.index("--dir") + 1])
        root.mkdir()
        (root / publisher.ARTIFACTS[name].replace("*", name)).write_bytes(b"wheel")
        return ""

    monkeypatch.setattr(publisher, "gh", gh)
    with pytest.raises(ValueError, match="tag moved"):
        publisher.publish("owner/repo", "v0.1.2", "123")
    assert all(call[0] == "run" for call in calls)
