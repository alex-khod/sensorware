""" Send test messages through can bus """

import time

import can
import j1939


def recv():
    bus = can.Bus(channel='can0', bustype='socketcan')
    for message in bus:
        msg = j1939.MessageId(can_id=message.arbitration_id)
        print('Priority:%d, PGN:%d, Source:%d' % (msg.priority, msg.parameter_group_number, msg.source_address))

        pgn = j1939.ParameterGroupNumber()
        pgn.from_message_id(msg)

        data = message.data

        print('PGN - Data Page (DP):%d, PDU Format (PF):%d, PDU Specific (PS): %s' %
              (pgn.data_page, pgn.pdu_format, pgn.pdu_specific))
        try:
            print('DATA (len %d):' % message.dlc, data.decode("ansi"))
        except UnicodeDecodeError:
            print('DATA (len %d):' % message.dlc, data)


def mid_from_values(priority, pgn, addr):
    mid = j1939.MessageId(priority=priority, parameter_group_number=pgn, source_address=addr)
    return mid


def send(mid_str, data_str):
    bus = can.Bus(channel='can0', bustype='socketcan')

    mid = int(mid_str, 16)
    # mid = mid_from_values(6, 65381, 240).can_id
    data = data_str.encode("ansi")
    for i in range(10):
        msg = can.Message(arbitration_id=mid, data=data, is_extended_id=True)
        bus.send(msg)
        time.sleep(0.5)
    bus.shutdown()
