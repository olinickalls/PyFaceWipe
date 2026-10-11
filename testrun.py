from pathlib import Path

from pyfacewipe import PyFaceWipe

print('Imported pyfacewipe.')

input_path = Path(r"./MRIsrc/3dT1.nii.gz")
if not input_path.exists():
    raise FileNotFoundError(f'File does not exist: "{input_path}"')
print(f'Source file/dir {input_path} exists.')

output_path = Path(r"./myMRIdefaced")
if not output_path.exists():
    output_path.mkdir(parents=True)
print(f'Output directory {output_path} is ready.')

pfw = PyFaceWipe()
print("Created PyFaceWipe instance.")

print(f'Defacing {input_path} into {output_path}...')
pfw.deface(source=input_path, output_dir=output_path)
print("Defacing completed.  Please review output for errors.")

