#!/usr/bin/env python3
import argparse
import configparser
import sys

from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from rmstable import pwr2delay, delay2pwr


def str2bool(v):
    if v is None:
        return False
    if isinstance(v, int):
        return True if v != 0 else False

    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def moc_get_power_level():
    regs = client.read_holding_registers(address=0, count=1, unit=unit)
    current_delay = regs.getRegister(0)
    current_pwr_level = delay2pwr[int(current_delay/10)]
    return current_pwr_level



def moc_set_power_level(level):
    if level < 0:
        level = 0
    if level > 999:
        level = 999
    if level == 0:
        client.write_register(0, 9801, unit=unit)
        return

    delay = pwr2delay[level]

    client.write_register(0, delay, unit=unit)





if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='gtil2',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--ini-file", help="ini file", default="ducas.ini", required=False)
    parser.add_argument("--set-pwr-level", help="set current", type=str, required=False)

    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.ini_file)

    # gtil2
    serial_device = config['modbus_gtil']['device']
    baudrate = config.getint('modbus_gtil', 'baudrate')
    unit = config.getint('modbus_gtil', 'unit')

    print(f"gtil2:: device: {serial_device}, baudrate: {baudrate}, unit: {unit}")
    client = ModbusClient(method='rtu', port=serial_device, baudrate=baudrate, timeout=0.5)
    client.connect()

    current_pwr_level = moc_get_power_level()
    print(f"current pwr level: {current_pwr_level}")
    if args.set_pwr_level is not None:
        new_pwr_level = int(args.set_pwr_level, 0)
        print(f"setting new pwr level to {new_pwr_level} 0x{new_pwr_level:02x}")
        moc_set_power_level(new_pwr_level)
