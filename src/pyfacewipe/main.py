import os
from pathlib import Path
from .synthstrip_class import SynthStrip
import medio
import nibabel as nib
import numpy as np
import skimage
import scipy
from .utils import larger, smaller

description = """Universal defacing for MRI brain images of virtually any
type. If you use PyFaceWipe in your analysis, please cite:

PyFaceWipe: A New Defacing Tool For Almost Any MRI Contrast.
Mitew, S., Yeow, L.Y., Ho, C.L., Bhanu, P.K.N., Nickalls, O.J. 
Magn Reson Mater Phy (2024).
https://doi.org/10.1007/s10334-024-01170-x
"""


class PyFaceWipe:
    def __init__(
        self,
        use_gpu: bool = False,
        disable_itk_warnings: bool = True,
        verbose: bool = False,
    ):
        print("==========\nPyFaceWipe\n==========")
        print(description)
        # See synthstrip_class.py for all available arguments
        self.strip = SynthStrip(
            debug=False, use_gpu=use_gpu, allow_torch_warnings=False, verbose=False
        )
        self.station_name = os.environ["COMPUTERNAME"]
        self.verbose = verbose

        if disable_itk_warnings:
            medio.backends.itk_io.itk.ProcessObject.SetGlobalWarningDisplay(False)

    def deface(
        self,
        source: Path,
        output_dir: Path,
        remove_ears: bool = True,
        save_steps: bool = False,
    ):
        """
        deface a single DICOM or NIFTI image volume.
            src_in:         (path-like object) Source directory or file
                            (required)
            output_dir:     (path-like object) Directory to save
                            defaced volumes (required)
                            Existing files may be overwritten without warning
            remove_ears:    If True, performs ear removal.
            save_steps:     (bool) If True, saves the intermediary volumes
                            in addition.
        """

        self.src_in = Path(source)  # Accepts both Path objects and strings
        print(f"Loading {self.src_in}")

        if not self.src_in.exists():
            raise FileNotFoundError(f'File does not exist: "{self.src_in}"')

        output_dir = Path(output_dir)
        # Append src name to make a subdir
        output_dir = output_dir.joinpath(self.src_in.name)

        if output_dir.exists():
            print(
                f'[WARNING] Output directory exists: "{output_dir}"\n'
                f"\tFiles may be overwritten without further warning."
            )

        self.output_dir = output_dir
        self.step_out_dir = output_dir.parent.joinpath(output_dir.name + "_steps")
        if self.verbose:
            print(f"output_dir: {self.output_dir}")
            print(f"step out dir: {self.step_out_dir}")

        # ####################################################################

        self.save_steps = save_steps
        if self.save_steps:
            print("\tIntermediate step volumes will be saved.")

        self.remove_ears = remove_ears
        if not self.remove_ears:
            print("\tNOT performing ear removal.")

        # 1 - LOAD -----------------------------------------------------------------
        try:
            arr, metadata = medio.read_img(
                self.src_in,
                desired_ornt="RAS",
                backend=None,
                dtype=None,
                header=True,
                channels_axis=-1,  # multichannel (ie RGB) not supported
                coord_sys="nib",
            )
            src_datatype = arr.dtype
            if len(arr.shape) == 4:
                arr = arr[:, :, :, 0]
            elif len(arr.shape) > 4:
                raise ValueError(f"Array has too many dimensions: shape {arr.shape}")
            elif len(arr.shape) < 3:
                raise ValueError(f"Array has too few dimensions: shape {arr.shape}")

        except FileNotFoundError as err:
            # Probably tried loading a nii with a dir input not a file
            print(f'Failed loading "{self.src_in}" - FileNotFoundError')
            raise err

        except ValueError as err:
            print(f'Failed loading "{self.src_in}" - ValueError')
            print(f"\tArray probably has an unexpected shape: shape {arr.shape}")
            raise err

        except Exception as err:
            print(f"Unexpected Error loading {self.src_in}\n{err}")
            print("*" * 60)
            raise err

        self.arr = arr

        if self.verbose:
            print(
                f"Loaded   : {self.src_in}\n"
                f"\tarr shape: {arr.shape}\n"
                f"\tvoxel spacing: {metadata.spacing}"
            )

        # 2 - SkullStrip with SynthStrip -------------------------------------------
        brain_mask = self.medio2mask_vol(arr, metadata)  # , metadata, strip=self.strip)

        if self.save_steps:
            self.save_out_step_nii(brain_mask, metadata.affine, txt="2 brainmask")
            self.save_out_step_nii(
                brain_mask * arr, metadata.affine, txt="2 brainmask_applied"
            )

        # 3 - Geometric Operations -------------------------------------------------
        deface_mask = self.make_deface_volume(brain_mask.copy(), metadata)

        if self.save_steps:
            self.save_out_step_nii(deface_mask, metadata.affine, txt="6- defacemask")
            self.save_out_step_nii(
                deface_mask * arr, metadata.affine, txt="6- defacemask_applied"
            )

        # 4 - Apply Defacing Mask --------------------------------------------------
        masked_arr = self.apply_mask(
            scan_vol=arr, mask=deface_mask, set_to="min_in_vol"
        )

        # 5 - Save out file --------------------------------------------------------
        #         Select output based on source
        out_fp = self.output_dir  # .joinpath(self.src_in.name)
        if self.verbose:
            print("\tSaving... ", end="")
        if self.src_in.is_dir():
            # ##########  Is a Directory of DICOM images
            medio.save_dir(
                out_fp,
                masked_arr.astype(np.float32),
                metadata,
                use_original_ornt=True,
                dtype=src_datatype,
                channels_axis=None,  # Is any MRI/CT multichannel? ie RGB
                parents=True,
                exist_ok=True,
                allow_dcm_reorient=False,  # needs checking
            )
        elif self.src_in.is_file():
            if self.src_in.suffix in (".gz", ".nii"):
                # ########### Is a NIFTI file  (nibabel backend)
                medio.save_img(
                    out_fp,
                    masked_arr,
                    metadata,
                    use_original_ornt=True,
                    backend="nib",
                    dtype=src_datatype,
                    channels_axis=None,
                    mkdir=True,
                    parents=True,
                )
            else:
                # ########### Is a DICOM file  (ITK backend)
                medio.save_img(
                    out_fp,
                    masked_arr,
                    metadata,
                    use_original_ornt=True,
                    allow_dcm_reorient=True,  # DICOM is Right-hand only
                    backend=None,
                    dtype=src_datatype,
                    channels_axis=None,
                    mkdir=True,
                    parents=True,
                )

        print(f'\tSaved to {out_fp}\n{"-"*45}')

        return {
            "outfile": out_fp,
            "src_arr": arr,
            "deface_mask": deface_mask,
            "masked_arr": masked_arr,
        }

    # ############################################################################
    # ###                    data loader helper                                ###
    # ############################################################################

    def medio2mask_vol(self, arr, metadata):  # , strip=None):
        # Takes direct return from medio as input
        # Vol is already rearranged into RAS by medio

        anat_nii = nib.Nifti1Image(arr, metadata.affine)

        if self.strip is None:
            print(
                "[WARNING] Synthstrip not properly initialised. This may be slower than expected."
            )
            self.strip = SynthStrip(debug=False)

        mask_nib = self.strip.run_from_nib(anat_nii, get_item="nibabel")

        return mask_nib.get_fdata()

    # ############################################################################
    # ###                    make_deface_volume                                ###
    # ############################################################################

    def make_deface_volume(self, brainMask, metadata):
        # Note the input volume is always RAS+ orientation (thanks to medio)
        # Axis 0 R+
        # Axis 1 A+
        # Axis 2 S+

        orig_shape = brainMask.shape
        proportion = 0.6  # Arbitrary for the de-chin
        margin_mm = 12  # pixel clearance, not really mm
        vox_size_ap = metadata.spacing[1]  # see axis comments above
        vox_size_si = metadata.spacing[2]  # see axis comments above

        # Get the lower and upper sagittal axis extremes of the brain mask
        raw_lower_sag_slice, raw_upper_sag_slice = self.lateral_limits(brainMask)

        # 1- x4 slice reduction in size - will expand later.
        print("\t[1", end="")
        reduce_factor = 2
        brainMaskSmall = brainMask[::reduce_factor, ::reduce_factor, ::reduce_factor]
        print("]", end="")

        # 2- binary dilation on the reduced volume (for speed)
        print("[2", end="")
        ball_size = 1  # Needs to be an odd number
        kernal_ball = skimage.morphology.ball(ball_size)
        kernal_ax = kernal_ball.copy()
        kernal_ax[:, :, 0] = 0  # Depends on ball size == 1
        kernal_ax[:, :, 2] = 0
        sz = 1 + (2 * ball_size)
        kernal_si = np.zeros((sz, sz, sz))
        kernal_si[1, 1, :] = 1

        # Remember volume size has been reduced by 4
        # Need to remember different resolution in LR, AP and SI axes.
        steps_AP = int(margin_mm / (vox_size_ap * ball_size * reduce_factor))
        steps_SI = int(margin_mm / (vox_size_si * ball_size * reduce_factor))
        steps_both = smaller(steps_AP, steps_SI)  # abs(steps_AP - steps_SI)
        steps_ap_only = abs(steps_AP - steps_both)
        steps_si_only = abs(steps_SI - steps_both)

        # BOTH axes (AP & SI) first
        for step in range(steps_both):
            brainMaskSmall = skimage.morphology.binary_dilation(
                brainMaskSmall, kernal_ball
            )

        # AP only (really axial plane)
        for step in range(steps_ap_only):
            brainMaskSmall = skimage.morphology.binary_dilation(
                brainMaskSmall, kernal_ax
            )

        # SI only - needed for coronal thick slice studies
        for step in range(steps_si_only):
            brainMaskSmall = skimage.morphology.binary_dilation(
                brainMaskSmall, kernal_si
            )
        print("]", end="")

        # 3- resize back to full size
        print("[3", end="")
        brainMask = scipy.ndimage.zoom(brainMaskSmall, reduce_factor).astype("bool")
        print("]", end="")

        # ######## Correct off-by-1 error after volume re-expansion ########################
        # Apply mask to the MRI volume
        # check mask shape is same as volume, & fix before masking to finalvol

        if brainMask.shape != orig_shape:
            # Only needs extra steps if brainMask is smaller than volume in any axis
            # Presumably related to the re-expansion after reducing size by 4
            # If bigger then can just slice off extra
            mask_i, mask_j, mask_k = brainMask.shape
            vol_i, vol_j, vol_k = orig_shape
            delta_i = mask_i - vol_i
            delta_j = mask_j - vol_j
            delta_k = mask_k - vol_k

            # Mask is bigger than vol in at least one axis.
            # solve by creating bigger zerod array, inserting mask
            # and slice out volume shaped array
            intermediate = np.zeros(
                (
                    larger(mask_i, delta_i),
                    larger(mask_j, delta_j),
                    larger(mask_k, delta_k),
                ),
                dtype=bool,
            )
            intermediate[:mask_i, :mask_j, :mask_k] = brainMask

            brainMask = intermediate[:vol_i, :vol_j, :vol_k].astype("int16")

        # ##################################################################################
        if self.save_steps:
            self.save_out_step_nii(
                brainMask, metadata.affine, txt="3-postdilate_mask.nii.gz"
            )
            self.save_out_step_nii(
                brainMask * self.arr,
                metadata.affine,
                txt="3-postdilate_mask_applied.nii.gz",
            )
        # ##################################################################################

        # 4- convex hull in sag plane again to fill in gaps
        print("[4", end="")
        brainMask = self.convexHull(brainMask)
        print("]", end="")

        # ##################################################################################
        if self.save_steps:
            self.save_out_step_nii(
                brainMask, metadata.affine, txt="4-postconvexhull_mask.nii.gz"
            )
            self.save_out_step_nii(
                brainMask * self.arr,
                metadata.affine,
                txt="4-postconvexhull_mask_applied.nii.gz",
            )
        # ##################################################################################

        # 5- Posterior Fill and lateral crop (ear removal)
        print("[5", end="")
        proportion = 0.6
        margin_mm = 12
        # Flood Fill mask POSTERIORLY to make sure cervical cord is preserved
        # IOP = dcm.ImageOrientationPatient
        brainMask = self.maskPosterior(
            brainMask, proportion, raw_lower_sag_slice, raw_upper_sag_slice
        )

        # ##################################################################################
        if self.save_steps:
            txt = "5-maskposterior"
            if self.remove_ears:
                txt += "_ears_removed"
            else:
                txt += "_ears_kept"

            self.save_out_step_nii(brainMask, metadata.affine, txt=txt + ".nii.gz")
            self.save_out_step_nii(
                brainMask * self.arr, metadata.affine, txt=txt + "_applied.nii.gz"
            )
        # ##################################################################################

        print("]")

        return brainMask

    # ########################################################################

    def save_out_step_nii(self, volume, affine, txt=""):
        # in_nii = nib.load(src_nii)
        # out_path = self.output_dir.joinpath(self.src_in.name +" "+'steps')
        self.step_out_dir.mkdir(exist_ok=True, parents=True)

        if volume.dtype == bool:
            out_img = nib.Nifti1Image(volume.astype("uint8"), affine)
        else:
            out_img = nib.Nifti1Image(volume, affine)

        out_fp = self.step_out_dir.joinpath(self.src_in.name + " " + txt + ".nii.gz")
        nib.save(out_img, out_fp)

        if self.verbose:
            print(f"step {txt} saved to {out_fp}")

    # ########################################################################

    def lateral_limits(self, mask_vol):
        """
        Define lateral limits of the binary brain mask
        Helps define where a lateral 'cut' can be made
        """
        sagSliceAxis = 0
        # corSliceAxis = 1
        # axSliceAxis = 2
        noSlices = mask_vol.shape[sagSliceAxis]

        for sagSliceNo in range(noSlices - 1):
            if mask_vol[sagSliceNo, :, :].any():
                lower_limit = sagSliceNo
                break
            else:
                lower_limit = 0

        for sagSliceNo in range(noSlices - 1, 0, -1):
            if mask_vol[sagSliceNo, :, :].any():
                upper_limit = sagSliceNo
                break
            else:
                upper_limit = noSlices - 1

        return lower_limit, upper_limit

    # ########################################################################

    def convexHull(self, volume):
        # Note the input volume is always RAS+ orientation (thanks medio)
        # Axis 0 R+
        # Axis 1 A+
        # Axis 2 S+
        sagSliceAxis = 0
        # corSliceAxis = 1
        axSliceAxis = 2
        noSlices = volume.shape[sagSliceAxis]

        for sagSliceNo in range(noSlices):
            sagSliceData = volume[sagSliceNo, :, :]
            if sagSliceData.any():
                volume[sagSliceNo, :, :] = skimage.morphology.convex_hull_image(
                    sagSliceData == True
                )

        noSlices = volume.shape[axSliceAxis]

        for axSliceNo in range(noSlices):
            axSliceData = volume[:, :, axSliceNo]
            if axSliceData.any():
                volume[:, :, axSliceNo] = skimage.morphology.convex_hull_image(
                    axSliceData == True
                )

        return volume

    # ########################################################################

    def maskPosterior(
        self,
        brainMask: np.ndarray,
        blankRatio: float,
        raw_lower_sag_slice,
        raw_upper_sag_slice,
    ) -> np.ndarray:
        """
        Apply POSTERIOR slab blanking to the final brainmask
        i.e. make the posterior portion = True
        Also Lateral Crop - only include the lower to upper sag slices
        brainMask = processed mask volume from DeepBrain
        blankRatio = how big the volume slab should be as proportion of
                the AP size of the volume
        Note the input volume is always RAS+ orientation (thanks medio)
        Axis 0 R+
        Axis 1 A+
        Axis 2 S+
        """

        xdim, ydim, zdim = np.shape(brainMask)
        proportion = int(blankRatio * ydim)

        if self.remove_ears:
            brainMask[raw_lower_sag_slice:raw_upper_sag_slice, :proportion, :] = True

        else:
            brainMask[:, :proportion, :] = True

        # Return the modified brainMask np.ndarray
        return brainMask

    # ########################################################################

    def apply_mask(self, scan_vol, mask, set_to=None):
        """
        Apply mask to scan volume.
        Default is set to zero.
        Alternatively (e.g. for CT) set to lowest value in volume
        or lowest value possible for array dtype, or min val in the scan volume
        min_value = np.iinfo(im.dtype).min
        max_value = np.iinfo(im.dtype).max
        """
        if set_to is None or set_to == 0:
            return scan_vol * mask

        if set_to == "min_dtype":
            min_value = np.iinfo(scan_vol.dtype).min
            return (min_value * np.logical_not(mask)) + (scan_vol * mask)

        if set_to == "min_in_vol":
            min_value = scan_vol.min()
            return (min_value * np.logical_not(mask)) + (scan_vol * mask)

        raise ValueError(f'[apply_mask] Unexpected "set_to" value: {set_to}')
