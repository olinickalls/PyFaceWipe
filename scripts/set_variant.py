"""Rewrite pyproject.toml in place for a published package variant (used by CI only).

cpu:  distribution "PyFaceWipe". On Linux it declares no torch dependency, so
      `pip install pyfacewipe` stays small and the user installs CPU torch themselves.
cuda: distribution "pyfacewipe-cuda". Declares torch everywhere (CUDA build from PyPI on Linux).

Both ship the identical `pyfacewipe` import package.
"""
import sys
from pathlib import Path

LINUX_TORCH = '"torch>=2.6; sys_platform != \'darwin\' or platform_machine != \'x86_64\'",'
CPU_TORCH = (
    '"torch>=2.6; sys_platform != \'linux\' and '
    '(sys_platform != \'darwin\' or platform_machine != \'x86_64\')",'
)


def main(variant: str) -> None:
    path = Path("pyproject.toml")
    text = path.read_text(encoding="utf-8")
    if variant == "cpu":
        if LINUX_TORCH not in text:
            raise SystemExit("torch dependency line not found")
        text = text.replace(LINUX_TORCH, CPU_TORCH)
    elif variant == "cuda":
        if 'name = "PyFaceWipe"' not in text:
            raise SystemExit("project name line not found")
        text = text.replace('name = "PyFaceWipe"', 'name = "pyfacewipe-cuda"')
    else:
        raise SystemExit("usage: set_variant.py cpu|cuda")
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
