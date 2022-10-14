import os
import traceback
import zipfile
from shutil import rmtree

from sensor import utils

"""
Flash checklist:
1. Ensure transferrable file (premade zip or zip entire contents of utils.main_root).
2. Transfer file to server.
3. Prepare server for flashing (cease operation).
4. Backup
5. Remove all files.
6. Unzip transferrable.
7. Restart.

1. python.zip
2. Flash command:
cmd_get_file TRANSFER.REFLASH

"""

FLASH_IN_PATH = os.path.join(utils.Pathing.codes_root, 'transfer', 'flash_in.zip')
FLASH_OUT_PATH = os.path.join(utils.Pathing.codes_root, 'transfer', 'flash_out.zip')
BACKUP_PATH = os.path.join(utils.Pathing.codes_root, 'transfer', 'backup.zip')


def pack_dir(src_dir, dest_zip, pack_source_dir=True):

    def pack(path, zip_file, pack_source_dir=True):
        if pack_source_dir:
            base_path = os.path.abspath(os.path.join(path, '..'))
        else:
            base_path = os.path.abspath(path)
        for root, _, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, base_path)
                zip_file.write(file_path, arcname)

    zip_file = zipfile.ZipFile(dest_zip, 'w', zipfile.ZIP_DEFLATED)
    pack(src_dir, zip_file, pack_source_dir)
    zip_file.close()


def unpack_dir(src_zip, dest_dir):
    zip_file = zipfile.ZipFile(src_zip, 'r', zipfile.ZIP_DEFLATED)
    zip_file.extractall(dest_dir)


def prepare():
    pack_dir(utils.Pathing.main_root, FLASH_IN_PATH, pack_source_dir=True)


def backup():
    pack_dir(utils.Pathing.main_root, BACKUP_PATH, pack_source_dir=True)


def restore():
    unpack_dir(BACKUP_PATH, utils.Pathing.codes_root)


def reflash():
    try:
        # backup
        backup()
        # cleanup
        rmtree(utils.Pathing.main_root, ignore_errors=True)
        # unpack flash
        unpack_dir(FLASH_OUT_PATH, utils.Pathing.codes_root)
    except Exception:
        restore()
        print("Error while restoring backup")
        traceback.print_exc()
