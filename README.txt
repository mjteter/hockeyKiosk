Caution: This code was written by an idiot.  Use at your own peril.

https://learn.adafruit.com/adafruit-pitft-3-dot-5-touch-screen-for-raspberry-pi/easy-install-2

64-bit boards seem to work better

Download latest working image (2023-12-11 as of 10/27/24):
64-bit: https://downloads.raspberrypi.org/raspios_lite_arm64/images/
32-bit: https://downloads.raspberrypi.org/raspios_lite_armhf/images/

Pins used by PiTFT hat:
BOARD | BCM
---------------
  12  | GPIO18
  18  | GPIO24 (only if using pwm to control brightness)
  19  | GPIO10 (SPI MOSI)
  21  | GPIO9  (SPI MISO)
  22  | GPIO25
  23  | GPIO11 (SPI SCLK)
  24  | GPIO8  (SPI CE0)
  26  | GPIO7  (SPI CE1)
  27  | GPIO0  (I2C ID EEPROM)
  28  | GPIO1  (I2C ID EEPROM)




Setup Virtual Environment:

sudo apt update
sudo apt upgrade -y

sudo apt install -y pigpiod
sudo apt install -y git gh python3-pip
sudo apt install -y xorg   # may want to add --without-recommends

sudo apt install python3-venv
python -m venv --system-site-packages adavenv
python -m venv .venv

Activate Virtual Environment:

source adavenv/bin/activate

or
#!/<path-to-venv>/bin/python
at top of scripts

PiTFT Installer Script

cd ~
pip install --upgrade adafruit-python-shell click
git clone https://github.com/adafruit/Raspberry-Pi-Installer-Scripts.git
cd Raspberry-Pi-Installer-Scripts


Console Mode Install Commands:

sudo -E env PATH=$PATH python3 adafruit-pitft.py --display=35r --rotation=90 --install-type=console

OR

sudo -E env PATH=$PATH python3 adafruit-pitft.py --display=35r --rotation=90 --install-type=mirror

Or Interactive Install:

sudo -E env PATH=$PATH python3 adafruit-pitft.py


PWM Backlight Control:
Turn off STMPE control:
sudo sh -c 'echo "0" > /sys/class/backlight/soc\:backlight/brightness'

Turn on STMPE control (will stop PWM modulation):
sudo sh -c 'echo "1" > /sys/class/backlight/soc\:backlight/brightness'

Manipulate GPIO 18 to change backlighting:
gpio -g mode 18 pwm
gpio pwmc 1000
gpio -g pwm 18 100
gpio -g pwm 18 1023
gpio -g pwm 18 0


Switch to regular venv
source .venv/bin/activate

pip install pigpio pygame-ce
pip install pygame-menu --no-deps


api power play from live game
"situation": {
    "homeTeam": {
      "abbrev": "PHI",
      "situationDescriptions": [
        "PP"
      ],
      "strength": 5
    },
    "awayTeam": {
      "abbrev": "VGK",
      "strength": 4
    },
    "situationCode": "1451",
    "timeRemaining": "01:21",
    "secondsRemaining": 81


 "situation": {
    "homeTeam": {
      "abbrev": "BOS",
      "strength": 4
    },
    "awayTeam": {
      "abbrev": "PHI",
      "strength": 4
    },
    "situationCode": "1441"
  },

sudo fbi -T 2 -d /dev/fb1 -noverbose -a my_picture.jpg

export DISPLAY=:0
os.putenv('SDL_FBDEV', '/dev/fb1')
os.putenv('SDL_VIDEODRIVER', 'fbcon')
