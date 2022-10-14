import binascii
import math
import os
import struct
import time
import shutil
import traceback

from sensor.canbus.requests import REQUEST
from sensor.canbus import flashing
from sensor import utils


class TransferHandler:
    def __init__(self, can_app):
        self.can_app = can_app
        self.file_tx = None
        self.file_rx = None

    def send_block(self):
        crc32 = self.file_tx.get_crc32()
        packed_crc = struct.pack('>L', crc32)
        self.send_chunk(TRANSFER.CHECKSUM, packed_crc)
        n_chk = self.file_tx.count_chunks()
        for chk in self.file_tx.read_chunks():
            self.send_chunk(n_chk, chk)
            time.sleep(self.can_app.min_delay)

    def send_chunk(self, n_chk, data):
        msg = bytes([REQUEST.GET_BYTES, n_chk]) + data
        self.can_app.cmd_res(msg)

    def request_get_file(self, arg_id):
        db_id = arg_id
        if db_id == TRANSFER.REFLASH:
            db_path = flashing.FLASH_OUT_PATH
        else:
            db_path = os.path.join(utils.Pathing.codes_root, 'transfer', str(db_id), 'snaps.db')
        self.file_rx = FileRx(db_path)
        self.can_app.cmd_get_bytes()

    def request_get_bytes(self, arg_id):
        # on get bytes request send get bytes response
        try:
            db_id = arg_id
            if db_id == TRANSFER.REFLASH:
                db_path = flashing.FLASH_IN_PATH
            else:
                db_path = os.path.join(utils.Pathing.codes_root, 'dbs', str(db_id), 'snaps.db')
            self.file_tx = FileTx(db_path)
            self.can_app.cmd_res([REQUEST.GET_FILE, db_id])
        except Exception:
            print("Couldn't find database #%d for transfer (%s)" % (arg_id, db_path))
            traceback.print_exc()
            self.can_app.cmd_res([REQUEST.GET_FILE, TRANSFER.NOT_FOUND])

    def response_get_file(self, arg_id):
        if arg_id == TRANSFER.RESEND:
            # there was communication error - attempt to resend previous block (without guards)
            try:
                if self.file_tx and self.file_tx.block:
                    self.send_block()
            except Exception:
                traceback.print_exc()
                self.can_app.cmd_res([REQUEST.GET_BYTES, TRANSFER.NOT_FOUND])
        else:
            # just send next part of file
            try:
                if self.file_tx:
                    self.file_tx.read_next()
                    self.send_block()
                else:
                    print("Didn't find file for transfer")
                    self.can_app.cmd_res([REQUEST.GET_BYTES, TRANSFER.NOT_FOUND])
            except StopIteration:
                self.file_tx.close()
                self.file_tx = None
                self.send_chunk(TRANSFER.STOP, bytes())
                print("Transfer completed")

    def response_get_bytes(self, arg_id, data):
        # print("Transfer command #arg", arg_id)
        if not self.file_rx:
            print("Client transfer error")
            return
        if arg_id == TRANSFER.NOT_FOUND:
            print("Server file transfer isn't initialized with GET_FILE request")
        if arg_id == TRANSFER.CHECKSUM:
            crc = struct.unpack('>L', data)[0]
            self.file_rx.supposed_crc = crc
        elif arg_id == TRANSFER.STOP:
            self.file_rx.close()
            self.file_rx = None
            print("Transfer finished")
        elif 0 < arg_id <= TRANSFER.MAX_CHUNKS:
            # print("Writing bytes")
            n_chk = arg_id
            self.file_rx.append_chunk(data)
            if self.file_rx.block_complete(n_chk):
                if self.file_rx.check_crc32():
                    self.file_rx.write_block()
                    self.can_app.cmd_req([REQUEST.GET_BYTES, TRANSFER.NEXT])
                    if self.file_rx.update_progress():
                        print("%d packets written" %
                              self.file_rx.writes)
                else:
                    self.can_app.cmd_req([REQUEST.GET_BYTES, TRANSFER.RESEND])
                self.file_rx.chunks = []

    def clear_db(self, db_id):
        self.file_tx = None
        try:
            path = os.path.join(utils.Pathing.db_root, str(db_id))
            print(path)
            shutil.rmtree(path, ignore_errors=True)
            self.can_app.cmd_res([REQUEST.CLEAR_DB, TRANSFER.OK])
        except Exception:
            traceback.print_exc()
            self.can_app.cmd_res([REQUEST.CLEAR_DB, TRANSFER.ERROR])


class TRANSFER:
    NONE = 0
    OK = 1
    ERROR = 2
    NEXT = 3
    RESEND = 4
    FLASH_ERROR = 5

    MAX_CHUNKS = 220
    CHECKSUM = MAX_CHUNKS + 1
    STOP = MAX_CHUNKS + 2
    NOT_FOUND = MAX_CHUNKS + 3
    CHUNK_SIZE = 6
    BLOCK_SIZE = CHUNK_SIZE * MAX_CHUNKS
    REFLASH = 255


class FileTx():
    """
        Class intended for reading file for transfer in blocks divided by chunks.
        Each block consists of up to MAX_CHUNKS chunks with CRC32 check.
        Each chunk is a pinch of bytes to transfer.
    """

    def __init__(self, fn):
        self.f = open(fn, 'rb')
        fsize = os.fstat(self.f.fileno()).st_size
        self.block = None
        self.n_blocks = fsize // TRANSFER.BLOCK_SIZE
        self.tx = self.read_blocks()

    def read_blocks(self):
        while True:
            _bytes = self.f.read(TRANSFER.BLOCK_SIZE)
            if not _bytes:
                break
            yield _bytes

    def count_chunks(self):
        actual_len = len(self.block)
        bs = TRANSFER.CHUNK_SIZE
        n_chk = math.ceil(actual_len / bs)
        # print(n_chk)
        return n_chk

    def read_next(self):
        self.block = next(self.tx)
        return self.block

    def read_chunks(self):
        for i in range(0, len(self.block), TRANSFER.CHUNK_SIZE):
            chunk = self.block[i:i + TRANSFER.CHUNK_SIZE]
            # print(chunk)
            yield chunk

    def get_crc32(self):
        crc = binascii.crc32(self.block, 0)
        return crc

    def reset(self):
        self.f.seek(0, 0)
        self.tx = self.read_blocks()

    def read(self):
        for _ in self.tx:
            for c in self.read_chunks():
                yield c

    def close(self):
        self.f.close()


class FileRx():
    WRITES_TO_UPDATE = 100

    def __init__(self, fn):
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        self.writes = 0
        self.f = open(fn, 'wb')
        self.chunks = []
        self.supposed_crc = None
        self.block = None

    def append_chunk(self, data):
        self.chunks += [bytes(data)]

    def block_complete(self, n_chk):
        complete = len(self.chunks) == n_chk
        return complete

    def check_crc32(self):
        from functools import reduce
        self.block = reduce(lambda a, b: a + b, self.chunks, bytes())
        crc = binascii.crc32(self.block, 0)
        return crc == self.supposed_crc

    def write_block(self):
        if self.block:
            self.f.write(self.block)
            self.writes += 1

    def update_progress(self):
        return (self.writes % self.WRITES_TO_UPDATE) == 0

    def close(self):
        self.f.close()
