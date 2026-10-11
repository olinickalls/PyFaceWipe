from scripts.set_variant import main


def test_cpu_variant_removes_torch_from_linux_dependency(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('"torch>=2.6",', encoding="utf-8")

    main("cpu")

    assert pyproject.read_text(encoding="utf-8") == '"torch>=2.6; sys_platform != \'linux\'",'
