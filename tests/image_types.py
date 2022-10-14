import os
import unittest

import numpy as np
from skimage import color, io
from skimage import util as sk_utils


def get_test_file(*args):
    return os.path.join("tests", "data", *args)


# prepared 1-byte color black-white image
T_GRAYSCALE_2D = "test_bw_2d.jpg"
# prepared 3-byte color black-white image
T_GRAYSCALE_3D = "test_bw_3d.jpg"
# prepared multi-channel image
T_RGB = "test_rgb.jpg"

T_CREATE_2D = "test_create_bw.jpg"
T_CREATE_3D = "test_create_rgb.jpg"

# image generated in color test
T_NEGATIVE = "test_negative.jpg"
T_IMAGE_DIMENSIONS = (10, 10)


class TestImageCreate(unittest.TestCase):
    def test_1byte_color(self):
        img = np.asarray([[255, 255, 255, 255]])
        io.imsave(get_test_file(T_CREATE_2D), img)
        img2 = io.imread(get_test_file(T_CREATE_2D))
        assert img2.ndim == 2

    def test_3byte_color(self):
        img = np.asarray([[[255, 255, 255], [255, 255, 255]]])
        io.imsave(get_test_file(T_CREATE_3D), img)
        img2 = io.imread(get_test_file(T_CREATE_3D))
        assert img2.ndim == 3


class TestImageColor(unittest.TestCase):

    # saving float-point dtype images to disk should be handled with care

    # color of saved and loaded image loops around 257 if less than -1
    # white (-1) > gray (-128) > black (-256) > white (-257)
    # both for jpg and bmp.
    # this depends on float image range (0, 1), (-1, 1), (-N, N)

    def test_saved_image_colors(self):
        img = np.asarray([[-1., 1., -128., -256., -257.]])
        io.imsave(get_test_file(T_NEGATIVE), img)
        img2 = io.imread(get_test_file(T_NEGATIVE))
        comp = img2 == [[252, 253, 130, 0, 1]]
        assert comp.all()

    def test_image_minus_one_is_white(self):
        img = np.zeros(T_IMAGE_DIMENSIONS, dtype=np.float32) - 1.
        io.imsave(get_test_file(T_NEGATIVE), img)
        img2 = io.imread(get_test_file(T_NEGATIVE), as_gray=True)
        is_white = (img2 == 255).all()
        assert is_white

    def test_image_minus_128_is_gray(self):
        img = np.zeros(T_IMAGE_DIMENSIONS, dtype=np.float32) - 128.
        io.imsave(get_test_file(T_NEGATIVE), img)
        img2 = io.imread(get_test_file(T_NEGATIVE), as_gray=True)
        is_gray = (img2 == 128).all()
        assert is_gray

    def test_image_plus_1_is_white(self):
        img = np.zeros(T_IMAGE_DIMENSIONS, dtype=np.float32) + 1.
        io.imsave(get_test_file(T_NEGATIVE), img)
        img2 = io.imread(get_test_file(T_NEGATIVE), as_gray=True)
        is_white = (img2 == 255).all()
        assert is_white

    def test_image_minus_256_is_black(self):
        img = np.zeros(T_IMAGE_DIMENSIONS, dtype=np.float32) - 256.
        io.imsave(get_test_file(T_NEGATIVE), img)
        img2 = io.imread(get_test_file(T_NEGATIVE), as_gray=True)
        is_black = (img2 == 0).all()
        assert is_black

    def test_image_minus_257_is_white(self):
        img = np.zeros(T_IMAGE_DIMENSIONS, dtype=np.float32) - 257.
        io.imsave(get_test_file(T_NEGATIVE), img)
        img2 = io.imread(get_test_file(T_NEGATIVE), as_gray=True)
        is_white = (img2 == 255).all()
        assert is_white


class TestImageTypes(unittest.TestCase):

    def test_sk_grayscale_is_2d_uint8(self):
        # img > rgb2gray >
        img = io.imread(get_test_file(T_GRAYSCALE_2D))
        assert img.ndim == 2
        assert img.dtype == np.dtype(np.uint8)

    def test_grayscale_is_3d_uint8(self):
        img = io.imread(get_test_file(T_GRAYSCALE_3D))
        assert img.ndim == 3
        assert img.dtype == np.dtype(np.uint8)

    def test_rgb_is_3d_uint8(self):
        img = io.imread(get_test_file(T_RGB))
        assert img.ndim == 3
        assert img.dtype == np.dtype(np.uint8)

    def test_imread_as_gray(self):
        def _test(image_fn):
            img = io.imread(get_test_file(image_fn))
            img = color.rgb2gray(img)
            img2 = io.imread(get_test_file(image_fn), as_gray=True)
            assert (img == img2).all()

        img_files = [T_GRAYSCALE_2D, T_GRAYSCALE_3D, T_RGB]
        for i in img_files:
            _test(i)

    def test_sk_grayscale_rgb2gray_is_2d_uint8(self):
        # this is equivalent to io.imread(..., as_gray=True)
        # because rgb2gray conversion is applied under the hood
        img = io.imread(get_test_file(T_GRAYSCALE_2D))
        img = color.rgb2gray(img)
        assert img.ndim == 2
        assert img.dtype == np.dtype(np.uint8)

    def test_grayscale_rgb2gray_is_2d_uint8(self):
        img = io.imread(get_test_file(T_GRAYSCALE_3D))
        img = color.rgb2gray(img)
        assert img.ndim == 2
        assert img.dtype == np.dtype(np.float64)

    def test_rgb_rgb2gray_is_2d_uint8(self):
        img = io.imread(get_test_file(T_RGB))
        img = color.rgb2gray(img)
        assert img.ndim == 2
        assert img.dtype == np.dtype(np.float64)

    def test_image_force_float64(self):
        img_files = [T_GRAYSCALE_2D, T_GRAYSCALE_3D, T_RGB]
        for i in img_files:
            img = io.imread(get_test_file(i))
            img = color.rgb2gray(img)
            img = sk_utils.img_as_float64(img)
            assert img.ndim == 2
            assert img.dtype == np.dtype(np.float64)
