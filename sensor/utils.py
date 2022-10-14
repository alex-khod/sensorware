import os
import random
import struct
import time
from datetime import datetime

import psutil


class Pathing:

    @staticmethod
    def count_dbs(db_root):
        for i in range(1_000_000):
            path = os.path.abspath(os.path.join(db_root, str(i)))
            if os.path.isdir(path) and os.listdir(path):
                yield path
            else:
                break

    @staticmethod
    def get_new_db_dir(db_root):
        new = len(list(Pathing.count_dbs(db_root)))
        path = os.path.abspath(os.path.join(db_root, str(new)))
        return path

    codes_root = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', '..'))

    main_root = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..'))

    sample_images_path = os.path.join(codes_root, 'data', 'samples', 'model')

    out_root = os.path.join(codes_root, 'out')
    image_dir = os.path.join(codes_root, 'photos')

    image_dir = os.path.abspath(image_dir)
    db_root = os.path.join(codes_root, 'dbs')


def get_random_string(length):
    import random
    import string
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    print("Random string of length", length, "is:", result_str)
    return result_str


def image_save_to(folder=None, ext='jpg'):
    folder = folder or Pathing.image_dir
    fmt = '%m-%d-%Y-%H=%M=%S_%f.' + ext
    time_stamp = datetime.now().strftime(fmt)
    path = os.path.join(folder, time_stamp)
    return Pathing.image_dir, path


def random_string(strlen=16):
    alpha_digits = 'qwertyuiopasdfghjklzxcvbnm1234567890'
    res = [random.choice(alpha_digits) for x in range(strlen)]
    res = ''.join(res)
    return res


def list_images(path, formats=None):
    if formats is None:
        formats = [".png", ".bmp", ".jpg", ".jpeg"]
    for image in list_files(path, formats):
        yield image


def list_files(path, formats=None):
    for fn in os.listdir(path):
        ext = os.path.splitext(fn)[1]
        if ext in formats:
            fp = os.path.join(path, fn)
            yield fn, fp


def get_date_str():
    return datetime.now().strftime('%Y-%m-%d; %H=%M=%S')


def get_image_fn(image_dir, prefix):
    date_str = datetime.now().strftime('%Y-%m-%d; %H=%M=%S')
    image_fn = os.path.join(image_dir, '%s%s.jpg' % (date_str, prefix))
    return image_fn


def get_free_space(path):
    free = psutil.disk_usage(path).free
    free_mb = free / 1024 / 1024
    return free_mb


def print_memory_usage():
    """Prints current memory usage stats.
    https://stackoverflow.com/a/15495136

    :return: None
    """
    PROCESS = psutil.Process(os.getpid())
    MEGA = 10 ** 6

    total, available, percent, used, free = psutil.virtual_memory()
    total, available, used, free = total / \
                                   MEGA, available / MEGA, used / MEGA, free / MEGA
    proc = PROCESS.memory_info()[1] / MEGA
    print('process = %s total = %s available = %s used = %s free = %s percent = %s'
          % (proc, total, available, used, free, percent))


def wait_until(func, timeout):
    time_out_on = time.time() + timeout
    while time.time() < time_out_on:
        if func():
            return True
        time.sleep(0.1)
    return False


def encode_float(value):
    value = float(value)
    bt = struct.pack('>f', value)
    return bt


def decode_float(hex_str):
    bt = bytes.fromhex(hex_str)
    value = struct.unpack('>f', bt)[0]
    return value


def benchmark(msg_fmt):
    def benchmark_decorator(func):
        def _func():
            start = time.time()
            result = func()
            duration_ms = (1000 * (time.time() - start))
            print(msg_fmt % duration_ms)
            return result

        return _func

    return benchmark_decorator
