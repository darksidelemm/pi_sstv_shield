#!/usr/bin/env python
#
# Basic DRA818 Programming
# Currently only supporting basic TX support, with no tone.
#
# Mark Jessop <vk5qi@rfhead.net>
#
import argparse
import serial
import time

MODE = 1 # 1 = FM (supposedly 5kHz deviation), 0 = NFM (2.5 kHz Deviation)
SQUELCH = 5 # Squelch Value, 0-8
CTCSS = '0000'

def dra818_program(port='/dev/ttyAMA0',
                frequency=146.500):
    ''' Program a DRA818U/V radio to operate on a particular frequency. '''


    _dmosetgroup = "AT+DMOSETGROUP=%d,%3.4f,%3.4f,%s,%d,%s\r\n" % (
        MODE, frequency, frequency, CTCSS, SQUELCH, CTCSS)

    print("Sending: %s" % _dmosetgroup.strip())

    # Open serial port
    _s = serial.Serial(
            port=port,
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS)

    # Send the programming command..
    _s.write(_dmosetgroup)
    time.sleep(1.00)

    # Read in the response from the module.
    _response = _s.readline()
    _s.close()
    
    print("Response: %s" % _response.strip())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--frequency", type=float, default=146.500, help="Transmit Frequency (MHz)")
    parser.add_argument("--port", type=str, default='/dev/ttyAMA0', help="Serial port connected to module.")
    args = parser.parse_args()

    dra818_program(args.port, args.frequency)
