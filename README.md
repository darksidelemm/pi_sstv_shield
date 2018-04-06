# Project Horus Raspberry Pi SSTV Shield Project


## Dependencies
### Hardware
* Raspberry Pi Model A or B 
  * If using a RPi without an audio output socket, you will also need a USB sound card or some other DAC.

* DRA818V/U on shield, with the following connections to the Pi:

DRA818 Pin | Function | RPi Header Pin
-----------|----------|---------------
1 | Squelch | ?? 
5 | PTT | ??
6 | Power Down | ??
7 | High/Low Power | ??
9 | GND | <Any ground pin>
16 | RXD (UART Input) | ??
17 | TXD (UART Output) | ??


### Software
The scripts in this repository have the following dependencies:

* 'sox' or some other audio player utility. 
* Python (2/3)
  * pyserial - obtain using distro package manager, i.e. `sudo apt-get install python-serial`
  * pySSTV  - obtain via pip, i.e. `sudo pip install pySSTV`


