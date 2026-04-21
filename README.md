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
* You have at least python 3.7
* Windows, Linux & Mac supported.

## Installation

### New- Wheels coming soon! In the meantime... for Windows on x64

- Download and unpack the source into your project directory

- Install requirements
```sh
python -m pip install -r requirements.txt
```

- Go! (if you are running Windows on x64)

### MacOS and Linux (also a fallback for windows):
You may need to recompile with Cython:

```sh
python -m pip install cython
python setup.py  build_ext --inplace
```


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

