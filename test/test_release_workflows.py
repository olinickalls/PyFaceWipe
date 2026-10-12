from pathlib import Path

import pytest


@pytest.fixture
def workflows():
    yaml = pytest.importorskip("yaml")
    directory = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    return {
        name: yaml.load((directory / name).read_text(), Loader=yaml.BaseLoader)
        for name in (
            "build-wheels.yml", "build-wheels-and-store-assets.yml", "release-assets.yml",
        )
    }


def test_release_orchestration_reuses_build_and_publishes_same_run(workflows):
    workflow = workflows["build-wheels-and-store-assets.yml"]
    assert workflow["name"] == "Build Wheels and Store Assets"
    assert workflow["on"]["push"] == {"tags": ["v*"]}
    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert inputs["release_tag"]["required"] == "true"
    assert inputs["replace_existing"]["default"] == "false"
    assert inputs["draft"]["default"] == "false"
    assert set(inputs) == {"release_tag", "replace_existing", "draft"}
    assert workflow["permissions"] == {"contents": "read"}
    build = workflow["jobs"]["build"]
    assert build["uses"] == "./.github/workflows/build-wheels.yml"
    assert build["permissions"] == {"contents": "read"}
    assert build["with"]["release_tag"] == "${{ inputs.release_tag || github.ref_name }}"
    publish = workflow["jobs"]["publish_release"]
    assert publish["needs"] == "build"
    assert "if" not in publish
    assert publish["uses"] == "./.github/workflows/release-assets.yml"
    assert publish["permissions"] == {"actions": "read", "contents": "write"}
    assert publish["with"]["build_run_id"] == "${{ github.run_id }}"
    assert publish["with"]["source_sha"] == "${{ needs.build.outputs.source_sha }}"
    assert publish["with"]["release_tag"] == "${{ needs.build.outputs.release_tag }}"


def test_reusable_build_preserves_ci_source_and_all_distributions(workflows):
    workflow = workflows["build-wheels.yml"]
    assert workflow["on"]["push"] == {"branches": ["main", "v0.*", "v1.*"]}
    call = workflow["on"]["workflow_call"]
    assert call["inputs"]["release_tag"]["required"] == "true"
    assert call["outputs"]["source_sha"]["value"] == "${{ jobs.source.outputs.sha }}"
    assert call["outputs"]["release_tag"]["value"] == "${{ jobs.source.outputs.tag }}"
    assert workflow["permissions"] == {"contents": "read"}
    assert set(workflow["jobs"]) == {"source", "build_wheels", "build_sdist"}
    source = workflow["jobs"]["source"]
    steps = {step.get("name"): step for step in source["steps"]}
    assert steps["Validate release tag"]["if"] == (
        "inputs.release_tag != '' || github.event_name == 'workflow_dispatch'"
    )
    assert 'git check-ref-format "refs/tags/$RELEASE_TAG"' in steps["Validate release tag"]["run"]
    reviewed = steps["Require reviewed source for manual rebuilds"]
    assert reviewed["if"] == "github.event_name == 'workflow_dispatch'"
    assert reviewed["run"] == 'git merge-base --is-ancestor HEAD "refs/remotes/origin/$DEFAULT_BRANCH"'
    assert steps["Verify pushed tag source"]["if"] == (
        "github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')"
    )
    assert steps["Verify pushed tag source"]["env"]["PUSH_SHA"] == "${{ github.sha }}"
    assert '$PUSH_SHA^{commit}' in steps["Verify pushed tag source"]["run"]
    checkout = next(step for step in source["steps"] if step.get("uses") == "actions/checkout@v4")
    assert checkout["with"]["ref"] == (
        "${{ inputs.release_tag && format('refs/tags/{0}', inputs.release_tag) || github.sha }}"
    )
    assert checkout["with"]["fetch-depth"] == "0"
    for name in ("build_wheels", "build_sdist"):
        job = workflow["jobs"][name]
        assert job["needs"] == "source"
        assert "permissions" not in job
        checkout = next(step for step in job["steps"] if step.get("uses") == "actions/checkout@v4")
        assert checkout["with"]["ref"] == "${{ needs.source.outputs.sha }}"
        assert checkout["with"]["persist-credentials"] == "false"
    wheels = workflow["jobs"]["build_wheels"]
    assert wheels["strategy"]["matrix"]["include"] == [
        {"os": "ubuntu-latest", "variant": "cpu"},
        {"os": "ubuntu-latest", "variant": "cuda"},
        {"os": "windows-latest", "variant": "cpu"},
        {"os": "macos-14", "variant": "cpu"},
    ]
    assert any(step.get("name") == "Verify wheels contain model weights" for step in wheels["steps"])
    assert any(step.get("with", {}).get("name") == "release-source" for step in source["steps"])


def test_publisher_retains_tag_serialization_and_permission_propagation(workflows):
    workflow = workflows["release-assets.yml"]
    assert workflow["on"]["workflow_call"]["inputs"]["source_sha"]["required"] == "true"
    publish = workflow["jobs"]["publish_release"]
    assert publish["permissions"] == {"actions": "read", "contents": "write"}
    assert publish["concurrency"] == {
        "group": "release-assets-${{ inputs.release_tag }}", "cancel-in-progress": "false",
    }
    assert publish["steps"][0]["with"]["ref"] == "${{ github.workflow_sha }}"
