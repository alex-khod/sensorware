import configparser
import os

from sensor import utils

CONFIG_FILENAME = os.path.join(utils.Pathing.main_root, 'config.ini')
defaults = {
    'allow_capture': 'True',
    'send_states': 'True',
    'param_1_th': '0.0',
    'param_2_th': '0.0',
    'min_delay': '0.1',
}


def get_config():
    conf = configparser.ConfigParser(defaults)
    conf.read(CONFIG_FILENAME)
    return conf


def set_config(cp):
    with open(CONFIG_FILENAME, 'w') as f:
        cp.write(f)
