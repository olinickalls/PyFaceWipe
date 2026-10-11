# PyFaceWipe

## Oliver Nickalls (2024) oliver.james.nickalls@singhealth.com.sg

> A python defacing tool for almost any MRI contrast.  (It also does CT)

Free for non-commercial use only. Free for personal use, and non-commercial research use. If in doubt or to aquire a commercial license, please contact me.

PyFaceWipe was built to address problems of defacing MRI data within our
IT environment. Although developed with Windows in mind, it
will work just as well on MacOS and Linux.

Powered by a skullstrip with the excellent tool SynthStrip [https://github.com/nipreps/synthstrip], it is fast and robust,
while removing facial details just as well as the competition (if not better).

If you use PyFaceWipe in your work, please cite us:

<ul>
PyFaceWipe: A New Defacing Tool For Almost Any MRI Contrast.
Mitew, S., Yeow, L.Y., Ho, C.L., Bhanu, P.K.N., Nickalls, O.J. 
Magn Reson Mater Phy (2024).
[https://doi.org/10.1007/s10334-024-01170-x]
</ul>


## Prerequisites

Before you begin, ensure you have met the following requirements:
* Python 3.10 - 3.12.
* Windows, Linux & Mac supported, see [Platform notes](#platform-notes).
* NumPy 1.x is required (`numpy<2`) because of the vendored `surfa` package.

## Installation

PyFaceWipe is managed with [uv](https://docs.astral.sh/uv/). From a checkout, with no other setup:

```sh
uv run testrun.py
```

uv picks a supported Python (3.10 - 3.12), installs the right dependencies for your platform,
compiles the Cython extension, and runs the script. You need a C compiler for the compile
step (Visual Studio Build Tools on Windows, Xcode command line tools on macOS). On Debian/Ubuntu
(including a fresh WSL install, which has none) run `sudo apt install build-essential` first;
without it the build fails with `No such file or directory: 'cc'`.

To run the tests: `uv run pytest`

Without uv: `python -m pip install .` (Python 3.10 - 3.12).

## Platform notes

| Platform | Status |
|---|---|
| Windows x64 | Supported, tested. |
| Linux x86_64 | Supported. Needs glibc 2.28 or newer (Ubuntu 20.04+, Debian 10+), which current PyTorch requires. |
| macOS Apple Silicon | Supported. Wheels are built in CI. |
| macOS Intel (x86_64) | **Best effort.** Uses PyTorch 2.2.2 (see below). Not tested. |

* NumPy 1.x only (`numpy<2`), so Python 3.13+ is not supported yet. NumPy 2 support depends on updating the vendored `surfa` package. This is due for the next release.

### CPU vs CUDA PyTorch

From a checkout, `uv run` installs the small CPU-only PyTorch on Linux (from `download.pytorch.org/whl/cpu`).

Published packages come in two variants with the same `pyfacewipe` import package (install only one):

| Package | Linux torch | Install |
|---|---|---|
| `pyfacewipe` | Not installed automatically (keeps the default install small) | `uv pip install pyfacewipe torch --extra-index-url https://download.pytorch.org/whl/cpu` (or `pip install ...`) |
| `pyfacewipe-cuda` | Default CUDA build from PyPI (about 3 GB) | `uv pip install pyfacewipe-cuda` (or `pip install ...`) |

On Windows and macOS, PyPI torch is CPU-only, so `pip install pyfacewipe` installs everything.

### macOS Intel

PyTorch stopped publishing macOS x86_64 wheels after 2.2.2, so on Intel Macs `pyproject.toml`
automatically selects `torch==2.2.2` instead of `torch>=2.6`. The dependency resolution is
verified, but PyFaceWipe has not been run on an Intel Mac. Please report any problems.
Use Python 3.10 - 3.12 and install the Xcode command line tools (`xcode-select --install`).

## Quick Guide

It's quick & easy to get started:
```sh
from pyfacewipe import PyFaceWipe

pfw = PyFaceWipe()
pfw.deface(source=r"C:\myMRIsrc\anat\pt001.nii.gz", output_dir=r"c:\myMRIdefaced")
```

## GPU

To use hardware accelleration you'll need to install the appropriate GPU-enabled Torch version.
You can find the correct pip command at [https://pytorch.org/get-started/locally/].

It is easiest if you install the GPU Torch _before_ requirements.txt.

For example (you will need to edit this for your system)

```sh
python -m pip install torch --index-url https://download.pytorch.org/whl/cu118
python -m pip install -r requirements.txt
```


## Release History

* 0.1
    * Alpha - as published in Magn Reson Mater Phy (2024)
* 0.1.1
    * CHANGE: Refactor into a class. No change to algorithm.
    * CHANGE: Update docs

## Meta

Oliver Nickalls – Oliver.James.Nickalls@SingHealth.com.sg

Distributed for review and research purposes only. Not for commercial use.

