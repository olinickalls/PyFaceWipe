import os
import torch
import warnings  # used only to suppress warnings in torch
import torch.nn as nn
import numpy as np
from . import surfa as sf
# import surfa as sf
import scipy.ndimage
import nibabel as nib
from pathlib import Path

description = '''
Robust, universal skull-stripping for brain images of any
type. If you use SynthStrip in your analysis, please cite:

SynthStrip: Skull-Stripping for Any Brain Image.
A Hoopes, JS Mora, AV Dalca, B Fischl, M Hoffmann.
NeuroImage 206 (2022), 119474.
https://doi.org/10.1016/j.neuroimage.2022.119474 
'''


class SynthStrip():
    def __init__(self,
                 use_gpu=False,
                 no_csf=False,
                 specific_model=None,
                 border=1,
                 verbose=False,
                 debug=False,
                 allow_torch_warnings=True
                 ):
        """
        Process a raw volume with no reforming
        Initialisation, then .run() to process.
        """
        self.debug = debug
        self.border = border
        self.verbose = verbose

        if self.debug:
            print(f'You are using::: {__file__}')
            import neurite as ne

        # necessary for speed gains (I think)
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = True

        # configure GPU device
        if use_gpu:  # NB Needs a CUDA compiled torch
            os.environ['CUDA_VISIBLE_DEVICES'] = '0'
            self.device = torch.device('cuda')
            self.device_name = 'GPU'
        else:
            os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
            self.device = torch.device('cpu')
            self.device_name = 'CPU'

        # configure model
        if self.verbose:
            print(f'Configuring model on the {self.device_name}')


        with torch.no_grad():
            self.model = StripModel()
            self.model.to(self.device)
            self.model.eval()

        if not allow_torch_warnings:
            # see https://discuss.pytorch.org/t/how-to-suppress-sourcechangewarning/46719/4
            warnings.filterwarnings("ignore")

        # load model weights
        if specific_model is not None:
            modelfile = specific_model
            print('Using custom model weights')
        else:
            version = '1'
            print(f'Running SynthStrip model version {version}')
            # fshome = os.environ.get('FREESURFER_HOME')
            # Modified to work independently of a Freesurfer installaltion
            fshome = str(Path(__file__).parent)
            if fshome is None:
                sf.system.warning('FREESURFER_HOME env variable must be set! Make sure FreeSurfer is properly sourced.')
                sf.system.warning('Defaulting to \'.\' current directory.')
                fshome = '.'

            if no_csf:
                print('Excluding CSF from brain boundary')
                modelfile = os.path.join(fshome, 'models', f'synthstrip.nocsf.{version}.pt')
            else:
                modelfile = os.path.join(fshome, 'models', f'synthstrip.{version}.pt')

        checkpoint = torch.load(modelfile, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        if verbose:
            print('If you use SynthStrip in your analysis, please cite:')
            print('----------------------------------------------------')
            print('SynthStrip: Skull-Stripping for Any Brain Image.')
            print('A Hoopes, JS Mora, AV Dalca, B Fischl, M Hoffmann.')
            print('NeuroImage 206 (2022), 119474.')


    def run_from_nib(self, in_nb_obj, get_item: str, filename=None):
        '''
        Process a Nibabel object with synthstrip.
        use:
          .run(<input_object>)
        where:
           <input_object> is a Nibabel object.

        Returns:
          Nibabel object with skullstrip performed - i.e. the mask 
          or
          numpy bool array mask
        '''
        if get_item.lower() not in ['mask', 'nibabel', 'save']:
            raise ValueError(f'Cannot return "{get_item}". Please use '
                             f'get_item="mask" or "nibabel".')
        # get the pixel data
        in_vol = in_nb_obj.get_fdata()

        # ###########################################################
        if self.debug:
            print(f'\tinput image data: {in_vol.shape} {in_vol.dtype}')
        # ###########################################################

        # ###########################################################
        if self.debug:
            print('Plotting received nibabel onject volume:')
            ne.plot.volume3D(in_nb_obj.get_fdata())
        # ###########################################################

        # load input volume
        image = sf.load_volume_from_nibabel(in_nb_obj)  # args.image is filename

        # ###########################################################
        if self.debug or self.verbose:
            print(f'\tinput image data: {image.shape} {image.dtype}')
            print(f'\t     instance of: {type(image)}')

        if self.debug:
            print(f'sf.load complete. Shape: {image.shape}  Type: {image.dtype}  Plotting loaded "image":')
            ne.plot.volume3D(image)
        # ###########################################################

        # frame check
        if image.nframes > 1:
            sf.system.fatal('Input image cannot have more than 1 frame')

        # conform image and fit to shape with factors of 64
        conformed = image.conform(voxsize=1.0, dtype='float32', method='nearest', orientation='LIA').crop_to_bbox()
        target_shape = np.clip(np.ceil(np.array(conformed.shape[:3]) / 64).astype(int) * 64, 192, 320)
        conformed = conformed.reshape(target_shape)

        # normalize intensities
        conformed -= conformed.min()
        conformed = (conformed / conformed.percentile(99)).clip(0, 1)
        in_vol -= in_vol.min()
        # percentile99 = np.percentile(in_vol, 99, method='nearest')
        # numpy 1.16.4 has 'interpolation', not 'method'
        percentile99 = np.percentile(in_vol, 99, interpolation='nearest')
        in_vol = (in_vol / percentile99).clip(0, 1)

        # ###########################################################
        if self.debug:
            print(f'Pre-inference conformed volume: Shape: {image.shape}  '
                f'Type: {image.dtype}  Plotting conformed "image":')
            ne.plot.volume3D(image)
        # ###########################################################

        # predict the surface distance transform
        with torch.no_grad():
            input_tensor = torch.from_numpy(conformed.data[np.newaxis, np.newaxis]).to(self.device)
            # input_tensor = torch.from_numpy(in_vol.astype(np.float64)).to(self.device)
            sdt = self.model(input_tensor).cpu().numpy().squeeze()

        # unconform the sdt and extract mask
        sdt = conformed.new(sdt).resample_like(image, fill=100)

        # find largest CC (just do this to be safe for now)
        components = scipy.ndimage.label(sdt.data < self.border)[0]
        bincount = np.bincount(components.flatten())[1:]
        # NB: components & mask are simple numpy arrays
        mask = (components == (np.argmax(bincount) + 1))
        mask = scipy.ndimage.binary_fill_holes(mask)

        # ###########################################################
        if self.verbose:
            print(f'Using border value: {self.border}')
        # ###########################################################

        # ###########################################################
        if self.debug:
            print(f'Post-inference SDT volume: Shape: {sdt.shape}  '
                f'Type: {sdt.dtype}  Plotting "sdt":')
            ne.plot.volume3D(sdt)

            print(f'Post-inference components volume: Shape: {components.shape}  '
                f'Type: {components.dtype}  Plotting "components":')
            ne.plot.volume3D(components)

            print(f'Post-inference mask volume: Shape: {mask.shape}  '
                f'Type: {mask.dtype}  Plotting "mask":')
            ne.plot.volume3D(mask)
        # ###########################################################


        # write the brain mask
        if get_item.lower()=='save':
            image.new(mask).save(filename)  # args.mask is the mask path
            print(f'Binary brain mask saved to: {filename}')

        if get_item.lower()=='mask':
            return mask

        elif get_item.lower()=='nibabel':
            # raise NotImplementedError('Returning as a nibabel object is not yet implemented.')
            # Manipulate the input nibabel in_nb_obj
            # Replace the pixel data with the mask array
            # Update the metadata - can we use surfa to do this?
            if self.debug:
                print('returning nibabel object')
            affine = in_nb_obj.affine
            out_nb = nib.Nifti1Image(mask.astype(int), affine)
            return out_nb



# -----------------------------------------------------------

class StripModel(nn.Module):

    def __init__(self,
                nb_features=16,
                nb_levels=7,
                feat_mult=2,
                max_features=64,
                nb_conv_per_level=2,
                max_pool=2,
                return_mask=False):

        super().__init__()

        # dimensionality
        ndims = 3

        # build feature list automatically
        if isinstance(nb_features, int):
            if nb_levels is None:
                raise ValueError('must provide unet nb_levels if nb_features is an integer')
            feats = np.round(nb_features * feat_mult ** np.arange(nb_levels)).astype(int)
            feats = np.clip(feats, 1, max_features)
            nb_features = [
                np.repeat(feats[:-1], nb_conv_per_level),
                np.repeat(np.flip(feats), nb_conv_per_level)
            ]
        elif nb_levels is not None:
            raise ValueError('cannot use nb_levels if nb_features is not an integer')

        # extract any surplus (full resolution) decoder convolutions
        enc_nf, dec_nf = nb_features
        nb_dec_convs = len(enc_nf)
        final_convs = dec_nf[nb_dec_convs:]
        dec_nf = dec_nf[:nb_dec_convs]
        self.nb_levels = int(nb_dec_convs / nb_conv_per_level) + 1

        if isinstance(max_pool, int):
            max_pool = [max_pool] * self.nb_levels

        # cache downsampling / upsampling operations
        MaxPooling = getattr(nn, 'MaxPool%dd' % ndims)
        self.pooling = [MaxPooling(s) for s in max_pool]
        self.upsampling = [nn.Upsample(scale_factor=s, mode='nearest') for s in max_pool]

        # configure encoder (down-sampling path)
        prev_nf = 1
        encoder_nfs = [prev_nf]
        self.encoder = nn.ModuleList()
        for level in range(self.nb_levels - 1):
            convs = nn.ModuleList()
            for conv in range(nb_conv_per_level):
                nf = enc_nf[level * nb_conv_per_level + conv]
                convs.append(ConvBlock(ndims, prev_nf, nf))
                prev_nf = nf
            self.encoder.append(convs)
            encoder_nfs.append(prev_nf)

        # configure decoder (up-sampling path)
        encoder_nfs = np.flip(encoder_nfs)
        self.decoder = nn.ModuleList()
        for level in range(self.nb_levels - 1):
            convs = nn.ModuleList()
            for conv in range(nb_conv_per_level):
                nf = dec_nf[level * nb_conv_per_level + conv]
                convs.append(ConvBlock(ndims, prev_nf, nf))
                prev_nf = nf
            self.decoder.append(convs)
            if level < (self.nb_levels - 1):
                prev_nf += encoder_nfs[level]

        # now we take care of any remaining convolutions
        self.remaining = nn.ModuleList()
        for num, nf in enumerate(final_convs):
            self.remaining.append(ConvBlock(ndims, prev_nf, nf))
            prev_nf = nf

        # final convolutions
        if return_mask:
            self.remaining.append(ConvBlock(ndims, prev_nf, 2, activation=None))
            self.remaining.append(nn.Softmax(dim=1))
        else:
            self.remaining.append(ConvBlock(ndims, prev_nf, 1, activation=None))

    def forward(self, x):

        # encoder forward pass
        x_history = [x]
        for level, convs in enumerate(self.encoder):
            for conv in convs:
                x = conv(x)
            x_history.append(x)
            x = self.pooling[level](x)

        # decoder forward pass with upsampling and concatenation
        for level, convs in enumerate(self.decoder):
            for conv in convs:
                x = conv(x)
            if level < (self.nb_levels - 1):
                x = self.upsampling[level](x)
                x = torch.cat([x, x_history.pop()], dim=1)

        # remaining convs at full resolution
        for conv in self.remaining:
            x = conv(x)

        return x

class ConvBlock(nn.Module):
    """
    Specific convolutional block followed by leakyrelu for unet.
    """

    def __init__(self, ndims, in_channels, out_channels, stride=1, activation='leaky'):
        super().__init__()

        Conv = getattr(nn, 'Conv%dd' % ndims)
        self.conv = Conv(in_channels, out_channels, 3, stride, 1)
        if activation == 'leaky':
            self.activation = nn.LeakyReLU(0.2)
        elif activation is None:
            self.activation = None
        else:
            raise ValueError(f'Unknown activation: {activation}')

    def forward(self, x):
        out = self.conv(x)
        if self.activation is not None:
            out = self.activation(out)
        return out

