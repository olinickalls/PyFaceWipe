#!/usr/bin/env python

import re
import pathlib

from setuptools import setup, find_packages
from setuptools.extension import Extension


requirements = [
    'torch',
    'numpy',
    'scipy',
    'nibabel',
    'medio',
    'scikit-image',
    'Pillow',
    'xxhash',
]


# base source directory
base_dir = pathlib.Path(__file__).parent.resolve()

# we don't want to require cython for package install from
# source distributions, like pypi installs, and the best way I
# can think of to detect this is by checking if PKG-INFO exists
cython_build = not base_dir.joinpath('PKG-INFO').is_file()

# configure c extensions
ext = 'pyx' if cython_build else 'c'
ext_opts = dict(extra_compile_args=['-O3', '-std=c99'])
extensions = [
    Extension('pyfacewipe.surfa.image.interp', [f'pyfacewipe/surfa/image/interp.{ext}'], **ext_opts),
#    Extension('pyfacewipe.surfa.mesh.intersection', [f'pyfacewipe/surfa/mesh/intersection.{ext}'], **ext_opts),
]

# if building locally or installing from somewhere that isn't
# an sdist, like directly from github, we'll want to cythonize
# the pyx files, so cython is a hard requirement here
if cython_build:
    from Cython.Build import cythonize
    extensions = cythonize(extensions, compiler_directives={'language_level' : '3'})

# since we interface the c stuff with numpy, it's another hard
# requirement at build-time
import numpy as np
include_dirs = [np.get_include()]

# extract the current version
init_file = base_dir.joinpath('pyfacewipe/__init__.py')
init_text = open(init_file, 'rt').read()
pattern = r"^__version__ = ['\"]([^'\"]*)['\"]"
match = re.search(pattern, init_text, re.M)
if not match:
    raise RuntimeError(f'Unable to find __version__ in {init_file}.')
version = match.group(1)

long_description = '''PyFaceWipe is a fast robust MRI defacer for multiple different
MRI sequences. It is powered by a skullstrip by SynthStrip.
If you use PyFaceWipe in your analysis, please cite:

PyFaceWipe: a new defacing tool for almost any MRI contrast.
Magn Reson Mater Phy (2024).
https://doi.org/10.1007/s10334-024-01170-x
'''

# run setup
setup(
    name='PyFaceWipe',
    version=version,
    description='MRI defacer for multiple sequences.',
    long_description=long_description,
    author='Oliver Nickalls',
    author_email='oliver.james.nickalls@singhealth.com.sg',
    url='https://doi.org/10.1007/s10334-024-01170-x',
    python_requires='>=3.6',
    packages=find_packages(),
    ext_modules=extensions,
    include_dirs=include_dirs,
    include_package_data=True,
    package_data={
        'pyfacewipe': ['models/*.pt'],
        'pyfacewipe.surfa.image': ['*.pyx', '*.h', '*.c'],
    },
    install_requires=requirements,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Natural Language :: English',
        'Topic :: Scientific/Engineering',
    ],
)
