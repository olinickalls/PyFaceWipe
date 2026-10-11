# PyFaceWipe changes List

## Currently in fixes_for_linux branch
## Done

- Python version now set at `>=3.10,<3.13`

- PyTorch dependency is `torch>=2.6` across supported platforms.

- `os.environ("COMPUTERNAME")` Windows only- changed to `platform.node()`

- NiBabel 5+ compatibility (temp fix pending merging in new surfa changes)


## Pending
- Model weights not in wheels - to check in CI 

- Surfa package update

- Fix Numpy 2+ compatibility
    - `np.bool8` removed (numpy 2.0)
    - `np.in1d` removed (numpy 2.0)
    - `np.int alias` removed (numpy 1.24)
    - `np.percentile(interpolation=...)` renamed to `method=` (numpy 1.22) and removed (2.0)

- Investigate `scipy.ndimage.find_objects` issue - related to numpy2?
