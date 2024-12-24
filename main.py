# MIT License
#
# Copyright (c) 2024 mjteter
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import datetime
import json
# import locale
import logging
import math
import os
import random
import sys
import threading
import time

import pygame
import pygame.gfxdraw
import requests
from PIL import Image, ImageDraw


PATH = sys.path[0] + '/'
# ICON_PATH = PATH + '/icons/'
LOGO_PATH = PATH + '/resources/logos/'
FONT_PATH = PATH + '/resources/fonts/'
LOG_PATH = PATH + '/logs/'

# create logger
logger = logging.getLogger(__package__)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger.setLevel(logging.INFO)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

config_data = open(PATH + 'config.json').read()
config = json.loads(config_data)

theme_config = config["THEME"]

theme_settings = open(PATH + theme_config).read()
theme = json.loads(theme_settings)

SERVER = config['NHL_URL']
HEADERS = {}

# locale.setlocale(locale.LC_ALL, (config['LOCALE']['ISO'], 'UTF-8'))  # assume USA

THREADS = []

try:
    # if you do local development you can add a mock server (e.g. from postman.io our your homebrew solution)
    # simple add this variables to your config.json to save api-requests
    # or to create your own custom test data for your own dashboard views)
    if config['ENV'] == 'DEV':
        SERVER = config['MOCKSERVER_URL']
        # WEATHERBIT_IO_KEY = config['WEATHERBIT_DEV_KEY']
        HEADERS = {'X-Api-Key': f'{config["MOCKSERVER_API_KEY"]}'}

    elif config['ENV'] == 'STAGE':
        # WEATHERBIT_IO_KEY = config['WEATHERBIT_DEV_KEY']
        pass
    elif config['ENV'] == 'Pi':
        if config['DISPLAY']['FRAMEBUFFER'] is not False and config['DISPLAY']['ADD_ENV_VARS']:
            # using the dashboard on a raspberry with TFT displays might make this necessary
            os.putenv('SDL_FBDEV', config['DISPLAY']['FRAMEBUFFER'])
            os.environ["SDL_VIDEODRIVER"] = "fbcon"

        LOG_PATH = '/mnt/ramdisk/'
        # WEATHERBIT_IO_KEY = config['WEATHERBIT_IO_KEY']

    logger.info(f"STARTING IN {config['ENV']} MODE")


except Exception as e:
    logger.warning(e)
    quit()

