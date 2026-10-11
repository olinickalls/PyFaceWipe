# PyFaceWipe changes List

## Currently in fixes_for_linux branch
## Done

- Python version now set at `>=3.10,<3.13`

- PyTorch version 'pinned' at `>=2.6` for everyone except intel macOs (`==2.2.2`)

```
  # Intel Macs: PyTorch 2.2.2 is the last release with macOS x86_64 wheels.
  "torch>=2.6; sys_platform != 'darwin' or platform_machine != 'x86_64'",
  "torch==2.2.2; sys_platform == 'darwin' and platform_machine == 'x86_64'",
```

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

