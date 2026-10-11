import importlib


def test_cython_extension_is_compiled():
    interp = importlib.import_module("pyfacewipe.surfa.image.interp")
    assert interp.__file__.endswith((".pyd", ".so")), (
        f"interp was not loaded as a compiled extension: {interp.__file__}"
    )
