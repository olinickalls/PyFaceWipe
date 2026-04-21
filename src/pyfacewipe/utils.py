from pathlib import Path
# PyFaceWipe Miscellaneous utils.
#

def larger(a, b) -> int:
    '''
    returns the larger of the two srguments.
    '''
    if a > b:
        return a
    else:
        return b

    
def smaller(a, b) -> int:
    '''
    returns the larger of the two srguments.
    '''
    if a < b:
        return a
    else:
        return b


def get_filename_components(fp: Path):
    valid_extensions = ['.nii.gz', '.dcm', '.nii']
    stem = fp.stem
    # if the filename.stem ends with one of these then remove it
    
    for ext in valid_extensions:
        if stem[-len(ext):] == ext:
            print("\tfound:", ext, stem)
            return stem[:-len(ext)], (ext+fp.suffix)
    return stem, fp.suffix
