__all__ = ["main.PyFaceWipe"]

from ._version import __version__

try:
    import torch  # noqa: F401
except ModuleNotFoundError as exc:
    if exc.name != "torch":
        raise
    raise ImportError(
        "PyFaceWipe needs PyTorch, which is not installed. For the small CPU-only build, run:\n"
        "    uv pip install torch --extra-index-url https://download.pytorch.org/whl/cpu\n"
        "or, with pip:\n"
        "    pip install torch --extra-index-url https://download.pytorch.org/whl/cpu\n"
        "or install the CUDA package instead: pip install pyfacewipe-cuda"
    ) from None

from .main import PyFaceWipe
