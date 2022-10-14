import os

import numpy as np
from PIL import Image as PILImage
from scipy import ndimage
from skimage import color, draw, feature, filters, io
from skimage.color import rgb2gray
from skimage.measure import regionprops


def load_image(filepath, mode="RGB", dtype="uint8"):
    image = PILImage.open(filepath).convert(mode)
    image = np.array(image, dtype)
    return image


def save_image(image, filepath):
    image = PILImage.fromarray(image)
    image.save(filepath)


def load_grayscale_image(filepath):
    return load_image(filepath, "L")


def load_rgb_image(filepath):
    return load_image(filepath, "RGB")


def draw_keys_to_image(image, keys):
    im_keys = np.copy(image)
    im_keys = color.gray2rgb(im_keys)

    keys = keys.astype(np.int)
    for key in keys:
        y, x, r = key
        rr, cc = draw.circle_perimeter(y, x, r, shape=im_keys.shape)
        im_keys[rr, cc] = [255, 0, 0]
    return im_keys


def mean_pixels(images):
    img_shape = images[0].shape

    for im in images:
        if im.shape != img_shape:
            raise ValueError('Images must have the same shape.')

    return np.mean(images, axis=0)


def subtract_image(image, minus_image):
    if image.shape != minus_image.shape:
        raise ValueError('Images must have the same shape.')

    return image - minus_image


def subtract_with_rescale(image, minus_image):
    if image.shape != minus_image.shape:
        raise ValueError('Images must have the same shape.')

    mask = minus_image > image
    diff = image - minus_image
    diff[mask] = 0
    return diff


def subtract_image_uint8(image, minus_image):
    if image.shape != minus_image.shape:
        raise ValueError('Images must have the same shape.')

    mask = minus_image > image
    diff = image - minus_image
    diff[mask] = 0
    return diff


def rescale(image, a, b):
    a0, b0 = image.min(), image.max()
    if b0 == a0:
        return image
    k = (b - a) / (b0 - a0)
    image = (image - a0) * k + a
    image = image.astype('uint8')
    return image


def blob_search(img, **kwargs):
    inverted = np.copy(img)
    # inverted = 255 - inverted

    keys = feature.blob_log(inverted, **kwargs)
    return keys, [img, inverted]


def binary_threshold(image_fn, prefix, out_dir):
    path = out_dir
    os.makedirs(path, exist_ok=True)

    image = io.imread(image_fn)

    orig_fn = os.path.basename(image_fn)
    io.imsave(os.path.join(path, prefix + '_1org_' + orig_fn), image)

    image = rgb2gray(image)

    binary = image > image.mean()
    black_white = binary.astype(int) * 255
    io.imsave(os.path.join(path, prefix + '_2bin_' + orig_fn), black_white)


def frangi(image_fn, prefix, out_dir, kwargs):
    import json
    if type('') == type(kwargs):
        kwargs = json.loads(kwargs)

    path = out_dir
    os.makedirs(path, exist_ok=True)

    image = io.imread(image_fn)
    orig_fn = os.path.basename(image_fn)
    io.imsave(os.path.join(path, prefix + '_1org_' + orig_fn), image)

    image = rgb2gray(image)

    # image = 255 - image # invert
    io.imsave(os.path.join(path, prefix + '_2rev_' + orig_fn), image)

    filtered_image = filters.frangi(image, black_ridges=False, **kwargs)
    filtered_image = filtered_image / filtered_image.max()

    io.imsave(os.path.join(path, prefix + '_3fil_' + orig_fn),
              filtered_image, check_contrast=False)

    cropx, cropy = 50, 50
    filtered_image = filtered_image[cropy:-cropy, cropx:-cropx]

    io.imsave(os.path.join(path, prefix + '_4cut_' + orig_fn),
              filtered_image, check_contrast=False, )

    threshhold = filtered_image.mean() + filtered_image.std()
    # threshhold = filtered_image.mean()

    binary = filtered_image > threshhold
    black_white = binary.astype(int) * 255

    io.imsave(os.path.join(path, prefix + '_5bin_' + orig_fn), black_white, check_contrast=False)

    filled = ndimage.binary_fill_holes(binary)
    black_white = filled.astype(int) * 255

    io.imsave(os.path.join(path, prefix + '_6hol_' + orig_fn), black_white, check_contrast=False)

    labeled_image, nlabels = ndimage.label(filled)
    props = regionprops(labeled_image)
    areas = list(map(lambda x: x.area, props))

    return areas
