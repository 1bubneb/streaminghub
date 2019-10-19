from pylsl import StreamInfo, StreamOutlet, IRREGULAR_RATE


def create_outlet(d_id: str, d_type: str, c_desc: dict, d_manufacturer, d_name, d_serial):
    """
    Generate LSL outlet from Metadata
    :rtype: StreamOutlet
    :param d_id: id for the device, usually the manufacturer and device type combined
    :param d_type: type of device (e.g. EEG, Wristband)
    :param c_desc: channel description. keys should be channel id. values should contain ('freq', 'unit' and 'type')
    :param d_manufacturer: manufacturer of the device
    :param d_name: name of the device
    :param d_serial: serial number of the device (for uniqueness)
    :return: StreamOutlet object to send data streams through
    """
    info = StreamInfo(d_id, d_type, len(c_desc.keys()), IRREGULAR_RATE, 'float32', d_serial)
    info.desc().append_child_value("manufacturer", d_manufacturer).append_child_value("device", d_name)
    channels = info.desc().append_child("channels")
    for c in c_desc.keys():
        channels.append_child("channel") \
            .append_child_value("label", c) \
            .append_child_value("unit", c_desc[c]['unit']) \
            .append_child_value("type", c_desc[c]['type']) \
            .append_child_value("freq", c_desc[c]['freq']) \
            # next make an outlet; we set the transmission chunk size to 32 samples and
    # the outgoing buffer size to 360 seconds (max.)
    return StreamOutlet(info, 32, 60)
