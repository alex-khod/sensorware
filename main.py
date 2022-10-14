import argparse
import logging
import os
import sys

from sensor import utils, workflow
from sensor.gui.canbus import gui_app as can_gui
from sensor.gui.vents import app as vents_gui
from sensor.gui.picam import hosted as picamera_gui

VERSION = "1.0.5.0"


def setup():
    log_dir = os.path.join(utils.Pathing.codes_root, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "main.log")

    logging.basicConfig(format='%(levelname)s %(asctime)s %(message)s',
                        datefmt="%Y-%m-%d, %H:%M:%S",
                        filename=log_file,
                        level=logging.DEBUG)
    # log to std
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    logging.info('Sensor daemon %s running @ "%s" \n%s' %
                 (VERSION, sys.executable, sys.version))


def process_command():
    parser = argparse.ArgumentParser(description='description')

    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.add_parser("run", help="Default workflow daemon")
    subparsers.add_parser("vents", help="Simple gui for testing vents and gpio")
    subparsers.add_parser("cangui", help="Simple gui for testing CAN bus messaging")
    subparsers.add_parser("picamera", help="Use PiCameraApp gui to capture photos & control vents")

    args = parser.parse_args()
    return parser, args


def main():
    setup()

    parser, args = process_command()

    if args.cmd == 'run':
        workflow.run()
    elif args.cmd == 'vents':
        vents_gui()
    elif args.cmd == 'cangui':
        can_gui()
    elif args.cmd == "picamera":
        picamera_gui()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
