import itertools
from unittest import mock

from sensor import utils, imaging
import numpy as np


class MockButton:
    is_pressed = True

    def __init__(self, *args, **kw):
        pass


def cyclic_list_images(dirname, limit=0):
    image_fns = list(utils.list_images(dirname))
    cyclic_gen = itertools.cycle(image_fns)
    i = 0
    for fn, fp in cyclic_gen:
        yield fn, fp
        if (limit > 0) and (i > limit):
            break
        i += 1


def mock_capture_images(path=utils.Pathing.sample_images_path):
    image_files = cyclic_list_images(path)

    def get_next_image(*args, **kwargs):
        image_fn = next(image_files)
        img = imaging.load_image(image_fn)
        return img

    return get_next_image


def mock_capture_null():
    def get_next_image(*args, **kwargs):
        return None

    return get_next_image


def mock_capture_rgb():
    def get_next_image(*args, **kwargs):
        shape = (320, 320, 3)
        rgb = np.random.randint(low=0, high=255, size=shape, dtype='uint8')
        return rgb

    return get_next_image


camera_mock = mock.MagicMock(
    brightness=10,
    contrast=10,
    saturation=10,
    sharpness=10,
    IMAGE_EFFECTS={
        'none': None,
        'off': None,
        '1': None,
    },
    FLASH_MODES={
        'off': None,
        'auto': None,
        '1': None,
    },
    METER_MODES={
        'off': None,
    },
    EXPOSURE_MODES={
        'off': None,
        'auto': None,
        '1': None,
        '2': None,
    },
    DRC_STRENGTHS={
        'off': None,
        '1': None,
    },
    AWB_MODES={
        'off': None,
        'auto': None,
        '1': None,
        '2': None,
    },
    still_stats=False,
)

camera_mock.capture = mock_capture_rgb()
