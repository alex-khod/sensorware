import os
import unittest

import numpy as np
from sensor import utils, imaging, mocks


class TestUtils(unittest.TestCase):

    def test_cyclic_images(self):
        path = os.path.join('.', 'data')
        image_fns = list(utils.list_images(path))
        cyclic_fns = list(mocks.cyclic_list_images(path, limit=len(image_fns) * 2))
        assert (len(image_fns) < len(cyclic_fns))


class TestImageConvert(unittest.TestCase):

    @unittest.skip
    def test_skip(self):
        print("This test won't run even if explicitly called as TestImage.test_skip")

    def a_method(self):
        print("This won't be run by unittest, but can be explicitly run," +
              "since the method name doesn't start from test*")

    def test_numpy_image_mean(self):
        # images = 3 4x2 arrays
        images = np.arange(24, dtype='float').reshape((3, 2, 4))
        im_equal = images[1] == imaging.mean_pixels(images)
        assert im_equal.all()

        im_equal = images[1] == images.mean(axis=0)
        assert im_equal.all()

    def test_uint8_subtract_uint8_is_proper(self):
        image = np.arange(8, dtype='uint8').reshape((2, 4))
        diff = imaging.subtract_image_uint8(image, 2 * image)
        # resulting value is subtracted properly
        assert (diff == 0).all()

        diff = imaging.subtract_image_uint8(2 * image, image)
        assert (diff == image).all()

    def test_uint8_subtract_loops(self):
        image = np.arange(8, dtype='uint8').reshape((2, 4))
        diff = imaging.subtract_image(image, 2 * image)
        # resulting value will overflow and become positive
        assert (diff >= 0).all()

    def test_int8_subtract_is_proper(self):
        image = np.arange(8, dtype='int8').reshape((2, 4))
        diff = imaging.subtract_image(image, 2 * image)
        # resulting value is subtracted properly
        assert (diff <= 0).all()

    def test_uint8_to_int8(self):
        image = np.asarray([[127, 128, 255, 256]], dtype='uint8')
        image2 = np.asarray([[127, -128, -1, 0]], dtype='int8')
        image_conv = image.astype('int8')
        assert (image_conv == image2).all()
