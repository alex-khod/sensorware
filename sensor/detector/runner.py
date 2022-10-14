import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from skimage import io
from sklearn.model_selection import ParameterGrid

from sensor import utils, imaging
from sensor.detector import utils as det_utils
from sensor.detector.sbd import SBDWrapper

# SMB_NAME = 'sample_3_170-180'
SMB_NAME = 'sample_1'


def load_images(sample_name=SMB_NAME):
    sample_dir = os.path.join(utils.Pathing.image_dir, sample_name)
    files = list(utils.list_images(sample_dir))
    # files = files[:10]
    return files


def generate_masks():
    image_fns = load_images()
    image_fns = image_fns[:10]
    images = [imaging.load_grayscale_image(im) for im in image_fns]
    for im_fn, im in zip(image_fns, images):
        io.imsave(det_utils.get_out_path('1_mask', im_fn, 'mask'), im)
    for i in range(1, len(images)):
        maskarr = images[:i]
        mask = imaging.mean_pixels(maskarr).astype('uint8')
        mask_path = det_utils.get_out_path('of_%s_images.jpg' % i, 'mask', 'mask')
        print(mask_path)
        io.imsave(mask_path, mask)


def generate_mask():
    image_fns = load_images()
    image_fns = image_fns[:4]
    images = [imaging.load_grayscale_image(im) for im in image_fns]
    for im_fn, im in zip(image_fns, images):
        io.imsave(det_utils.get_out_path('1_mask', im_fn, 'mask'), im)
    mask = imaging.mean_pixels(images).astype('uint8')
    mask_path = det_utils.get_out_path('1_mask', 'masks.jpg', 'mask')
    io.imsave(mask_path, mask)


def run_sbd_default():
    run_sbd(sample_name=SMB_NAME)


def run_sbd_all():
    def get_dirs(path):
        return [f.path for f in os.scandir(path) if f.is_dir()]

    samples = get_dirs(utils.Pathing.image_dir)

    for s in samples:
        sample_name = os.path.basename(s)
        run_sbd(sample_name)


def run_bruteforce():
    image_fn = os.path.join(
        '.', 'data', 'sample.jpg')
    img = imaging.load_grayscale_image(image_fn)
    mask = (np.zeros(img.shape) + 1) * 80
    mask = mask.astype('uint8')

    kwargs = {
        # 100, 250, 5, 5
        'minThreshold': np.linspace(255, 0, 12),
        'maxThreshold': np.linspace(255, 0, 12),
        'step': np.linspace(25, 0, 6),
        'minDistBetweenBlobs': 25,
    }
    pg = ParameterGrid(kwargs)

    sbd = SBDWrapper()

    max_len_keys = 0
    image_fn = os.path.join('.', 'data', utils.get_random_string(16), 'abc.jpg')
    for p in pg:
        keys = sbd.process((img, image_fn), mask, p)
        if len(keys) > 0:
            out_path = det_utils.get_out_path('8_params', image_fn, ext='.txt')
            with open(out_path, 'w') as f:
                f.write('%s' % p)
        if len(keys) > max_len_keys:
            print(p)
            print(len(keys))
            image_fn = os.path.join(
                '.', 'data', 'keys_%d' % max_len_keys, 'abc.jpg')
            max_len_keys = len(keys)


def run_bruteforce_custom():
    images_max = list(utils.list_images(os.path.join('.', 'data', 'max')))
    images_min = list(utils.list_images(os.path.join('.', 'data', 'min')))

    imagedefs_max = [(imaging.load_grayscale_image(ifn), ifn) for ifn in images_max]
    imagedefs_min = [(imaging.load_grayscale_image(ifn), ifn) for ifn in images_min]

    scale = 2

    kwargs = {
        # 100, 250, 5, 5
        'minThreshold': [0],
        'maxThreshold': [175, 200, 225, 250],
        'step': [25],
        'minDistBetweenBlobs': [15],
        'minArea': [det_utils.diamToAreaPx(d, 4.9 / scale) for d in [2, 4, 6]],
        'maxArea': [det_utils.diamToAreaPx(100, 4.9 / scale)],
        'scale': [scale * 2],
        'minInertiaRatio': [0.1, 0.3, 0.5, 0.9],
        'minConvexity': [0.5, 0.8, 0.9, 0.95],
        'minRepeatability': [3, 4, 5]
    }
    pg = ParameterGrid(kwargs)
    sbd = SBDWrapper()

    for p in pg:
        p['minArea'] = 16
        p['filterByCircularity'] = True
        try:

            brute_seed = utils.get_random_string(20)

            def get_brute_path(ifn):
                di = os.path.dirname(ifn)
                ba = os.path.basename(ifn)
                ifn = ba.replace('_3_gray8_6_unmasked_True', '')
                new_path = os.path.join(di, brute_seed, ifn)
                return new_path

            keys_max = [sbd.process((idf[0], get_brute_path(idf[1])), None, p)
                        for idf in imagedefs_max]
            keys_max = list(
                filter(lambda x: x is not None and x.any(), keys_max))
            if keys_max:
                keys_max = np.concatenate(keys_max)
            else:
                keys_max = []

            keys_min = [sbd.process((idf[0], get_brute_path(idf[1])), None, p)
                        for idf in imagedefs_min]
            keys_min = list(
                filter(lambda x: x is not None and x.any(), keys_min))

            if keys_min:
                keys_min = np.concatenate(keys_min)
            else:
                keys_min = []

            mn, mx = len(keys_min), len(keys_max)

            out_path = os.path.join('.', 'brute_multi.csv')
            with open(out_path, 'a') as f:
                f.write('%s%d%d%d%s\n' % (brute_seed, mx, mn, mx - mn, p))
        except Exception as exc:
            print(exc)
            breakpoint()


def run_single():
    image_fn = os.path.join('..', 'data', 'sample.jpg')
    img = imaging.load_grayscale_image(image_fn)
    sbd = SBDWrapper()
    # mask = load_as_gray8(os.path.join('.', 'data', 'sample_mask.jpg'))
    mask = None
    keys = sbd.process((img, image_fn), mask)
    print(keys)
    print(len(keys))


def run_sbd(sample_name):
    sbd = SBDWrapper()
    image_fns = load_images(sample_name)
    keyarr = []
    for image_fn in image_fns:
        img = imaging.load_grayscale_image(image_fn)
        imagedef = img, image_fn
        keys = sbd.process_dynamic_mask(imagedef)
        keyarr.append(keys)
    keyarr = list(filter(lambda x: x is not None and x.any(), keyarr))
    if keyarr:
        keyarr = np.concatenate(keyarr)
        res_df = pd.DataFrame(keyarr, columns=['x', 'y', 'r'])
        res_df.to_csv(os.path.join(utils.Pathing.out_root, sample_name) + '.csv')
        build_hist(sample_name)


def hist():
    build_hist('model')


def build_hist(sample_name):
    res_df = pd.read_csv(os.path.join(utils.Pathing.out_root, sample_name) + '.csv')
    res_df = res_df['r']
    res_df.to_excel(os.path.join(utils.Pathing.out_root, sample_name) + '.xlsx')
    # plt.hist(res_df, bins=[0, 5, 10, 15, 20, 25])
    plt.hist(res_df)
    plt.xscale('log')
    plt.title('Diameter distribution (ln scale)')
    ax = plt.gca()
    if sample_name == 'model':
        ax.axvline(15, color='black')
    d_mean = np.exp(np.log(res_df).mean())
    ax.axvline(d_mean, color='red')
    ax.xaxis.set_minor_locator(plt.NullLocator())
    ax.xaxis.set_major_locator(plt.MaxNLocator())
    ax.xaxis.set_major_formatter(plt.ScalarFormatter())
    plt.savefig(os.path.join(utils.Pathing.out_root, sample_name) + '_hist.jpg')
    plt.close()
