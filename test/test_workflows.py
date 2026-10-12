from pathlib import Path


def test_cibuildwheel_references_are_pinned_consistently():
    workflows = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    references = [
        line.strip()
        for workflow in workflows.iterdir()
        if workflow.suffix in {".yml", ".yaml"}
        for line in workflow.read_text(encoding="utf-8").splitlines()
        if "cibuildwheel" in line
    ]

    assert references
    assert all(
        line == "uses: pypa/cibuildwheel@v2.23.4"
        or line == "run: python -m pip install cibuildwheel==2.23.4"
        for line in references
    )


def test_wheel_builds_only_run_lightweight_build_tests():
    workflow = (
        Path(__file__).resolve().parents[1] / ".github/workflows/build-wheels.yml"
    ).read_text(encoding="utf-8")
    assert "CIBW_TEST_COMMAND: 'pytest {project}/test/test_build.py'" in workflow
    assert "test_end_to_end" not in workflow


def test_release_publishing_depends_on_all_builds_and_only_targets_tags():
    workflow = (
        Path(__file__).resolve().parents[1] / ".github/workflows/build-wheels.yml"
    ).read_text(encoding="utf-8")
    publishing = workflow.split("  publish_release:\n", 1)[1]
    assert "needs: [source, build_wheels, build_sdist]" in publishing
    assert "if: needs.source.outputs.tag != ''" in publishing
    assert "uses: ./.github/workflows/release-assets.yml" in publishing
    assert "source_sha: ${{ needs.source.outputs.sha }}" in publishing
    assert workflow.count("ref: ${{ needs.source.outputs.sha }}") == 2
    assert workflow.count("if-no-files-found: error") == 3
    assert workflow.count("contents: write") == 1
    assert 'git merge-base --is-ancestor HEAD "refs/remotes/origin/$DEFAULT_BRANCH"' in workflow
    assert workflow.count('ACTIONS_RUNTIME_TOKEN: ""') == 3


def test_backfill_has_explicit_inputs_and_serialized_publishing():
    workflow = (
        Path(__file__).resolve().parents[1] / ".github/workflows/release-assets.yml"
    ).read_text(encoding="utf-8")
    assert "  push:" not in workflow
    assert "  workflow_dispatch:" in workflow
    assert "  workflow_call:" in workflow
    assert workflow.count("      release_tag:") == 2
    assert workflow.count("      build_run_id:") == 2
    assert "group: release-assets-${{ inputs.release_tag }}" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "persist-credentials: false" in workflow
