import math
import os
import types

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw

from sensor import utils, imaging


def get_out_path(affix, image_fn, ext=None, out_root=utils.Pathing.out_root):
    basename = os.path.basename(image_fn)
    name, _ext = os.path.splitext(basename)
    if ext is None:
        ext = _ext
    out_fn = '%s_%s%s' % (name, affix, ext)
    upper_folder = os.path.abspath(os.path.join(image_fn, '..'))
    upper_name = os.path.basename(upper_folder)
    out_dir = os.path.join(out_root, upper_name)
    return os.path.join(out_dir, out_fn)


def diamToAreaPx(diam, pixel_to_um):
    # maxDiameter to maxArea
    # pixel_to_um == 4.9
    # maxDiameter = 100, maxDiameterPx = 490
    # maxAreaPx = pi * (490 ** 2) == 754296
    # pixel_to_um == 2.45 => maxAreaPx == 188574

    area = math.pi * ((diam * pixel_to_um) ** 2)
    return area


def get_iou(left, right):
    """
        Get intersection-over-union metric for two bounding boxes.
        https://stackoverflow.com/questions/25349178/calculating-percentage-of-bounding-box-overlap-for-image-detector-evaluation
    """

    lx0, ly0, lx1, ly1 = left
    wl, hl = lx1 - lx0, ly1 - ly0
    rx0, ry0, rx1, ry1 = right
    wr, hr = rx1 - rx0, ry1 - ry0

    assert lx0 < lx1
    assert ly0 < ly1
    assert rx0 < rx1
    assert ry0 < ry1

    # determine the coordinates of the intersection rectangle
    x_left = max(lx0, rx0)
    y_top = max(ly0, ry0)
    x_right = min(lx1, rx1)
    y_bottom = min(ly1, ry1)

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)

    left_area = wl * hl
    right_area = wr * hr

    iou = intersection_area / float(left_area + right_area - intersection_area)
    assert iou >= 0.0
    assert iou <= 1.0
    return iou


def rect_plotter(a_figs, scale=4, aspect=16 / 9):
    """
        Multi-plot figures onto a rectangle.

        Usage:
        for fig in rect_plotter(a_figs):
            plt.imshow(fig)
    """
    figs = a_figs
    if isinstance(a_figs, types.GeneratorType):
        figs = list(a_figs)
    n_figs = len(figs)
    a = math.ceil(math.sqrt(n_figs * aspect))
    b = math.ceil(n_figs / a)
    ix = 1
    plt.figure(figsize=(a * scale, b * scale))
    for i in range(b):
        for j in range(a):
            # length, width
            ax = plt.subplot(b, a, ix)
            ax.set_xticks([])
            ax.set_yticks([])
            fid = ix - 1
            fig = figs[fid]
            yield fig
            ix += 1
            if ix > n_figs:
                break
    plt.tight_layout()


def draw_box(image, box, color="green", width=3, text=None):
    # draw bounding box onto an image
    img = Image.fromarray(image)
    img_draw = ImageDraw.Draw(img)
    x, y, x1, y1 = box
    img_draw.rectangle((x, y, x1, y1), outline=color, width=width)
    if text is not None:
        img_draw.text((x1, y1), text, font=None,
                      fill="white", stroke_fill="black")
    return np.array(img)


def draw_box_to_plot(box, color='green', text=None, text_color="white"):
    # draw bounding box onto a plot
    x, y, x1, y1 = box
    # function accepts x, y, w, h
    plt.gca().add_patch(plt.Rectangle((x, y), x1 - x, y1 -
                                      y, color=color, fill=False, linewidth=1))
    if text is not None:
        plt.annotate(text, (x - 16, y - 3), color=text_color)


def plot_detections(pathes, detections, class_colors, truth=None,
                    plot_scale=None, plot_aspect=None):
    """
        Draw detection results onto a plot
        :pathes - list of image filenames to draw on
        :detections - list of [boxes, confidences, idxs]
        boxes - list of bounding boxes (x0, y0, x1 y1)
        confidences - confidence
        :truth - list of bounding boxes that represent ground truth objects
        """
    assert len(pathes) == len(detections)
    images = list(map(lambda x: imaging.load_rgb_image(x), pathes))
    fns = list(map(lambda x: os.path.basename(x), pathes))
    if truth is None:
        truth = [[]] * len(images)
    for img, fn, det, truth_boxes in zip(rect_plotter(images, scale=plot_scale, aspect=plot_aspect),
                                         fns, detections, truth):
        plt.imshow(img)
        plt.title(fn)
        for box, confidence, class_id in zip(*det):
            annot = "%.2f%%" % (confidence * 100)
            draw_box_to_plot(box, class_colors[class_id], annot)
        for truth_box in truth_boxes:
            draw_box_to_plot(truth_box, "white")


def draw_detections(pathes, detections, class_colors, truth=None, out_dir="detected"):
    """
    Draw detection results onto an image and save it to "detected" dir next to the image
    :pathes - list of image filenames to draw on
    :detections - list of [boxes, confidences, idxs]
    boxes - list of bounding boxes (x0, y0, x1 y1)
    confidences - confidence
    :truth - list of bounding boxes that represent ground truth objects
    """
    images = list(map(imaging.load_rgb_image, pathes))
    if truth is None:
        truth = [[]] * len(images)
    for img, path, det, truth_boxes in zip(images, pathes, detections, truth):
        for box, confidence, class_id in zip(*det):
            annot = "%.2f%%" % (confidence * 100)
            img = draw_box(img, box, class_colors[class_id], text=annot)
        for truth_box in truth_boxes:
            img = draw_box(img, truth_box, "white")

        out_dir = os.path.join(os.path.dirname(path), out_dir)
        out_path = os.path.join(out_dir, os.path.basename(path))
        os.makedirs(out_dir, exist_ok=True)
        imaging.save_image(img, out_path)


def plot_truth(pathes, truth):
    detections = [[]] * len(pathes)
    plot_detections(pathes, detections, class_colors=[], truth=truth)


def draw_truth(pathes, truth):
    detections = [[]] * len(pathes)
    draw_detections(pathes, detections, class_colors=[], truth=truth, out_dir="truth")
