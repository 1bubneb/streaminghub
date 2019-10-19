#!/usr/bin/env python3
import codecs
import socket
import numpy as np

# constants
from connectors.lsl_streaming import create_outlet

BUFFER_SIZE = 4096
# acc - 3 - axis acceleration
# bvp - Blood Volume Pulse
# gsr - Galvanic Skin Response
# ibi - Inter-Beat Interval and Heartbeat
# tmp - Skin Temperature
# bat - Device Battery
# tag - Tag taken from the device
STREAMS = ['acc', 'bvp', 'gsr', 'tmp', 'ibi', 'bat', 'tag']
STREAM_IDS = ['E4_Acc', 'E4_Bvp', 'E4_Gsr', 'E4_Temperature', 'E4_Ibi', 'E4_Hr', 'E4_Battery', 'E4_Tag']
TAGS = []


# states
class STATES:
    NEW__ = 'new'
    WAITING__ = 'waiting'
    NO_DEVICES__ = 'no_devices'
    DEVICES_FOUND__ = 'devices_found'
    CONNECTED_TO_DEVICE__ = "connected"
    READY_TO_SUBSCRIBE__ = "ready_to_subscribe"
    SUBSCRIBE_COMPLETED__ = "subscribe completed"
    STREAMING__ = 'streaming'


# commands
class COMMANDS:
    DEVICE_LIST__ = 'device_list'
    DEVICE_CONNECT__ = 'device_connect'
    DEVICE_SUBSCRIBE__ = 'device_subscribe'
    PAUSE__ = "pause"


channel_description = {
    'E4_Acc_x': {
        'unit': 'g',
        'type': 'acceleration',
        'freq': '32'
    },
    'E4_Acc_y': {
        'unit': 'g',
        'type': 'acceleration',
        'freq': '32'
    },
    'E4_Acc_z': {
        'unit': 'g',
        'type': 'acceleration',
        'freq': '32'
    },
    'E4_Bvp': {
        'unit': '',
        'type': '',
        'freq': '64'
    },
    'E4_Ibi': {
        'unit': 'ms',
        'type': 'interval',
        'freq': 'N/A'
    },
    'E4_Gsr': {
        'unit': '',
        'type': '',
        'freq': '4'
    },
    'E4_Temperature': {
        'unit': '',
        'type': '',
        'freq': '4'
    },
    'E4_Hr': {
        'unit': '',
        'type': '',
        'freq': 'N/A'

    },
    'E4_Battery': {
        'unit': '',
        'type': '',
        'freq': '64'
    },
    'E4_Tag': {
        'unit': '',
        'type': '',
        'freq': '64'
    }
}

OUTLET = create_outlet('Empatica_E4', 'wristband', channel_description, 'Empatica', 'E4', '1234567890')

# State
STATE = STATES.NEW__
DEVICE = None
stream_i = 0


def msg(s_: str) -> bytes:
    return codecs.encode(s_ + '\r\n')


def set_devices_connected(num: int, devices: list):
    global DEVICE
    print('%d device(s) found: %s' % (num, ', '.join([id_ for id_, name_ in devices])))
    set_state(STATES.NO_DEVICES__ if num == 0 else STATES.DEVICES_FOUND__)
    if num > 1:
        # ask user to select device
        id_ = input('Select device id: ')
        if id_ in [y for x, y in devices]:
            DEVICE = id_
        else:
            print('Invalid device id')
            exit(1)
    elif num == 1:
        id_ = devices[0][0]
        print('Selecting %s' % id_)
        DEVICE = id_


def set_state(state: str):
    global STATE
    STATE = state


def process_incoming_msgs():
    global stream_i
    in_msg: str = codecs.decode(s.recv(BUFFER_SIZE))
    # parse message(s)
    in_msg_cmds = [x.strip() for x in in_msg.split('\r\n')]
    for cmd in in_msg_cmds:
        if len(cmd) == 0 or cmd.find(' ') == -1:
            continue
        # Handle responses to request
        if cmd[0] == 'R':
            cmd = cmd[2:]
            i = cmd.find(' ')
            # DEVICE_LIST response
            if cmd[:i] == COMMANDS.DEVICE_LIST__:
                cmd = cmd[i + 1:]
                # list devices connected
                i = cmd.find(' ')
                num = int(cmd[:i]) if i != -1 else 0
                devices = []
                if num > 0:
                    cmds = cmd[i + 3:].split(' | ')
                    if len(cmds) != num:
                        print('device count mismatch')
                        exit(1)
                    devices = [x.split(' ') for x in cmds]
                set_devices_connected(num, devices)
            # DEVICE_CONNECT response
            elif cmd[:i] == COMMANDS.DEVICE_CONNECT__:
                cmd = cmd[i + 1:]
                i = cmd.find(' ')
                status = cmd[:i] if i != -1 else cmd
                if status == "ERR":
                    cmd = cmd[i + 1:]
                    print('Error connecting to device: %s' % cmd)
                    exit(1)
                elif status == "OK":
                    print('Connected to device')
                    set_state(STATES.CONNECTED_TO_DEVICE__)
            # PAUSE response
            elif cmd[:i] == COMMANDS.PAUSE__:
                cmd = cmd[i + 1:]
                i = cmd.find(' ')
                status = cmd[:i] if i != -1 else cmd
                if status == "ERR":
                    cmd = cmd[i + 1:]
                    print('Error pausing streaming: %s' % cmd)
                    exit(1)
                elif status == "ON":
                    print('Streaming paused')
                    set_state(STATES.READY_TO_SUBSCRIBE__)
                elif status == "OFF":
                    print('Streaming resumed')
                    set_state(STATES.STREAMING__)
            # DEVICE SUBSCRIBE response
            elif cmd[:i] == COMMANDS.DEVICE_SUBSCRIBE__:
                cmd = cmd[i + 1:]
                i = cmd.find(' ')
                stream_type = cmd[:i]
                cmd = cmd[i + 1:]
                i = cmd.find(' ')
                status = cmd[:i] if i != -1 else cmd
                if status == "ERR":
                    cmd = cmd[i + 1:]
                    print('Error subscribing to stream %s: %s' % (stream_type, cmd))
                    exit(1)
                elif status == "OK":
                    print('Subscribed: %s' % stream_type)
                    stream_i += 1
                    if stream_i == len(STREAMS):
                        set_state(STATES.SUBSCRIBE_COMPLETED__)
                    else:
                        set_state(STATES.READY_TO_SUBSCRIBE__)
        # Handle data stream
        elif STATE == STATES.STREAMING__:
            process_data_stream(cmd)


def process_data_stream(cmd: str):
    d = next(filter(lambda x: cmd.startswith(x), STREAM_IDS), None)
    if d is not None:
        # data stream. handle accordingly
        try:
            if d == 'E4_Acc':
                t, x, y, z = [float(n) for n in cmd.split(' ')[1:]]
                if OUTLET.have_consumers():
                    OUTLET.push_sample([x, y, z, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan], t)
            elif d == 'E4_Bvp':
                t, v = [float(n) for n in cmd.split(' ')[1:]]
                if OUTLET.have_consumers():
                    OUTLET.push_sample([np.nan, np.nan, np.nan, v, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan], t)
            elif d == 'E4_Gsr':
                t, v = [float(n) for n in cmd.split(' ')[1:]]
                if OUTLET.have_consumers():
                    OUTLET.push_sample([np.nan, np.nan, np.nan, np.nan, np.nan, v, np.nan, np.nan, np.nan, np.nan], t)
            elif d == 'E4_Temperature':
                t, v = [float(n) for n in cmd.split(' ')[1:]]
                if OUTLET.have_consumers():
                    OUTLET.push_sample([np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, v, np.nan, np.nan, np.nan], t)
            elif d == 'E4_Ibi':
                t, v = [float(n) for n in cmd.split(' ')[1:]]
                if OUTLET.have_consumers():
                    OUTLET.push_sample([np.nan, np.nan, np.nan, np.nan, v, np.nan, np.nan, np.nan, np.nan, np.nan], t)
            elif d == 'E4_Hr':
                t, v = [float(n) for n in cmd.split(' ')[1:]]
                if OUTLET.have_consumers():
                    OUTLET.push_sample([np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, v, np.nan, np.nan], t)
            elif d == 'E4_Battery':
                t, v = [float(n) for n in cmd.split(' ')[1:]]
                if OUTLET.have_consumers():
                    OUTLET.push_sample([np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, v, np.nan], t)
            elif d == 'E4_Tag':
                t = [float(n) for n in cmd.split(' ')[1]]
                if OUTLET.have_consumers():
                    OUTLET.push_sample([np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, t], t)
            print('.', end='', flush=True)
        except Exception as e:
            print('Error: ', e)
    else:
        # some other message
        print('Unknown message: %s' % cmd)


def handle_outgoing_msgs():
    if STATE == STATES.NEW__:
        # request devices list
        print('Getting list of devices...')
        s.send(msg(COMMANDS.DEVICE_LIST__))
        set_state(STATES.WAITING__)
    elif STATE == STATES.NO_DEVICES__:
        print('No devices found!')
        exit(1)
    elif STATE == STATES.DEVICES_FOUND__:
        # connect to device
        print('Connecting to device...')
        s.send(msg("%s %s" % (COMMANDS.DEVICE_CONNECT__, DEVICE)))
        set_state(STATES.WAITING__)
    elif STATE == STATES.CONNECTED_TO_DEVICE__:
        # pause streaming initially
        print('Initializing...')
        s.send(msg("%s ON" % COMMANDS.PAUSE__))
        set_state(STATES.WAITING__)
    elif STATE == STATES.READY_TO_SUBSCRIBE__:
        # subscribe to streams
        stream = STREAMS[stream_i]
        print('Subscribing to stream: %s' % stream)
        s.send(msg("%s %s ON" % (COMMANDS.DEVICE_SUBSCRIBE__, stream)))
        set_state(STATES.WAITING__)
    elif STATE == STATES.SUBSCRIBE_COMPLETED__:
        # begin streaming data
        print('Requesting data')
        s.send(msg("%s OFF" % COMMANDS.PAUSE__))
        set_state(STATES.STREAMING__)


if __name__ == '__main__':
    # Create socket connection
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("10.211.55.3", 28000))
    # event loop
    while True:
        handle_outgoing_msgs()
        process_incoming_msgs()
