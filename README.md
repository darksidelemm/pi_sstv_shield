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
6 | Power Down | Not connected in Rev B PCB.
7 | High/Low Power | 13 (GPIO 27) - Optional
9 | GND | <Any ground pin>
16 | RXD (UART Input) | 8 (UART0 TX)
17 | TXD (UART Output) | 10 (UART0 RX)

Currently the Squelch, Power-Down and High/Low pins are un-used in this software.

Note: If you connect the high/low pin to the Raspberry Pi, you must NOT tie this pin high. It will result in the DRA818 drawing about 10W of power and heating up very quickly. It must be either floating (high power), or set low (low power).

### Software Dependencies

Obtain most of the dependencies via apt-get:
```
$ sudo apt-get install sox imagemagick python-pip python-serial python-picamera python-rpi.gpio python-pil libgd-dev libmagic-dev
```

Now we need to go compile the `pisstvpp` SSTV encoder:
```
$ git clone https://github.com/hatsunearu/pisstvpp.git
$ cd pisstvpp
$ make
$ cp pisstvpp ../
$ cd ..
```


## Operation
### DRA818 Configuration
First, configure the DRA818 module to your desired transmit frequency:
```
$ sudo python dra818.py --frequency 146.525
```
You can optionally add `--test` to have the script key the radio up for one second after programming.

### Setting Volume Levels
You will need to adjust volume levels into the DRA818 to avoid the audio clipping. Ideally this is done with a deviation monitor (i.e. a service monitor), but you can sometimes do it by ear.

 * Configure the DRA818 onto your desired frequency as above.
 * Create/get an audio file to test with. I'd suggest generating maybe 30 second of 1 kHz tone with Audacity, and copying it to your Raspberry Pi.
 * Use the dra818 library to set the PTT to on:
```
$ python
> from dra818 import *
> dra818_setup_io()
> dra818_ptt(True)
```
 * Now in another terminal use `aplay your_audio_file.wav` to play your audio file.
 * In yet another terminal, run `alsamixer` and set the volume to about 50.
 * Use either the trimpot on the PCB, or alsamixer to adjust the audio level to acheive approx 2.5 kHz transmit deviation.
 * Set the PTT to off
```
> dra818_ptt(False)
```
All done!

### Transmitting Images
You will now need a PiCam connected. Check you can capture images using the raspistill utility (i.e. `raspistill -o test.jpg`).

Once you are sure this is working, you can run:
```
$ sudo python picam_sstv.py
```


TODO:
* Do we really need to use sudo? (probably not)
* Figure out why the Pi stops playing audio after a while (dodgy PWM audio driver probably)
* Make image transmission non-blocking, so images can be captured and converted while transmission is taking place.
* Add image/text overlays.
