from pathlib import Path
import os

import nibabel as nib
import numpy as np
import pytest

from pyfacewipe import PyFaceWipe

# Skip this entire module during CI wheel builds (when pytest marker filtering doesn't work reliably)
if os.getenv("CIBW_BUILD", ""):
    pytest.skip("Skipping slow end-to-end tests during wheel builds", allow_module_level=True)

TEST_DIR = Path(__file__).parent
ORIG_DIR = TEST_DIR / "scans_orig"
REF_DIR = TEST_DIR / "scans_defaced"


@pytest.mark.slow
@pytest.mark.parametrize("name", ["axT2", "3dT1"])
def test_deface_matches_reference(name, tmp_path):
    src = ORIG_DIR / f"{name}.nii.gz"
    ref = REF_DIR / f"{name}_reference_defaced.nii.gz"

    PyFaceWipe().deface(source=src, output_dir=tmp_path)

    out = tmp_path / src.name
    assert out.exists(), f"Expected output not created: {out}"

    ref_img = nib.load(str(ref))
    out_img = nib.load(str(out))
    ref_data = np.asanyarray(ref_img.dataobj)
    out_data = np.asanyarray(out_img.dataobj)

    assert out_data.shape == ref_data.shape, "Output shape differs from reference"

    diff = out_data != ref_data
    n_diff = int(diff.sum())
    if n_diff:
        idx = np.argwhere(diff)
        raise AssertionError(
            f"{n_diff} of {diff.size} voxels differ from reference "
            f"({100 * n_diff / diff.size:.4f}%). "
            f"Bounding box of changes: min={idx.min(axis=0).tolist()} "
            f"max={idx.max(axis=0).tolist()}. First differing voxels: "
            f"{[tuple(i) for i in idx[:5].tolist()]}"
        )

    assert np.allclose(out_img.affine, ref_img.affine), "Affine differs from reference"
