from pathlib import Path
from pyfacewipe import PyFaceWipe
import shutil

# Set the root output directory.
output_dir = Path(r"C:\MRIBrain\defacedout")

# Delete the output directory each time
# try:
#     print('Cleaning output dir...', end='')
#     shutil.rmtree(output_dir)
#     print(f"{output_dir} removed successfully\n")
# except OSError as o:
#     print(f"Error, {o.strerror}: {output_dir}\n")

# Create the PyFaceWipe class instance
# To use GPU, please ensure you have the GPU-enabled Torch installed.
pfw = PyFaceWipe(use_gpu=False)

# Replace these with your MRI or CT volumes
test_filepaths = [
    Path(r"C:\MRIBrain\src\AxT2"),
    Path(r"C:\MRIBrain\src\cor_T1"),
    Path(r"C:\MRIBrain\src\cor_FLAIR"),
    Path(r"C:\MRIBrain\src\multiframe_sag_t1\multi_sag_t1.dcm"),
    Path(r"C:\MRIBrain\src\nii\corT1.nii.gz"),
]

for test_filepath in test_filepaths:
    pfw.deface(
        source=test_filepath,
        output_dir=output_dir,
        #    save_steps=True,
        #    remove_ears=False,
    )
