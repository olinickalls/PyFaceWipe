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

* NumPy 1.x only (`numpy<2`), so Python 3.13+ is not supported yet. NumPy 2 support depends on updating the vendored `surfa` package. This is due for the next release.

### CPU vs CUDA PyTorch

From a checkout, `uv run` installs the small CPU-only PyTorch on Linux (from `download.pytorch.org/whl/cpu`).

Published packages come in two variants with the same `pyfacewipe` import package (install only one):

| Package | Linux torch | Install |
|---|---|---|
| `pyfacewipe` | Not installed automatically (keeps the default install small) | `uv pip install pyfacewipe torch --extra-index-url https://download.pytorch.org/whl/cpu` (or `pip install ...`) |
| `pyfacewipe-cuda` | Default CUDA build from PyPI (about 3 GB) | `uv pip install pyfacewipe-cuda` (or `pip install ...`) |

On Windows and macOS, PyPI torch is CPU-only, so `pip install pyfacewipe` installs everything.

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


## Publishing GitHub release assets

These workflows attach distributions to GitHub Releases; they do not publish to PyPI.

### New releases

1. Update `version` in `pyproject.toml`, commit, and create and push the matching
   version tag (for example `v0.1.3`).
2. Pushing a `v*` tag automatically starts **Build Wheels and Store Assets**, which
   calls **Build Wheels** to build and test the CPU wheels for Linux, Windows and
   macOS, the Linux CUDA wheels, and the source distribution.
3. Only after all builds succeed, the publishing job creates or updates the
   tagged release and uploads its distributions. Ordinary branch builds only
   save Actions artifacts; they do not publish releases.

### Build and store assets for an existing tag

Open **Actions → Build Wheels and Store Assets → Run workflow**, select `main`,
enter the existing `release_tag` (for example `v0.1.2`), and run. No build run ID
or source SHA is needed. This creates fresh distributions from the tag's immutable
commit and uploads those exact artifacts from the same run after every build
succeeds. The publisher verifies the recorded source against the tag and rejects
moved tags before changing the release.

**Build Wheels** remains available for standalone builds and normal branch CI.
Its manual dispatch now builds the selected tag and saves Actions artifacts only;
it no longer publishes. Tag pushes run only the new orchestration workflow, avoiding
duplicate builds and uploads.

### Advanced backfill using existing artifacts

If artifacts are still available, open **Actions → Release Assets → Run workflow**.
Select `main` (which contains the current publishing workflow), enter the exact
`release_tag`, such as `v0.1.2`, and a successful **Build Wheels** or
**Build Wheels and Store Assets** `build_run_id`
(the number in its `/actions/runs/<number>` URL).

The publisher checks that the run belongs to one of this repository's trusted build workflows,
succeeded, and built the commit currently referenced by the tag. New builds record
their checked-out source in a `release-source` artifact; older builds are checked
against the run's commit. All four wheel artifacts and the source distribution must
be available and nonempty. Missing/expired artifacts cause an error before any
release is changed. Supplying a source SHA cannot substitute for missing provenance
or make artifacts from the wrong commit valid; use a fresh build instead.

Alternatively, download and extract the artifacts from that verified build run
and attach the missing `.whl` files using the release's **Edit** page.

### Rebuild when artifacts have expired

Open **Actions → Build Wheels and Store Assets → Run workflow**, select `main`, and enter the
existing `release_tag`. The build checks out that tag's commit, not `main`, then
builds, tests and publishes its distributions. Manual rebuilds require the tagged
commit to be reachable from the default branch, so unmerged code cannot run in
that branch's cache context. Build commands also have Actions runtime/cache
credentials cleared. The tagged source must support the
current build steps, including `scripts/set_variant.py` and the package layout.
Tags predating that build layout may need a version-specific build process.
Do not move an existing release tag to newer code just to rebuild it.

Both publishing workflows preserve existing assets by default. Enable
`replace_existing` only when deliberately replacing files with matching names.
The optional `draft` setting applies only when creating a release; it never
changes an existing release's publication status. Inspect a draft before publishing
it through GitHub's release UI. Publishing is serialized per release tag, and only
the publishing job has release-write permission.

If publishing fails after a successful build, rerun the failed publishing job;
the default missing-only uploads safely resume a partial upload.

## Release History

* 0.1
    * Alpha - as published in Magn Reson Mater Phy (2024)
* 0.1.1
    * CHANGE: Refactor into a class. No change to algorithm.
    * CHANGE: Update docs

## Meta

Oliver Nickalls – Oliver.James.Nickalls@SingHealth.com.sg

Distributed for review and research purposes only. Not for commercial use.
