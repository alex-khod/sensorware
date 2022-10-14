import os
import unittest

from sensor.canbus import flashing


class TestFolderPacking(unittest.TestCase):

    def test_packing(self):
        test_dir = os.path.join("tests", "test_dir", "test")
        test_out_dir = os.path.join("tests", "test_dir", "test_out")
        test_out_zip = test_out_dir + ".zip"
        flashing.pack_dir(test_dir, test_out_zip)
        assert os.path.isfile(test_out_zip)
        flashing.unpack_dir(test_out_zip, test_out_dir)
        test_file_path = os.path.join(test_out_dir, "test", "test_file")
        assert os.path.isfile(test_file_path)
