#!/usr/bin/env python
#
# Basic DRA818 Programming
# Currently only supporting basic TX support, with no tone.
# Refer command set in: http://www.dorji.com/docs/data/DRA818V.pdf
#
# Mark Jessop <vk5qi@rfhead.net>
#
import argparse
import serial
import time

try:
    import RPi.GPIO as GPIO
except RuntimeError:
    print("ERROR: Could not load RPi GPIO Libraries.")

# DRA818 GPIO Connections
DRA818_PTT = 17
DRA818_SQ = 18 # Currently we ignore this. Pin 18 also appears to conflict with the PWM outputs used for audio.
DRA818_HL = 27 # Currently un-used. Leave HL pin floating for 1W output power.
DRA818_PD = 22 # Currently un-used

# Default Transmitter / Squelch Settings
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
    # We need to issue this command to be able to send further commands.
    _s.write("AT+DMOCONNECT\r\n")
    time.sleep(1.00)
    _response = _s.readline()
    print("Connect Response: %s" % _response)

    # Send the programming command..
    _s.write(_dmosetgroup)
    time.sleep(1.00)

    # Read in the response from the module.
    _response = _s.readline()
    _s.close()
    
    print("Response: %s" % _response.strip())


def dra818_setup_io():
    ''' Configure the RPi IO pins for communication with the DRA818 module '''
    # All pin definitions are in Broadcom format.
    GPIO.setmode(GPIO.BCM)
    # Configure pins, and set initial values.
    GPIO.setup(DRA818_PTT, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(DRA818_HL, GPIO.OUT, initial=GPIO.LOW) # WARNING - Do NOT set this pin high. 
    GPIO.setup(DRA818_PD, GPIO.OUT, initial=GPIO.HIGH)


def dra818_high_power(enabled):
    ''' Set the DRA818 to high power by floating the HL input '''
    if enabled:
        GPIO.setup(DRA818_HL, GPIO.IN)
    else:
        GPIO.setup(DRA818_HL, GPIO.OUT, initial=GPIO.LOW)


def dra818_ptt(enabled):
    ''' Set the DRA818's PTT on or off '''
    if enabled:
        GPIO.output(DRA818_PTT, GPIO.LOW)
    else:
        GPIO.output(DRA818_PTT, GPIO.HIGH)


def dra818_read_squelch():
    ''' Read the DRA818 Squelch line. Return True if there is signal detected. '''
    return not GPIO.input(DRA818_SQ)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--frequency", type=float, default=146.500, help="Transmit Frequency (MHz)")
    parser.add_argument("--port", type=str, default='/dev/ttyAMA0', help="Serial port connected to module.")
    parser.add_argument("--test", action="store_true", default=False, help="Test transmitter after programming with 1s of PTT.")
    args = parser.parse_args()

    dra818_program(args.port, args.frequency)

    if args.test:
        dra818_ptt(True)
        time.sleep(1)
        dra818_ptt(False)


