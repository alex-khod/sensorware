import collections
import os
import struct
import threading
import time
import traceback

import can
import numpy as np

from sensor import settings, utils
from sensor.canbus.requests import REQUEST
from sensor.canbus.transfer import TRANSFER

QUEUE_MAX_LEN = 300
ERROR_SEND_DELAY = 3


class StateHandler:
    param_names = {
        0: 'param_1',
        1: 'param_2',
        2: 'param_1_th',
        3: 'param_2_th',
        4: 'min_delay'
    }

    allow_set = {2, 3, 4}

    def get_default_buffer(self):
        return [None] * 9

    def __init__(self, can_app):
        self.can_app = can_app
        self.send_requests = True

        self.param_1 = np.float32(0.0)
        self.param_2 = np.float32(0.0)

        config = settings.get_config()['DEFAULT']

        self.send_states = config.getboolean('send_states')
        self.allow_capture = config.getboolean('allow_capture')
        self.param_1_th = np.float32(config['param_1_th'])
        self.param_2_th = np.float32(config['param_2_th'])
        self.min_delay = np.float32(config['min_delay'])
        self.n_particles = 0

        self.que_items_ready_to_fetch = 0
        self.que = collections.deque([], maxlen=QUEUE_MAX_LEN)
        self.return_buffer = self.get_default_buffer()
        self.data_lock = threading.RLock()

        self.camera_ok = 0xFF
        self.vents_ok = 0xFF
        self.ready = 0

    def send_queue_item(self, request_id):
        try:
            with self.data_lock:
                item = self.que.popleft()
        except IndexError:
            # que is empty : fail silently
            # self.send_message(self.priority, PGN.RESPONSE, [request_id, 0, REQUEST.ERROR])
            return
        for i, value in enumerate(item):
            self.can_app.cmd_res([request_id, i] + list(utils.encode_float(value)))

    def recv_queue_item(self, request_id, arg_id, data):
        if not len(data) == 4:
            if data[0] == TRANSFER.ERROR:
                print("Error transferring que item")
            return
        try:
            self.return_buffer[arg_id] = struct.unpack('>f', data)[0]
            decoded = len(
                list(filter(lambda x: x is not None, self.return_buffer)))
            if decoded == len(self.return_buffer):
                print(
                    "Progress message: #%d, CAN_CAPTURE=%d, VENTS_OK=%d, CAMERA=%d, "
                    "%d particles, z=%.3f, P=%.3f, dP=%.3f, free space:%.1f mb" % tuple(self.return_buffer))
                recv_path = os.path.join(utils.Pathing.codes_root, 'transfer', 'recv.csv')
                os.makedirs(os.path.dirname(recv_path), exist_ok=True)
                with open(recv_path, 'a') as f:
                    f.write('%d;%d;%d;%d;%d;%f;%f;%f;%f\n' % tuple(self.return_buffer))
                self.return_buffer = self.get_default_buffer()
        except Exception:
            print("Error decoding arg#%d for request#%d" %
                  (arg_id, request_id))
            traceback.print_exc()
            self.return_buffer = self.get_default_buffer()
            self.can_app.cmd_res([request_id, arg_id, TRANSFER.ERROR])

    def valid_param_name(self, param_id):
        try:
            param_name = self.param_names[param_id]
            return True
        except KeyError:
            print("Unknown param: id=%d" % param_id)
            return False

    def set_param(self, param_id, data):
        if not self.valid_param_name(param_id):
            return
        param_name = self.param_names[param_id]
        try:
            if param_id not in self.allow_set:
                raise KeyError("Can't set param %s(#%d)" %
                               (param_name, param_id))
            # 42F60000 = 123.0
            if not data:
                print('Error - empty data')
                return
            value = struct.unpack('>f', data)[0]
            if value < 0 and param_name == 'min_delay':
                raise ValueError("Subzero param value")
            print('Setting %s=%.3f from 0x%s' %
                  (param_name, value, bytearray(data).hex()))
            with self.data_lock:
                setattr(self, param_name, value)
            self.set_config_key(param_name, value)
            self.can_app.cmd_res([REQUEST.SET_PARAM, TRANSFER.OK])
        except Exception:
            print("Error setting param %s to as %s" % (param_name, data))
            traceback.print_exc()
            self.can_app.cmd_res([REQUEST.SET_PARAM, TRANSFER.ERROR])

    def get_param(self, param_id):
        if not self.valid_param_name(param_id):
            return
        param_name = self.param_names[param_id]
        try:
            value = getattr(self, param_name)
            bt = struct.pack('>f', value)
            print('Returning %s=%.3f as 0x%s' % (param_name, value, bt.hex()))
            self.can_app.cmd_res(bytes([REQUEST.GET_PARAM, param_id]) + bt)
        except Exception:
            print("Error returning param ", param_name)
            traceback.print_exc()
            self.can_app.cmd_res([REQUEST.GET_PARAM, TRANSFER.ERROR])

    def client_get_param(self, param_id, data):
        if not self.valid_param_name(param_id):
            return
        param_name = self.param_names[param_id]
        try:
            value = struct.unpack('>f', data)[0]
            print('Received %s=%f' % (param_name, value))
        except Exception:
            print("Error receiving param %s#%d" %
                  (param_name, param_id))
            traceback.print_exc()

    def add_queue_item(self, item):
        with self.data_lock:
            self.que.append(item)

    def set_data(self, data):
        with self.data_lock:
            self.ready = data['ready']
            self.param_1 = data['param_1']
            self.param_2 = data['param_2']
            self.n_particles = data['n_particles']
            self.camera_ok = data['camera_ok']
            self.vents_ok = data['vents_ok']

    def send_state_message(self):
        if self.send_states:
            with self.data_lock:
                data = [
                           int(self.ready),
                           int(self.param_1 > self.param_1_th),
                           int(self.param_2 > self.param_2_th),
                           min(self.n_particles, 0xFF),
                           int(self.camera_ok),
                       ] + 3 * [0xFF]
            self.can_app.cmd_state(data)

    def set_config_key(self, key, value):
        config = settings.get_config()
        config['DEFAULT'][key] = str(value)
        print(value)
        settings.set_config(config)

    def callback(self):
        if self.send_requests:
            if self.que_items_ready_to_fetch > 0:
                for _ in range(self.que_items_ready_to_fetch):
                    self.can_app.request_state()
                    time.sleep(self.min_delay)
                self.que_items_ready_to_fetch = 0
            else:
                try:
                    self.can_app.cmd_get_que_length()
                    self.can_app.request_state()
                except can.CanError:
                    print("Error sending state request")
                    time.sleep(ERROR_SEND_DELAY)
                    traceback.print_exc()
