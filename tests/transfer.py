import os
import unittest

from sensor.canbus import transfer


class TestTxRx(unittest.TestCase):

    def setUp(self):
        path = os.path.join(os.path.dirname(__file__), 'data')
        src = os.path.join(path, 'test_rgb.jpg')
        dest = os.path.join(path, 'test_rgb_dest.jpg')
        self.file_tx = transfer.FileTx(src)
        self.file_rx = transfer.FileRx(dest)

    def tearDown(self):
        self.file_tx.close()
        self.file_rx.close()

    def test_tx_to_rx(self):
        file_tx = self.file_tx
        file_rx = self.file_rx

        blocks = []
        while True:
            try:
                file_tx.read_next()
            except StopIteration:
                # file_tx.close()
                break
            n_chk = file_tx.count_chunks()
            crc = file_tx.get_crc32()
            chunks = list(file_tx.read_chunks())
            blocks.append([n_chk, crc, chunks])

        for n_chk, crc, chunks in blocks:
            file_rx.chunks = []
            file_rx.supposed_crc = crc
            for chk in chunks:
                file_rx.append_chunk(chk)
            # print(len(file_rx.chunks), n_chk)
            if file_rx.block_complete(n_chk):

                if file_rx.check_crc32():
                    pass
                    # file_rx.write_block()
                else:
                    raise ValueError("Invalid CRC")
            else:
                raise ValueError("Incomplete block")
        # file_rx.close()

    def test_repeat_read(self):
        file_tx = self.file_tx
        file_tx.read_next()
        chunks_a = list(file_tx.read_chunks())
        chunks_b = list(file_tx.read_chunks())
        assert (chunks_a == chunks_b)
