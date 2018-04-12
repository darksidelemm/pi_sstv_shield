# Project Horus Raspberry Pi SSTV Shield Project


## Dependencies
### Hardware
* Raspberry Pi Model A or B 
  * If using a RPi without an audio output socket, you will also need a USB sound card or some other DAC.

* DRA818V/U on shield, with the following connections to the Pi:

DRA818 Pin | Function | RPi Pin Header
-----------|----------|---------------
1 | Squelch | 12 (GPIO 18, Active Low)
5 | PTT | 11 (GPIO 17, Active Low)
6 | Power Down | Not Used
7 | High/Low Power | 13 (GPIO 27) - Optional
9 | GND | <Any ground pin>
16 | RXD (UART Input) | 8 (UART0 TX)
17 | TXD (UART Output) | 10 (UART0 RX)

Currently the Squelch, Power-Down and High/Low pins are un-used in this software.


### Software Dependencies

Obtain most of the dependencies via apt-get:
```
$ sudo apt-get install sox imagemagick python-pip python-serial python-picamera python-rpi.gpio
```

Then, use pip to install the remaining dependencies:
```
$ sudo pip install pySSTV
```


## Operation
```
$ sudo python picam_sstv.py
```

TODO:
* Figure out why the Pi stops playing audio after a while (dodgy PWM audio driver probably)
* Make image transmission non-blocking, so images can be captured and converted while transmission is taking place.
* Add image overlays.
