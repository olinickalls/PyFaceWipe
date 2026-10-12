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
