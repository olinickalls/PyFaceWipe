import importlib
from importlib.util import find_spec
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "pyfacewipe.surfa.image.interp",
        "pyfacewipe.surfa.mesh.intersection",
    ],
)
def test_cython_extension_is_compiled(module_name):
    module = importlib.import_module(module_name)
    assert module.__file__.endswith((".pyd", ".so")), (
        f"{module_name} was not loaded as a compiled extension: {module.__file__}"
    )


@pytest.mark.parametrize("name", ["synthstrip.1.pt", "synthstrip.nocsf.1.pt"])
def test_model_weights_are_packaged(name):
    weights = Path(find_spec("pyfacewipe").origin).parent / "models" / name
    assert weights.is_file(), f"Model weights are missing: {name}"
