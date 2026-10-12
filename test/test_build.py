import importlib
from importlib.util import find_spec
from pathlib import Path

import pytest


def test_cython_extension_is_compiled():
    interp = importlib.import_module("pyfacewipe.surfa.image.interp")
    assert interp.__file__.endswith((".pyd", ".so")), (
        f"interp was not loaded as a compiled extension: {interp.__file__}"
    )


@pytest.mark.parametrize("name", ["synthstrip.1.pt", "synthstrip.nocsf.1.pt"])
def test_model_weights_are_packaged(name):
    weights = Path(find_spec("pyfacewipe").origin).parent / "models" / name
    assert weights.is_file(), f"Model weights are missing: {name}"
