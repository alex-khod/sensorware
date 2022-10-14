import logging
import struct
import traceback

import j1939
import numpy as np

from sensor import utils, proxy
from sensor.canbus import transfer, shutdown, state
from sensor.canbus.requests import REQUEST

TRANSFER = transfer.TRANSFER

logger = logging.getLogger('j1939')
logger.setLevel(logging.INFO)
logging.getLogger('can').setLevel(logging.INFO)

DEFAULT_DEVICE_ADDR = 10
STANDARD_SEND_DELAY = 1.0
MIN_SEND_DELAY = 0.1

"""
The interpretation of the PDU specific (PS) field changes based on the PF value:

If the PF is between 0 and 239,
the message is addressable (PDU1) and the PS field contains the destination address.
If the PF is between 240 and 255,
the message can only be broadcast (PDU2) and the PS field contains a Group Extension.
"""


class PGN:
    # 65380 == 0xFF64
    STATE = j1939.ParameterGroupNumber(data_page=0, pdu_format=0xFF, pdu_specific=0x64).value
    # 65381 == 0xFF65
    REQUEST = j1939.ParameterGroupNumber(data_page=0, pdu_format=0xFF, pdu_specific=0x65).value
    # 65382 == 0xFF66
    RESPONSE = j1939.ParameterGroupNumber(data_page=0, pdu_format=0xFF, pdu_specific=0x66).value
    ERROR = j1939.ParameterGroupNumber(data_page=0, pdu_format=0xFF, pdu_specific=0x67).value
    WHOIS = j1939.ParameterGroupNumber(data_page=0, pdu_format=0xFF, pdu_specific=0x68).value
    SOFT_ID = j1939.ParameterGroupNumber(data_page=0, pdu_format=0xFE, pdu_specific=0xDA).value


def get_mid(priority, pgn, addr):
    mid = j1939.MessageId(priority=priority, parameter_group_number=pgn, source_address=addr)
    return mid


def init_app(device_addr=DEFAULT_DEVICE_ADDR, client_mode=False):
    name = j1939.Name(
        arbitrary_address_capable=1,
        industry_group=j1939.Name.IndustryGroup.Industrial,
        vehicle_system_instance=1,
        vehicle_system=1,
        function=1,
        function_instance=1,
        ecu_instance=1,
        manufacturer_code=666,
        identity_number=1234567
    )

    ecu = j1939.ElectronicControlUnit()
    ecu.connect(bustype=proxy.bustype, channel='can0')

    cnt = CanApp(name, device_addr, client_mode=client_mode)

    ecu.add_ca(controller_application=cnt)
    cnt.start()

    return cnt


class CanApp(j1939.ControllerApplication):
    FORCE_CAPTURE = 2

    def __init__(self, name, device_address_preferred=None, client_mode=False):
        self.client_mode = client_mode

        self.shutdown_handler = shutdown.ShutdownHandler(self)
        self.transfer_handler = transfer.TransferHandler(self)
        self.state_handler = state.StateHandler(self)

        self.priority = 6

        j1939.ControllerApplication.__init__(
            self, name, device_address_preferred)

    def cmd_req(self, msg):
        self.send_message(self.priority, PGN.REQUEST, msg)

    def cmd_res(self, msg):
        self.send_message(self.priority, PGN.RESPONSE, msg)

    def cmd_state(self, msg):
        self.send_message(self.priority, PGN.STATE, msg)

    def cmd_set_send_states(self, value):
        self.cmd_req([REQUEST.SET_SEND_STATES, value])

    def cmd_set_allow_capture(self, value):
        self.cmd_req([REQUEST.SET_ALLOW_CAPTURE, value])

    def cmd_set_default_send_states(self, value):
        self.cmd_req([REQUEST.SET_DEFAULT_SEND_STATES, value])

    def cmd_set_default_allow_capture(self, value):
        self.cmd_req([REQUEST.SET_DEFAULT_ALLOW_CAPTURE, value])

    def cmd_reboot(self):
        self.cmd_req([REQUEST.SHUTDOWN, shutdown.SHUTDOWN_TYPE.REBOOT])

    def cmd_shutdown(self):
        self.cmd_req([REQUEST.SHUTDOWN, shutdown.SHUTDOWN_TYPE.SHUTDOWN])

    def cmd_get_que_length(self):
        self.cmd_req([REQUEST.GET_QUE_LENGTH, 0])

    def cmd_get_file(self, arg_id):
        self.cmd_req([REQUEST.GET_FILE, arg_id])

    def cmd_enum_db(self):
        self.cmd_req([REQUEST.ENUM_DB, 0])

    def cmd_clear_db(self, arg_id):
        self.cmd_req([REQUEST.CLEAR_DB, arg_id])

    def cmd_get_bytes(self):
        self.cmd_req([REQUEST.GET_BYTES, 0])

    def request_state(self):
        self.cmd_req([REQUEST.GET_QUE_ITEM, 0])

    def cmd_set_param(self, param_id, value):
        try:
            value = np.float32(value)
            bt = struct.pack('>f', value)
            self.cmd_req(bytes([REQUEST.SET_PARAM, param_id]) + bt)
        except Exception:
            traceback.print_exc()

    def cmd_get_param(self, float_id):
        self.cmd_req([REQUEST.GET_PARAM, float_id])

    def start(self):
        self._ecu.add_timer(STANDARD_SEND_DELAY, self.timer_callback)
        return j1939.ControllerApplication.start(self)

    def stop(self):
        self._ecu.remove_timer(self.timer_callback)

    def parse_request_data(self, data):
        request_id, arg_id, data = data[0:2]
        data = data[2:len(data)]

        if not request_id:
            raise Exception('Error - empty request')
        if request_id >= REQUEST.UNKNOWN:
            raise Exception('Error - unknown request #%d' % request_id)

        return request_id, arg_id, data

    def on_message(self, pgn, data):
        mid = get_mid(0, pgn, 0)
        _pgn = j1939.ParameterGroupNumber()
        _pgn.from_message_id(mid)
        pgn = _pgn

        if not pgn.value in [PGN.REQUEST, PGN.RESPONSE]:
            print('PGN %d(0x%s) - Data Page (DP):%d, PDU Format (PF):%d, PDU Specific (PS): %s' %
                  (pgn.value, hex(pgn.value), pgn.data_page, pgn.pdu_format, pgn.pdu_specific))
            print('DATA (len %d):' % len(data), data)
            return

        try:
            # ValueError
            request_id, arg_id, data = self.parse_request_data(data)
            if pgn.value == PGN.REQUEST:
                self.trigger_on_request(request_id, arg_id, data)
            if pgn.value == PGN.RESPONSE:
                self.trigger_on_response(request_id, arg_id, data)
        except Exception:
            print("Unhandled exception for PGN %d" % pgn.value)
            traceback.print_exc()

    def if_ok_else_error(self, request_id, condition):
        if condition:
            self.cmd_res([request_id, TRANSFER.OK])
        else:
            self.cmd_res([request_id, TRANSFER.ERROR])
        return condition

    def trigger_on_request(self, request_id, arg_id, data):
        if self.client_mode and request_id not in REQUEST.TRANSFER:
            msg_fmt = "Error - received request#%d, arg#%d while in client mode"
            print(msg_fmt % (request_id, arg_id))
            return

        if request_id not in [REQUEST.GET_QUE_ITEM, REQUEST.GET_QUE_LENGTH]:
            print('Processing request#%d, arg#%d' % (request_id, arg_id))

        if request_id == REQUEST.SET_PARAM:
            self.state_handler.set_param(arg_id, data)
        elif request_id == REQUEST.GET_PARAM:
            self.state_handler.get_param(arg_id)
        elif request_id == REQUEST.GET_QUE_ITEM:
            self.state_handler.send_queue_item(request_id)
        elif request_id == REQUEST.GET_QUE_LENGTH:
            self.cmd_res([REQUEST.GET_QUE_LENGTH, min(0xFF, len(self.state_handler.que))])
        elif request_id == REQUEST.SET_ALLOW_CAPTURE:
            if self.if_ok_else_error(request_id, arg_id in (0, 1, self.FORCE_CAPTURE)):
                self.state_handler.allow_capture = arg_id
        elif request_id == REQUEST.SET_SEND_STATES:
            if self.if_ok_else_error(request_id, arg_id in (0, 1)):
                self.state_handler.send_states = bool(arg_id)
        elif request_id == REQUEST.SET_DEFAULT_ALLOW_CAPTURE:
            if self.if_ok_else_error(request_id, arg_id in (0, 1)):
                self.state_handler.set_config_key('allow_capture', bool(arg_id))
        elif request_id == REQUEST.SET_DEFAULT_SEND_STATES:
            if self.if_ok_else_error(request_id, arg_id in (0, 1)):
                self.state_handler.set_config_key('send_states', bool(arg_id))
        elif request_id == REQUEST.SHUTDOWN:
            self.shutdown_handler.process(arg_id)
        elif request_id == REQUEST.ENUM_DB:
            n_dbs = len(list(utils.Pathing.count_dbs(utils.Pathing.db_root)))
            self.cmd_res([REQUEST.ENUM_DB, min(0xFF, n_dbs)])
        elif request_id == REQUEST.GET_FILE:
            self.transfer_handler.request_get_file(arg_id)
        elif request_id == REQUEST.GET_BYTES:
            self.transfer_handler.request_get_bytes(arg_id)
        elif request_id == REQUEST.CLEAR_DB:
            self.transfer_handler.clear_db(arg_id)
        elif request_id == REQUEST.UPLOAD:
            self.cmd_req([REQUEST.GET_FILE, TRANSFER.REFLASH])

    def trigger_on_response(self, request_id, arg_id, data):
        if not self.client_mode and request_id not in REQUEST.TRANSFER:
            msg_fmt = "Error - received response#%d, arg#%d but isn't in client mode"
            print(msg_fmt % (request_id, arg_id))
            return
        if request_id == REQUEST.GET_PARAM:
            self.state_handler.client_get_param(arg_id, data)
        elif request_id == REQUEST.GET_QUE_ITEM:
            self.state_handler.recv_queue_item(request_id, arg_id, data)
        elif request_id == REQUEST.GET_QUE_LENGTH:
            self.state_handler.que_items_ready_to_fetch = arg_id
        elif request_id == REQUEST.ENUM_DB:
            print("Number of dbs is %d" % arg_id)
        elif request_id == REQUEST.SHUTDOWN:
            if arg_id == TRANSFER.OK:
                print('Shutdown confirmed')
        elif request_id == REQUEST.GET_FILE:
            self.transfer_handler.response_get_file(arg_id)
        elif request_id == REQUEST.GET_BYTES:
            self.transfer_handler.response_get_bytes(arg_id, data)
        else:
            print("Unhandled response #%d arg#%d" % (request_id, arg_id))

    def timer_callback(self, cookie):
        if not self.shutdown_handler.callback():
            return False

        # if not configured, skip
        if self.state != j1939.ControllerApplication.State.NORMAL:
            return True

        if self.client_mode:
            self.state_handler.callback()
        else:
            self.state_handler.send_state_message()
        return True
