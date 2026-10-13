from pathlib import Path

from pyfacewipe import PyFaceWipe

print('Imported pyfacewipe.')

input_path = Path(r"./test/scans_orig/axT2.nii.gz")
# if not input_path.exists():
#     raise FileNotFoundError(f'File does not exist: "{input_path}"')
# print(f'Source file/dir {input_path} exists.')

# output_path = Path(r"./myMRIdefaced")
# if not output_path.exists():
#     output_path.mkdir(parents=True)
# print(f'Output directory {output_path} is ready.')

# pfw = PyFaceWipe()
# print("Created PyFaceWipe instance.")

# print(f'Defacing {input_path} into {output_path}...')
# pfw.deface(source=input_path, output_dir=output_path)
# print("Defacing completed.  Please review output for errors.")


import nibabel as nib
from pyfacewipe import surfa as sf
from pyfacewipe.surfa.io import protocol
from pyfacewipe.surfa.io.framed import array_io_protocols
from src.pyfacewipe.surfa.io.framed import NibabelObjIO

print(f'array_io_protocols: {array_io_protocols}')

fmt = 'nibabel'
print(f'fmt: {fmt}')

# 1. Load the image object from disk
nb_obj = nib.load(input_path)

# iop = protocol.find_protocol_by_name(array_io_protocols, fmt)
iop = NibabelObjIO()

image = sf.load_volume_from_nibabel(nb_obj)

print("Done.")
print(f"Loaded image: {image}")
print(f"  type {type(image)}")
