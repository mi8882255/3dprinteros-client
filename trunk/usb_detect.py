#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import logging
import usb.core
import usb.util
import usb.backend.libusb1
import serial.tools.list_ports

import config
import utils

def format_vid_or_pid(vid_or_pid):
    return hex(vid_or_pid)[2:].zfill(4).upper()

def get_devices():
    logger = logging.getLogger('app.' + __name__)
    try:
        devices = usb.core.find(find_all=True)
        devices = list(devices)        
        if not devices:
            raise ValueError
    except ValueError:           
        backend_from_our_directory = usb.backend.libusb1.get_backend(find_library=utils.get_libusb_path)
        devices = usb.core.find(find_all=True, backend=backend_from_our_directory)
    if not devices:
        logger.warning("Libusb error: no usb devices was detected. Check if libusb1 is installed.")
    device_data_dcts = []
    for dev in devices:
        device_dct = {
            'VID': format_vid_or_pid(dev.idVendor), #cuts "0x", fill with zeroes if needed, doing case up
            'PID': format_vid_or_pid(dev.idProduct),
        }
        try:
            SNR = str(usb.util.get_string(dev, dev.iSerialNumber)) #originaly it's unicode, but this provoke bugs
            if "x" in SNR:
                 SNR = None
        except:
            SNR = None
        try:
            manufacturer = dev.manufacturer  # can provoke PIPE ERROR
        except (usb.core.USBError, AttributeError):
            manufacturer = None
        try:
            product = dev.product  # can provoke PIPE ERROR
        except (usb.core.USBError, AttributeError):
            product = None
        device_dct['SNR'] = SNR
        device_dct['Manufacturer'] = manufacturer
        device_dct['Product'] = product
        device_dct['COM'] = get_port_by_vid_pid_snr(device_dct['VID'], device_dct['PID'], SNR)
        device_data_dcts.append(device_dct)
        #dev.close()
        #logger.debug(device_dct)
    return device_data_dcts

def get_port_by_vid_pid_snr(vid, pid, snr=None):
    vid_pid_re = re.compile('(?:.*\=([0-9-A-Z-a-f]+):([0-9-A-Z-a-f]+) SNR)|(?:.*VID_([0-9-A-Z-a-f]+)\+PID_([0-9-A-Z-a-f]+)\+)')
    for port_dct in serial.tools.list_ports.comports():
        match = vid_pid_re.match(port_dct[2])
        if match:
            vid_of_comport = match.group(1)
            pid_of_comport = match.group(2)
            if not vid_of_comport or not pid_of_comport:
                vid_of_comport = match.group(3)
                pid_of_comport = match.group(4)
            vid_of_comport = vid_of_comport.zfill(4).upper()
            pid_of_comport = pid_of_comport.zfill(4).upper()
            if vid == vid_of_comport and pid == pid_of_comport:
                if snr and not 'SNR=' + snr in port_dct[2].upper():
                    continue
                return port_dct[0]
    return None

def sort_and_add_profile(devices):
    printers = []
    profiles = config.config['profiles']
    for device in devices:
        for profile in profiles:
            for vid_pid in profiles[profile][u'vids_pids']:
                if vid_pid[0] == device['VID']:
                    if not vid_pid[1] or vid_pid[1] == device['PID']:
                        dct = {}
                        dct.update(profiles[profile])
                        dct.update(device)
                        printers.append(dct)
    return printers

def get_printers():
    logger = logging.getLogger('app.' + __name__)
    devices = get_devices()
    printers = sort_and_add_profile(devices)
    if len(printers) == 0:
        printers = get_unknown_printers(devices)
    #logger.info('Detected USB printers: ' + str(printers))
    return printers


def get_unknown_printers(devices):
    devices = filter(lambda x: x['COM'] is not None, devices)
    printers = []
    for device in devices:
        profiles = config.config['profiles']
        for profile in profiles:
            if not profiles[profile]['print_from_binary']:
                dct = { 'guess' : 'true' }
                dct.update(profiles[profile])
                dct.update(device)
                printers.append(dct)
    return printers

if __name__ == '__main__':
    import json
    import time
    before = time.time()
    #for _ in range(0,100):
    printers = get_printers()
    print "time=" + str( time.time() - before )
    print json.dumps(printers)
