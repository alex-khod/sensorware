import collections
import sys

import cv2
import numpy as np
from skimage import transform

from sensor import imaging
from sensor.detector import utils as det_utils

default_kwargs = {
    "thresholdStep": 10,
    "minThreshold": 50,
    "maxThreshold": 220,
    "minRepeatability": 2,
    "minDistBetweenBlobs": 10,

    "filterByColor": True,
    "blobColor": 0,

    "filterByArea": True,
    "minArea": 25,
    "maxArea": 5000,

    "filterByCircularity": False,
    "minCircularity": 0.8,
    "maxCircularity": sys.float_info.max,

    "filterByInertia": True,
    "minInertiaRatio": 0.1,
    "maxInertiaRatio": sys.float_info.max,

    "filterByConvexity": True,
    "minConvexity": 0.95,
    "maxConvexity": sys.float_info.max,
}

scan_add_kwargs = {
    # 'step': 25,
    'thresholdStep': 25,

    'minThreshold': 0,
    'maxThreshold': 250,
    'minRepeatability': 4,
    'minDistBetweenBlobs': 15,

    'minConvexity': 0.8,
    'minInertiaRatio': 0.3,
    'filterByCircularity': True
}

scan_kwargs = default_kwargs.copy()
scan_kwargs.update(scan_add_kwargs)
UM_PER_SCREEN = 519


class SBDWrapper:

    def __init__(self):
        MASK_IMAGE_COUNT = 3
        self.scale_factor = 1
        # mask for static background filtering
        self.masks = collections.deque(maxlen=MASK_IMAGE_COUNT)
        self.pixel_to_um = 0  # 'auto'

    def setup_detector(self, **kwargs):
        params = cv2.SimpleBlobDetector_Params()
        for k, v in kwargs.items():
            if hasattr(params, k):
                setattr(params, k, v)
        return params

    def detect(self, image, **kwargs):
        if kwargs['maxThreshold'] < kwargs['minThreshold']:
            return None

        image, image_fn = image
        params = self.setup_detector(**kwargs)
        detector = cv2.SimpleBlobDetector_create(params)
        # search for black blobs on white background
        cv2keys = detector.detect(image)

        # x, y, radius
        keys = [(k.pt[1], k.pt[0], k.size / 2) for k in cv2keys]
        keys = np.array(keys)

        return keys, image_fn, kwargs

    def update_masks(self, image):
        self.masks.append(image)

    def process_kwargs(self, kwargs):
        min_area_px = 16
        max_area_px = det_utils.diamToAreaPx(100, self.pixel_to_um / self.scale_factor)

        final_kwargs = scan_kwargs.copy()
        final_kwargs.update({
            'minArea': min_area_px,
            'maxArea': max_area_px,
        })
        if kwargs is not None:
            final_kwargs.update(kwargs)
        return final_kwargs

    def process_dynamic_mask(self, imagedef):
        image, image_fn = imagedef
        masks = self.masks
        keys, steps = None, None
        if len(masks) == masks.maxlen:
            mask = imaging.mean_pixels(masks)
            mask = mask.astype('uint8')
            keys, steps = self.process(imagedef, mask)
        self.update_masks(image)
        return keys, steps

    def mask_from_integer(self, shape, value):
        assert value < 256
        mask = np.ones(shape, dtype="uint8") * (255 - value)
        return mask

    def mask_or_mean(self, mask, image):
        if mask is None:
            mask = np.ones(image.shape) * image.mean()
        elif type(mask) is int:
            mask = self.mask_from_integer(image.shape, mask)

        return mask

    def process(self, imagedef, mask, kwargs=None):
        image, image_fn = imagedef
        self.pixel_to_um = image.shape[1] / UM_PER_SCREEN
        im_original = image.copy()

        mask = self.mask_or_mean(mask, image)

        image = 255 - imaging.subtract_image_uint8(255 - image, 255 - mask)
        image = imaging.rescale(image, 0, 255)

        im_unmasked = image.copy()

        # io.imsave(get_out_path('5_unmasked', image_fn), 255 - image)
        # io.imsave(get_out_path('6_unmasked_True', image_fn), image)

        scale_factor = self.scale_factor
        final_kwargs = self.process_kwargs(kwargs)
        scaled_image = transform.downscale_local_mean(image, (scale_factor, scale_factor)).astype('uint8')
        keys, _, _ = self.detect((scaled_image, image_fn), **final_kwargs)
        keys = keys * scale_factor

        im_keys = imaging.draw_keys_to_image(image, keys).astype('uint8')

        if keys is not None and len(keys) > 0:
            keys[:, 2] = keys[:, 2] * 2 / self.pixel_to_um

        steps = [
            ("original", im_original),
            ("unmasked", im_unmasked),
            ("keys", im_keys),
        ]

        return keys, steps
