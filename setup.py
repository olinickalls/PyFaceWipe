#!/usr/bin/env python
"""
setup.py — dynamic build configuration only.

All static package metadata lives in pyproject.toml.  This file exists
solely to declare the Cython extension, which setuptools.build_meta
cannot express purely in TOML.  Cython is guaranteed to be present at
build time via [build-system].requires in pyproject.toml, so we always
cythonize from the .pyx source rather than shipping pre-generated .c files.
"""

import sys

from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import cythonize
import numpy as np

# Compiler flags: MSVC (Windows) uses /O2; GCC/Clang use -O3 -std=c99.
if sys.platform == "win32":
    extra_compile_args = ["/O2"]
else:
    extra_compile_args = ["-O3", "-std=c99"]

extensions = [
    Extension(
        "pyfacewipe.surfa.image.interp",
        ["src/pyfacewipe/surfa/image/interp.pyx"],
        extra_compile_args=extra_compile_args,
    ),
]

setup(
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": "3"},
    ),
    include_dirs=[np.get_include()],
)
