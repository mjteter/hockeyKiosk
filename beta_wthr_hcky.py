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
# import math
import os
from pathlib import Path
# import random
import sys
import threading
import time

import pygame
import pygame.gfxdraw
import requests
from PIL import Image  # , ImageDraw


# PATH = sys.path[0] + '/'
# # ICON_PATH = PATH + '/icons/'
# LOGO_PATH = PATH + '/resources/logos/'
# FONT_PATH = PATH + '/resources/fonts/'
# LOG_PATH = PATH + '/logs/'

PATH = Path('.')
LOGO_PATH = PATH / 'resources' / 'logos'
FONT_PATH = PATH / 'resources' / 'fonts'
LOG_PATH = PATH / 'logs'

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

config_data = open(PATH / 'config.json').read()
config = json.loads(config_data)

theme_config = config["THEME"]

theme_settings = open(PATH / theme_config).read()
theme = json.loads(theme_settings)

SERVER = config['NHL_URL']
NHL_TEAM = config['NHL_TEAM']
GAME_ID = config['DEFAULT_GAME']
HEADERS = {}
# WEATHERBIT_COUNTRY = config['WEATHERBIT_COUNTRY']
# WEATHERBIT_LANG = config['WEATHERBIT_LANGUAGE']
# WEATHERBIT_POSTALCODE = config['WEATHERBIT_POSTALCODE']
# WEATHERBIT_HOURS = config['WEATHERBIT_HOURS']
# WEATHERBIT_DAYS = config['WEATHERBIT_DAYS']
# METRIC = config['LOCALE']['METRIC']

# locale.setlocale(locale.LC_ALL, (config['LOCALE']['ISO'], 'UTF-8'))  # assume USA

# list of keys for own dict matched to cascading list of keys from nhl api
GAME_MAP = {'id': ['id'],
            'awayTeam': ['awayTeam', 'abbrev'],
            'homeTeam': ['homeTeam', 'abbrev'],
            'awayScore': ['awayTeam', 'score'],
            'homeScore': ['homeTeam', 'score'],
            'awaySog': ['awayTeam', 'sog'],
            'homeSog': ['homeTeam', 'sog'],
            'gameState': ['gameState'],  # FINAL, OFF, LIVE, FUT, PRE, CRIT
            'period': ['periodDescriptor', 'number'],
            'clock': ['clock', 'timeRemaining'],
            'inIntermission': ['clock', 'inIntermission'],
            'awayStrength': ['situation', 'awayTeam', 'strength'],
            'homeStrength': ['situation', 'homeTeam', 'strength'],
            'awaySituation': ['situation', 'awayTeam', 'situationDescriptions'],
            'homeSituation': ['situation', 'homeTeam', 'situationDescriptions'],
            'situationClock': ['situation', 'timeRemaining']
            }

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

pygame.display.init()
pygame.mixer.quit()
pygame.font.init()
pygame.mouse.set_visible(config['DISPLAY']['MOUSE'])
pygame.display.set_caption('HockeyKiosk')


def quit_all():

    pygame.display.quit()
    pygame.quit()

    global THREADS

    for thread in THREADS:
        logger.info(f'Thread killed {thread}')
        thread.cancel()
        thread.join()

    sys.exit()


PWM = config['DISPLAY']['PWM']

if PWM:
    logger.info(f'set PWM for brightness control to PIN {PWM}')
    os.system(f"gpio -g mode {PWM} pwm")
else:
    logger.info('no PWM for brightness control configured')


# display settings from theme config
DISPLAY_WIDTH = int(config["DISPLAY"]["WIDTH"])
DISPLAY_HEIGHT = int(config["DISPLAY"]["HEIGHT"])
# DISPLAY_RATIO = float(DISPLAY_WIDTH / DISPLAY_HEIGHT)

# the drawing area to place all text and img on
SURFACE_WIDTH = 480
SURFACE_HEIGHT = 320
SURFACE_RATIO = float(SURFACE_WIDTH / SURFACE_HEIGHT)

# find the limiting factor in scaling
if float(DISPLAY_WIDTH / SURFACE_WIDTH) > float(DISPLAY_HEIGHT / SURFACE_HEIGHT):
    SCALE = float(DISPLAY_HEIGHT / SURFACE_HEIGHT)  # height limiting
    logger.info(f'display is limited by height, DISPLAY_HEIGHT: {DISPLAY_HEIGHT} set SCALE: {SCALE}')

else:
    SCALE = float(DISPLAY_WIDTH / SURFACE_WIDTH)  # width limiting
    logger.info(f'display is limited by width, DISPLAY_WIDTH: {DISPLAY_WIDTH} set SCALE: {SCALE}')

ZOOM = 1

FPS = config['DISPLAY']['FPS']
SHOW_FPS = config['DISPLAY']['SHOW_FPS']
AA = config['DISPLAY']['AA']
ANIMATION = config['DISPLAY']['ANIMATION']


# # correction for 1:1 displays like hyperpixel4 square
# if DISPLAY_WIDTH / DISPLAY_HEIGHT == 1:
#     logger.info(f'square display configuration detected')
#     square_width = int(DISPLAY_WIDTH / float(4 / 3))
#     SCALE = float(square_width / SURFACE_WIDTH)
#
#     logger.info(f'scale and display correction caused by square display')
#     logger.info(f'DISPLAY_WIDTH: {square_width} new SCALE: {SCALE}')

# # check if a landscape display is configured
# if DISPLAY_WIDTH > DISPLAY_HEIGHT:
#     logger.info(f'landscape display configuration detected')
#     SCALE = float(DISPLAY_HEIGHT / SURFACE_HEIGHT)
#
#     logger.info(f'scale and display correction caused by landscape display')
#     logger.info(f'DISPLAY_HEIGHT: {DISPLAY_HEIGHT} new SCALE: {SCALE}')

# zoom the application surface rendering to display size scale
if SCALE != 1:
    ZOOM = SCALE

    # if DISPLAY_WIDTH < SURFACE_WIDTH:
    #     logger.info('screen smaller as surface area - zooming smaller')
    #     SURFACE_WIDTH = DISPLAY_WIDTH
    #     SURFACE_HEIGHT = int(SURFACE_WIDTH / SURFACE_RATIO)
    #     logger.info(f'surface correction caused by small display')
    #     if DISPLAY_WIDTH == DISPLAY_HEIGHT:
    #         logger.info('small and square')
    #         ZOOM = round(ZOOM, 2)
    #     else:
    #         ZOOM = round(ZOOM, 1)
    #     logger.info(f'zoom correction caused by small display')
    # else:
    #     logger.info('screen bigger as surface area - zooming bigger')
    #     SURFACE_WIDTH = int(SURFACE_WIDTH * ZOOM)
    #     SURFACE_HEIGHT = int(SURFACE_HEIGHT * ZOOM)
    #     logger.info(f'surface correction caused by bigger display')
    SURFACE_WIDTH = int(SURFACE_WIDTH * ZOOM)
    SURFACE_HEIGHT = int(SURFACE_HEIGHT * ZOOM)

    logger.info(f'SURFACE_WIDTH: {SURFACE_WIDTH} SURFACE_HEIGHT: {SURFACE_HEIGHT} ZOOM: {ZOOM}')

FIT_SCREEN = (int((DISPLAY_WIDTH - SURFACE_WIDTH) / 2), int((DISPLAY_HEIGHT - SURFACE_HEIGHT) / 2))

# the real display surface
tft_surf = pygame.display.set_mode((DISPLAY_WIDTH, DISPLAY_HEIGHT), pygame.NOFRAME if config['ENV'] == 'Pi' else 0)

# the drawing area - everything will be drawn here before scaling and rendering on the display tft_surf
display_surf = pygame.Surface((SURFACE_WIDTH, SURFACE_HEIGHT))
# dynamic surface for status bar updates and dynamic values like fps
dynamic_surf = pygame.Surface((SURFACE_WIDTH, SURFACE_HEIGHT))
# # exclusive surface for the time
# time_surf = pygame.Surface((SURFACE_WIDTH, SURFACE_HEIGHT))
# exclusive surface for the mouse/touch events
mouse_surf = pygame.Surface((SURFACE_WIDTH, SURFACE_HEIGHT))
# surface for the weather data - will only be created once if the data is updated from the api
hockey_surf = pygame.Surface((SURFACE_WIDTH, SURFACE_HEIGHT))

clock = pygame.time.Clock()

logger.info(f'display with {DISPLAY_WIDTH}px width and {DISPLAY_HEIGHT}px height is set to {FPS} FPS with AA {AA}')

LOGO_SUFFIX = theme['LOGO_SUFFIX']

BACKGROUND = tuple(theme["COLOR"]["BACKGROUND"])
MAIN_FONT = tuple(theme["COLOR"]["MAIN_FONT"])
ACTIVE_FONT = tuple(theme["COLOR"]["ACTIVE_FONT"])
INACTIVE_FONT = tuple(theme["COLOR"]["INACTIVE_FONT"])
BORDER = tuple(theme["COLOR"]["BORDER"])
BLACK = tuple(theme["COLOR"]["BLACK"])
DARK_GRAY = tuple(theme["COLOR"]["DARK_GRAY"])
WHITE = tuple(theme["COLOR"]["WHITE"])
RED = tuple(theme["COLOR"]["RED"])
GREEN = tuple(theme["COLOR"]["GREEN"])
BLUE = tuple(theme["COLOR"]["BLUE"])
LIGHT_BLUE = tuple((BLUE[0], 210, BLUE[2]))
DARK_BLUE = tuple((BLUE[0], 100, 255))
YELLOW = tuple(theme["COLOR"]["YELLOW"])
ORANGE = tuple(theme["COLOR"]["ORANGE"])
VIOLET = tuple(theme["COLOR"]["VIOLET"])
COLOR_LIST = [BLUE, LIGHT_BLUE, DARK_BLUE]

FONT_MEDIUM = theme["FONT"]["MEDIUM"]
FONT_BOLD = theme["FONT"]["BOLD"]
MENU_SIZE = int(theme["FONT"]["MENU_SIZE"] * ZOOM)
SCORE_SIZE = int(theme["FONT"]["SCORE_SIZE"] * ZOOM)
SMALL_SIZE = int(theme["FONT"]["SMALL_SIZE"] * ZOOM)
BIG_SIZE = int(theme["FONT"]["BIG_SIZE"] * ZOOM)

FONT_SMALL = pygame.font.Font(FONT_PATH / FONT_MEDIUM, SMALL_SIZE)
FONT_SMALL_BOLD = pygame.font.Font(FONT_PATH / FONT_BOLD, SMALL_SIZE)
FONT_BIG = pygame.font.Font(FONT_PATH / FONT_MEDIUM, BIG_SIZE)
FONT_BIG_BOLD = pygame.font.Font(FONT_PATH / FONT_BOLD, BIG_SIZE)
FONT_MENU = pygame.font.Font(FONT_PATH / FONT_MEDIUM, MENU_SIZE)
FONT_SCORE = pygame.font.Font(FONT_PATH / FONT_BOLD, SCORE_SIZE)

# WEATHERICON = 'unknown'
#
# FORECASTICON_DAY_1 = 'unknown'
# FORECASTICON_DAY_2 = 'unknown'
# FORECASTICON_DAY_3 = 'unknown'
AWAY_LOGO = 'unknown'
HOME_LOGO = 'unknown'

CONNECTION_ERROR = True
REFRESH_ERROR = True
PATH_ERROR = True
# PRECIPTYPE = 'NULL'
# PRECIPCOLOR = WHITE

CONNECTION = False
READING = False
UPDATING = False

JSON_DATA = {}


def image_factory(image_path: Path):
    result = {}
    for img in os.listdir(image_path):
        image_id = img.split('.')[0]
        if image_id == "":
            pass
        else:
            result[image_id] = Image.open(image_path / img)
    return result


# class Particles(object):
#     def __init__(self):
#         self.size = int(20 * ZOOM)
#         self.count = 20
#         self.surf = pygame.Surface((self.size, self.size))
#
#     def create_particle_list(self):
#
#         particle_list = []
#
#         for i in range(self.count):
#             x = random.randrange(0, self.size)
#             y = random.randrange(0, self.size)
#             w = int(1 * ZOOM)
#             h = random.randint(int(2 * ZOOM), int(3 * ZOOM))
#             speed = random.choice([1, 2, 3])
#             color = random.choice(COLOR_LIST)
#             direct = random.choice([0, 0, 1])
#             particle_list.append([x, y, w, h, speed, color, direct])
#         return particle_list
#
#     def move(self, surf, particle_list):
#         # Process each snow flake in the list
#         self.surf.fill(BACKGROUND)
#         self.surf.set_colorkey(BACKGROUND)
#
#         if not PRECIPTYPE == config['LOCALE']['PRECIP_STR']:
#
#             for i in range(len(particle_list)):
#
#                 particle = particle_list[i]
#                 x, y, w, h, speed, color, direct = particle
#
#                 # Draw the snow flake
#                 if PRECIPTYPE == config['LOCALE']['RAIN_STR']:
#                     pygame.draw.rect(self.surf, color, (x, y, w, h), 0)
#                 else:
#                     pygame.draw.rect(self.surf, PRECIPCOLOR, (x, y, 2, 2), 0)
#
#                 # Move the snow flake down one pixel
#                 particle_list[i][1] += speed if PRECIPTYPE == config['LOCALE']['RAIN_STR'] else 1
#                 if random.choice([True, False]):
#                     if PRECIPTYPE == config['LOCALE']['SNOW_STR']:
#                         particle_list[i][0] += 1 if direct else 0
#
#                 # If the snow flake has moved off the bottom of the screen
#                 if particle_list[i][1] > self.size:
#                     # Reset it just above the top
#                     y -= self.size
#                     particle_list[i][1] = y
#                     # Give it a new x position
#                     x = random.randrange(0, self.size)
#                     particle_list[i][0] = x
#
#             surf.blit(self.surf, (int(155 * ZOOM), int(140 * ZOOM)))


class DrawString:
    def __init__(self, surf, string: str, font, color, y: int):
        """
        :param string: the input string
        :param font: the fonts object
        :param color: a rgb color tuple
        :param y: the y position where you want to render the text
        """
        self.string = string
        self.font = font
        self.color = color
        self.y = int(y * ZOOM)
        self.size = self.font.size(self.string)
        self.surf = surf

    def left(self, offset=0):
        """
        :param offset: define some offset pixel to move strings a little bit more left (default=0)
        """

        x = int(10 * ZOOM + (offset * ZOOM))

        self.draw_string(x)

    def right(self, offset=0):
        """
        :param offset: define some offset pixel to move strings a little bit more right (default=0)
        """

        x = int((SURFACE_WIDTH - self.size[0] - (10 * ZOOM)) - (offset * ZOOM))

        self.draw_string(x)

    def center(self, parts, part, offset=0):
        """
        :param parts: define in how many parts you want to split your display
        :param part: the part in which you want to render text (first part is 0, second is 1, etc.)
        :param offset: define some offset pixel to move strings a little bit (default=0)
        """

        x = int(((((SURFACE_WIDTH / parts) / 2) + ((SURFACE_WIDTH / parts) * part)) -
                 (self.size[0] / 2)) + (offset * ZOOM))

        self.draw_string(x)

    def draw_string(self, x):
        """
        takes x and y from the functions above and render the fonts
        """

        self.surf.blit(self.font.render(self.string, True, self.color), (x, self.y))


class DrawImage:
    def __init__(self, surf, image, y=None, size=None, fillcolor=None, angle=None, maintain_ratio=True):
        """
        :param image: image from the image_factory()
        :param y: the y-position of the image you want to render
        """
        self.image = image
        if y:
            self.y = int(y * ZOOM)

        self.img_size = self.image.size  # noqa
        # self.size = int(size * ZOOM)
        self.angle = angle
        self.surf = surf

        if angle:
            self.image = self.image.rotate(self.angle, resample=Image.BICUBIC)  # noqa

        if size:
            raw_width, raw_height = self.image.size
            width, height = size

            if maintain_ratio:
                if (raw_width / width) <= (raw_height / height):
                    # height is the limiting factor to resize the image
                    raw_width = round(height / raw_height * raw_width)
                    raw_height = height
                else:
                    raw_height = round(width / raw_width * raw_height)
                    raw_width = width
            else:
                raw_width = width
                raw_height = height
            # if raw_width >= raw_height:
            #     raw_width, raw_height = (self.size, int(self.size / raw_width * raw_height))
            # else:
            #     raw_width, raw_height = (int(self.size / raw_width * raw_height), self.size)

            new_image = self.image.resize((raw_width, raw_height), Image.LANCZOS if AA else Image.BILINEAR)  # noqa
            self.image = new_image
            self.img_size = new_image.size
        else:
            self.size = self.img_size

        self.fillcolor = fillcolor

        # self.image = pygame.image.fromstring(self.image.tobytes(), self.image.size, self.image.mode)
        self.image = pygame.image.frombytes(self.image.tobytes(), self.image.size, self.image.mode)

    @staticmethod
    def fill(surface, fillcolor: tuple):
        """converts the color on an mono colored icon"""
        surface.set_colorkey(BACKGROUND)
        w, h = surface.get_size()
        r, g, b = fillcolor
        for x in range(w):
            for y in range(h):
                a: int = surface.get_at((x, y))[3]
                # removes some distortion from scaling/zooming
                if a > 5:
                    color = pygame.Color(r, g, b, a)
                    surface.set_at((x, y), color)

    def left(self, offset=0):
        """
        :param offset: define some offset pixel to move image a little bit more left(default=0)
        """

        x = int(10 * ZOOM + (offset * ZOOM))

        self.draw_image(x)

    def right(self, offset=0):
        """
        :param offset: define some offset pixel to move image a little bit more right (default=0)
        """

        x = int((SURFACE_WIDTH - self.img_size[0] - 10 * ZOOM) - (offset * ZOOM))

        self.draw_image(x)

    def center(self, parts, part, offset=0):
        """
        :param parts: define in how many parts you want to split your display
        :param part: the part in which you want to render text (first part is 0, second is 1, etc.)
        :param offset: define some offset pixel to move strings a little bit (default=0)
        """

        x = int(((((SURFACE_WIDTH / parts) / 2) + ((SURFACE_WIDTH / parts) * part)) -
                 (self.img_size[0] / 2)) + (offset * ZOOM))

        self.draw_image(x)

    def draw_middle_position_icon(self):

        position_x = int((SURFACE_WIDTH - ((SURFACE_WIDTH / 3) / 2) - (self.image.get_rect()[2] / 2)))

        position_y = int((self.y - (self.image.get_rect()[3] / 2)))

        self.draw_image(draw_x=position_x, draw_y=position_y)

    def draw_position(self, pos: tuple):
        x, y = pos
        if y == 0:
            y += 1
        self.draw_image(draw_x=int(x * ZOOM), draw_y=int(y * ZOOM))

    def draw_absolut_position(self, pos: tuple):
        x, y = pos
        if y == 0:
            y += 1
        self.draw_image(draw_x=int(x), draw_y=int(y))

    def draw_image(self, draw_x, draw_y=None):
        """
        takes x from the functions above and the y from the class to render the image
        """

        if self.fillcolor:

            surface = self.image
            self.fill(surface, self.fillcolor)

            if draw_y:
                self.surf.blit(surface, (int(draw_x), int(draw_y)))
            else:
                self.surf.blit(surface, (int(draw_x), self.y))
        else:
            if draw_y:
                self.surf.blit(self.image, (int(draw_x), int(draw_y)))
            else:
                self.surf.blit(self.image, (int(draw_x), self.y))


class Update(object):

    @staticmethod
    def update_json():

        if PWM:
            brightness = get_brightness()
            os.system(f'gpio -g pwm {PWM} {brightness}') if PWM is not False else logger.info('not setting pwm')
            logger.info(f'set brightness: {brightness}, pwm configured: {PWM}')

        global THREADS, CONNECTION_ERROR, CONNECTION

        thread = threading.Timer(config["TIMER"]["UPDATE"], Update.update_json)

        thread.start()

        THREADS.append(thread)

        CONNECTION = pygame.time.get_ticks() + 1500  # 1.5 seconds

        try:
            standings_request_url = f'{SERVER}/standings/now'
            schedule_request_url = f'{SERVER}/club-schedule-season/{NHL_TEAM}/now'
            roster_request_url = f'{SERVER}/club-stats/{NHL_TEAM}/now'

            # current_endpoint = f'{SERVER}/current'
            # daily_endpoint = f'{SERVER}/forecast/daily'
            # stats_endpoint = f'{SERVER}/subscription/usage'
            # units = 'M' if METRIC else 'I'

            logger.info(f'connecting to server: {SERVER}')

            # options = str(f'&postal_code={WEATHERBIT_POSTALCODE}'
            #               f'&country={WEATHERBIT_COUNTRY}'
            #               f'&lang={WEATHERBIT_LANG}'
            #               f'&units={units}')

            # current_request_url = str(f'{current_endpoint}?key={WEATHERBIT_IO_KEY}{options}')
            # daily_request_url = str(f'{daily_endpoint}?key={WEATHERBIT_IO_KEY}{options}&days={WEATHERBIT_DAYS}')
            # stats_request_url = str(f'{stats_endpoint}?key={WEATHERBIT_IO_KEY}')

            # current_data = requests.get(current_request_url, headers=HEADERS).json()
            # daily_data = requests.get(daily_request_url, headers=HEADERS).json()
            # stats_data = requests.get(stats_request_url, headers=HEADERS).json()

            standings_data = Update.clean_standings_response(requests.get(standings_request_url,
                                                                          headers=HEADERS).json())
            schedule_data = Update.clean_schedule_response(requests.get(schedule_request_url, headers=HEADERS).json())
            roster_data = Update.clean_roster_response(requests.get(roster_request_url, headers=HEADERS).json())

            game_request_url = f'{SERVER}/gamecenter/{GAME_ID}/play-by-play'
            game_data = Update.clean_game_response(requests.get(game_request_url, headers=HEADERS).json())

            data = {
                'standings': standings_data,
                'schedule': schedule_data,
                'roster': roster_data,
                'game': game_data
            }

            with open(LOG_PATH / 'latest_hockey.json', 'w+') as outputfile:
                json.dump(data, outputfile, indent=2, sort_keys=True)  # noqa

            logger.info('json file saved')

            CONNECTION_ERROR = False

        except (requests.HTTPError, requests.ConnectionError) as update_ex:

            CONNECTION_ERROR = True

            logger.warning(f'Connection ERROR: {update_ex}')

        return

    @staticmethod
    def read_json():

        global THREADS, JSON_DATA, GAME_ID, REFRESH_ERROR, READING

        thread = threading.Timer(config["TIMER"]["RELOAD"], Update.read_json)

        thread.start()

        THREADS.append(thread)

        READING = pygame.time.get_ticks() + 1500  # 1.5 seconds

        try:

            data = open(LOG_PATH / 'latest_hockey.json').read()

            new_json_data = json.loads(data)

            logger.info('json file read by module')
            logger.info(f'{new_json_data}')

            JSON_DATA = new_json_data
            # ToDo: set GAME_ID here maybe
            REFRESH_ERROR = False

        except IOError as read_ex:

            REFRESH_ERROR = True

            logger.warning(f'ERROR - json file read by module: {read_ex}')

        Update.icon_path()

    @staticmethod
    def clean_standings_response(response):
        standings = { 'Central': {}, 'Pacific': {}, 'Atlantic': {}, 'Metropolitan': {}, 'Western': {}, 'Eastern': {}}

        for team in response['standings']:
            if len(standings[team['divisionName']]) < 3:
                standings[team['divisionName']][team['teamAbbrev']['default']] = {'gamesPlayed': team['gamesPlayed'],  # noqa
                                                                       'wins': team['wins'], 'losses': team['losses'],
                                                                       'otLosses': team['otLosses'],
                                                                       'points': team['points'],
                                                                       'pointPctg': team['pointPctg']}
            else:
                standings[team['conferenceName']][team['teamAbbrev']['default']] = {'gamesPlayed': team['gamesPlayed'],  # noqa
                                                                         'wins': team['wins'], 'losses': team['losses'],
                                                                         'otLosses': team['otLosses'],
                                                                         'points': team['points'],
                                                                         'pointPctg': team['pointPctg']}

        for conf in standings:
            if conf in ('Western', 'Eastern'):
                standings[conf] = dict(sorted(standings[conf].items(),
                                              key=lambda item: (-item[1]['points'], -item[1]['pointPctg'])))

        return standings

    @staticmethod
    def clean_schedule_response(response):
        global GAME_ID
        schedule = {'team': NHL_TEAM, 'games': []}
        for gm in response['games']:
            schedule['games'].append({'id': gm['id'],
                                      'startTimeUTC': gm['startTimeUTC'],
                                      'gameType': gm['gameType'],  # 1: preseason, 2: regular
                                      'gameState': gm['gameState'],  # FINAL, OFF, LIVE, FUT, PRE
                                      'awayTeam': gm['awayTeam']['abbrev'],
                                      'homeTeam': gm['homeTeam']['abbrev']})
            schedule['games'][-1]['awayScore'] = gm['awayTeam'].get('score', None)
            schedule['games'][-1]['homeScore'] = gm['homeTeam'].get('score', None)
            try:
                schedule['games'][-1]['gameOutcome'] = gm['gameOutcome'].get('lastPeriodType', None)  # REG, OT, SO
            except KeyError:
                schedule['games'][-1]['gameOutcome'] = None

        for ii, gm in enumerate(schedule['games']):
            if gm['gameState'] == 'FUT':
                if ii == 0:
                    show_game_ind = 0
                else:
                    show_game_ind = ii - 1
                break
        else:
            show_game_ind = -1

        GAME_ID = schedule['games'][show_game_ind]['id']

        return schedule

    @staticmethod
    def clean_roster_response(response):
        roster = {'team': NHL_TEAM, 'skaters': [],
                  'goalies': []}
        for sktr in response['skaters']:
            roster['skaters'].append({'playerId': sktr['playerId'],
                                      'headshot': sktr['headshot'],
                                      'firstName': sktr['firstName']['default'],
                                      'lastName': sktr['lastName']['default'],
                                      'positionCode': sktr['positionCode'],
                                      'gamesPlayed': sktr['gamesPlayed'],
                                      'goals': sktr['goals'],
                                      'assists': sktr['assists'],
                                      'points': sktr['points']})

        for glie in response['goalies']:
            roster['goalies'].append({'playerId': glie['playerId'],
                                      'headshot': glie['headshot'],
                                      'firstName': glie['firstName']['default'],
                                      'lastName': glie['lastName']['default'],
                                      'gamesPlayed': glie['gamesPlayed'],
                                      'gamesStarted': glie['gamesStarted'],
                                      'wins': glie['wins'],
                                      'losses': glie['losses'],
                                      'ties': glie['ties'],
                                      'overtimeLosses': glie['overtimeLosses'],
                                      'savePercentage': glie['savePercentage'],
                                      'goals': glie['goals'],
                                      'assists': glie['assists'],
                                      'points': glie['points']})

        return roster

    @staticmethod
    def clean_game_response(response):
        game = {}

        for key, rkeys in GAME_MAP.items():
            temp_resp = response
            for rk in rkeys[:-1]:
                if rk not in temp_resp:
                    game[key] = ''
                    break
                else:
                    temp_resp = temp_resp[rk]  # let temp_resp be the sub dict in response
            else:
                if rkeys[-1] not in temp_resp:
                    game[key] = ''
                else:
                    game[key] = temp_resp[rkeys[-1]]  # get the last value

        game['plays'] = []
        for play in response['plays']:
            try:
                if play['typeDescKey'] == 'goal':
                    game['plays'].append({'typeDescKey': 'goal', 'period': play['periodDescriptor']['number'],
                                          'timeInPeriod': play['timeInPeriod'],
                                          'scoringPlayerId': play['details']['scoringPlayerId']})

                    for plyr in response['rosterSpots']:
                        if plyr['playerId'] == game['plays'][-1]['scoringPlayerId']:  # noqa (pycharm bs)
                            game['plays'][-1]['scoringPlayerName'] = plyr['firstName']['default'] + ' ' + \
                                                                     plyr['lastName']['default']
                            break
                    else:
                        game['plays'][-1]['scoringPlayerName'] = ''
            except KeyError:
                logger.error('KeyError in League().get_game() plays')

        return game

    @staticmethod
    def icon_path():

        # global WEATHERICON, FORECASTICON_DAY_1, \
        #     FORECASTICON_DAY_2, FORECASTICON_DAY_3, PRECIPTYPE, PRECIPCOLOR, UPDATING
        global AWAY_LOGO, HOME_LOGO, UPDATING

        icon_extension = '.png'

        updated_list = []

        # icon = JSON_DATA['current']['data'][0]['weather']['icon']

        away_logo = str(JSON_DATA['game']['awayTeam']) + LOGO_SUFFIX
        home_logo = str(JSON_DATA['game']['homeTeam']) + LOGO_SUFFIX
        # forecast_icon_3 = JSON_DATA['daily']['data'][3]['weather']['icon']

        logos = (away_logo, home_logo)

        logger.debug(logos)

        logger.debug(f'validating path: {logos}')

        for icon in logos:
            full_icon = icon + icon_extension
            if os.path.isfile(LOGO_PATH / full_icon):

                logger.debug(f'TRUE : {icon}')

                updated_list.append(icon)

            else:

                logger.warning(f'FALSE : {icon}')

                updated_list.append('unknown')

        AWAY_LOGO = updated_list[0]
        HOME_LOGO = updated_list[1]
        # FORECASTICON_DAY_2 = updated_list[2]
        # FORECASTICON_DAY_3 = updated_list[3]

        global PATH_ERROR

        if any("unknown" in s for s in updated_list):

            PATH_ERROR = True

        else:

            PATH_ERROR = False

        logger.info(f'update path for icons: {updated_list}')

        # Update.get_precip_type()
        Update.create_surface()

    # @staticmethod
    # def get_precip_type():
    #
    #     global JSON_DATA, PRECIPCOLOR, PRECIPTYPE
    #
    #     pop = int(JSON_DATA['daily']['data'][0]['pop'])
    #     rain = float(JSON_DATA['daily']['data'][0]['precip'])
    #     snow = float(JSON_DATA['daily']['data'][0]['snow'])
    #
    #     if pop == 0:
    #
    #         PRECIPTYPE = config['LOCALE']['PRECIP_STR']
    #         PRECIPCOLOR = GREEN
    #
    #     else:
    #
    #         if pop > 0 and rain > snow:
    #
    #             PRECIPTYPE = config['LOCALE']['RAIN_STR']
    #             PRECIPCOLOR = BLUE
    #
    #         elif pop > 0 and snow > rain:
    #
    #             PRECIPTYPE = config['LOCALE']['SNOW_STR']
    #             PRECIPCOLOR = WHITE
    #
    #     logger.info(f'update PRECIPPOP to: {pop} %')
    #     logger.info(f'update PRECIPTYPE to: {PRECIPTYPE}')
    #     logger.info(f'update PRECIPCOLOR to: {PRECIPCOLOR}')
    #
    #     Update.create_surface()

    @staticmethod
    def create_surface():
        schedule = JSON_DATA['schedule']
        standings = JSON_DATA['standings']
        roster = JSON_DATA['roster']
        game_pbp = JSON_DATA['game']
        
        away_score = str(game_pbp['awayScore'])
        home_score = str(game_pbp['homeScore'])
        away_sog = str(game_pbp['awaySog'])
        home_sog = str(game_pbp['homeSog'])
        game_state = game_pbp['gameState']
        if game_pbp['period'] == 1:
            period = '1st'
        elif game_pbp['period'] == 2:
            period = '2nd'
        elif game_pbp['period'] == 3:
            period = '3rd'
        elif game_pbp['period'] == 4:
            period = 'OT'
        elif game_pbp['period'] == 5:
            period = 'SO'
        else:
            period = ' '
        period += ' Int' if game_pbp['inIntermission'] else ''
        game_clock = game_pbp['clock']
        away_strength = str(game_pbp['awayStrength'])
        home_strength = str(game_pbp['homeStrength'])
        away_situation = game_pbp['awaySituation']
        home_situation = game_pbp['homeSituation']
        situation_clock = game_pbp['situationClock']
        
        if away_situation:
            away_full_sit = away_strength + 'v' + home_strength + ' ' + ','.join(away_situation) + ' ' + situation_clock
        else:
            away_full_sit = ''
            
        if home_situation:
            home_full_sit = home_strength + 'v' + away_strength + ' ' + ','.join(home_situation) + ' ' + situation_clock
        else:
            home_full_sit = ''


        # current_forecast = JSON_DATA['current']['data'][0]
        # daily_forecast = JSON_DATA['daily']['data']
        # stats_data = JSON_DATA['stats']
        # 
        # summary_string = current_forecast['weather']['description']
        # temp_out = str(int(current_forecast['temp']))
        # temp_out_unit = '°C' if METRIC else '°F'
        # temp_out_string = str(temp_out + temp_out_unit)
        # precip = JSON_DATA['daily']['data'][0]['pop']
        # precip_string = str(f'{precip} %')
        # 
        # today = daily_forecast[0]
        # day_1 = daily_forecast[1]
        # day_2 = daily_forecast[2]
        # day_3 = daily_forecast[3]

        # df_forecast = theme["DATE_FORMAT"]["FORECAST_DAY"]
        # df_sun = theme["DATE_FORMAT"]["SUNRISE_SUNSET"]
        #
        # day_1_ts = time.mktime(time.strptime(day_1['datetime'], '%Y-%m-%d'))
        # day_1_ts = convert_timestamp(day_1_ts, df_forecast)
        # day_2_ts = time.mktime(time.strptime(day_2['datetime'], '%Y-%m-%d'))
        # day_2_ts = convert_timestamp(day_2_ts, df_forecast)
        # day_3_ts = time.mktime(time.strptime(day_3['datetime'], '%Y-%m-%d'))
        # day_3_ts = convert_timestamp(day_3_ts, df_forecast)
        #
        # day_1_min_max_temp = f"{int(day_1['low_temp'])} | {int(day_1['high_temp'])}"
        # day_2_min_max_temp = f"{int(day_2['low_temp'])} | {int(day_2['high_temp'])}"
        # day_3_min_max_temp = f"{int(day_3['low_temp'])} | {int(day_3['high_temp'])}"
        #
        # sunrise = convert_timestamp(today['sunrise_ts'], df_sun)
        # sunset = convert_timestamp(today['sunset_ts'], df_sun)
        #
        # wind_direction = str(current_forecast['wind_cdir'])
        # wind_speed = float(current_forecast['wind_spd'])
        # wind_speed = wind_speed * 3.6 if METRIC else wind_speed
        # wind_speed_unit = 'km/h' if METRIC else 'mph'
        # wind_speed_string = str(f'{round(wind_speed, 1)} {wind_speed_unit}')

        global hockey_surf, UPDATING

        new_surf = pygame.Surface((SURFACE_WIDTH, SURFACE_HEIGHT))
        new_surf.fill(BACKGROUND)

        DrawImage(new_surf, images['wifi'], 5, size=(15, 15), fillcolor=RED if CONNECTION_ERROR else GREEN).left()
        DrawImage(new_surf, images['refresh'], 5, size=(15, 15), fillcolor=RED if REFRESH_ERROR else GREEN).right(8)
        DrawImage(new_surf, images['path'], 5, size=(15, 15), fillcolor=RED if PATH_ERROR else GREEN).right(-5)

        # DrawImage(new_surf, images[WEATHERICON], 68, size=100).center(2, 0, offset=10)

        # if not ANIMATION:
        #     if PRECIPTYPE == config['LOCALE']['RAIN_STR']:
        #
        #         DrawImage(new_surf, images['preciprain'], size=20).draw_position(pos=(155, 140))
        #
        #     elif PRECIPTYPE == config['LOCALE']['SNOW_STR']:
        #
        #         DrawImage(new_surf, images['precipsnow'], size=20).draw_position(pos=(155, 140))

        DrawImage(new_surf, images[AWAY_LOGO], 40 + 10, size=(188, 125)).left()
        DrawImage(new_surf, images[HOME_LOGO], 40 + 2 * 10 + 125, size=(188, 125)).left()
        # DrawImage(new_surf, images[FORECASTICON_DAY_1], 200, size=50).center(3, 0)
        # DrawImage(new_surf, images[FORECASTICON_DAY_2], 200, size=50).center(3, 1)
        # DrawImage(new_surf, images[FORECASTICON_DAY_3], 200, size=50).center(3, 2)

        # DrawImage(new_surf, images['sunrise'], 260, size=25).left()
        # DrawImage(new_surf, images['sunset'], 290, size=25).left()

        # draw_wind_layer(new_surf, current_forecast['wind_dir'], 285)

        # draw_moon_layer(new_surf, int(255 * ZOOM), int(60 * ZOOM))

        # draw all the strings
        # if config["DISPLAY"]["SHOW_API_STATS"]:
        #     DrawString(new_surf, str(stats_data['calls_remaining']), FONT_SMALL_BOLD, BLUE, 20).right(offset=-5)

        DrawString(new_surf, away_score, FONT_SCORE, MAIN_FONT, 40 + 0).left(188 + 10)
        DrawString(new_surf, home_score, FONT_SCORE, MAIN_FONT, 40 + 1 * 10 + 125).left(188 + 10)

        # DrawString(new_surf, summary_string, FONT_SMALL_BOLD, VIOLET, 50).center(1, 0)
        #
        # DrawString(new_surf, temp_out_string, FONT_BIG, ORANGE, 75).right()
        #
        # DrawString(new_surf, precip_string, FONT_BIG, PRECIPCOLOR, 105).right()
        # DrawString(new_surf, PRECIPTYPE, FONT_SMALL_BOLD, PRECIPCOLOR, 140).right()
        #
        # DrawString(new_surf, day_1_ts, FONT_SMALL_BOLD, ORANGE, 165).center(3, 0)
        # DrawString(new_surf, day_2_ts, FONT_SMALL_BOLD, ORANGE, 165).center(3, 1)
        # DrawString(new_surf, day_3_ts, FONT_SMALL_BOLD, ORANGE, 165).center(3, 2)
        #
        # DrawString(new_surf, day_1_min_max_temp, FONT_SMALL_BOLD, MAIN_FONT, 180).center(3, 0)
        # DrawString(new_surf, day_2_min_max_temp, FONT_SMALL_BOLD, MAIN_FONT, 180).center(3, 1)
        # DrawString(new_surf, day_3_min_max_temp, FONT_SMALL_BOLD, MAIN_FONT, 180).center(3, 2)
        #
        # DrawString(new_surf, sunrise, FONT_SMALL_BOLD, MAIN_FONT, 265).left(30)
        # DrawString(new_surf, sunset, FONT_SMALL_BOLD, MAIN_FONT, 292).left(30)
        #
        # DrawString(new_surf, wind_direction, FONT_SMALL_BOLD, MAIN_FONT, 250).center(3, 2)
        # DrawString(new_surf, wind_speed_string, FONT_SMALL_BOLD, MAIN_FONT, 300).center(3, 2)

        hockey_surf = new_surf

        # logger.info(f'summary: {summary_string}')
        # logger.info(f'temp out: {temp_out_string}')
        # logger.info(f'{PRECIPTYPE}: {precip_string}')
        # logger.info(f'icon: {WEATHERICON}')
        # logger.info(f'forecast: '
        #             f'{day_1_ts} {day_1_min_max_temp} {FORECASTICON_DAY_1}; '
        #             f'{day_2_ts} {day_2_min_max_temp} {FORECASTICON_DAY_2}; '
        #             f'{day_3_ts} {day_3_min_max_temp} {FORECASTICON_DAY_3}')
        # logger.info(f'sunrise: {sunrise} ; sunset {sunset}')
        # logger.info(f'WindSpeed: {wind_speed_string}')

        # remove the ended timer and threads
        global THREADS
        THREADS = [t for t in THREADS if t.is_alive()]
        logging.info(f'threads cleaned: {len(THREADS)} left in the queue')

        pygame.time.delay(1500)
        UPDATING = pygame.time.get_ticks() + 1500  # 1.5 seconds

        return hockey_surf

    @staticmethod
    def run(first_run=False):
        if first_run:
            Update.read_json()
            Update.update_json()
        else:
            Update.update_json()
            Update.read_json()


def get_brightness():
    current_time = time.time()
    current_time = int(convert_timestamp(current_time, '%H'))

    return 25 if current_time >= 20 or current_time <= 5 else 100


def convert_timestamp(timestamp, param_string):
    """
    :param timestamp: takes a normal integer unix timestamp
    :param param_string: use the default convert timestamp to timestring options
    :return: a converted string from timestamp
    """
    timestring = str(datetime.datetime.fromtimestamp(int(timestamp)).astimezone().strftime(param_string))

    return timestring


# def draw_time_layer():
#     timestamp = time.time()
#
#     date_day_string = convert_timestamp(timestamp, theme["DATE_FORMAT"]["DATE"])
#     date_time_string = convert_timestamp(timestamp, theme["DATE_FORMAT"]["TIME"])
#
#     logger.debug(f'Day: {date_day_string}')
#     logger.debug(f'Time: {date_time_string}')
#
#     DrawString(time_surf, date_day_string, DATE_FONT, MAIN_FONT, 0).center(1, 0)
#     DrawString(time_surf, date_time_string, CLOCK_FONT, MAIN_FONT, 15).center(1, 0)


# def draw_moon_layer(surf, y, size):
#     # based on @miyaichi's fork -> great idea :)
#     _size = 1000
#     dt = datetime.datetime.fromtimestamp(JSON_DATA['daily']['data'][0]['ts'])
#     moon_age = (((dt.year - 11) % 19) * 11 + [0, 2, 0, 2, 2, 4, 5, 6, 7, 8, 9, 10][dt.month - 1] + dt.day) % 30
#
#     image = Image.new("RGBA", (_size + 2, _size + 2))
#     draw = ImageDraw.Draw(image)
#
#     radius = int(_size / 2)
#
#     # draw full moon
#     draw.ellipse([(1, 1), (_size, _size)], fill=WHITE)
#
#     # draw dark side of the moon
#     theta = moon_age / 14.765 * math.pi
#     sum_x = sum_length = 0
#
#     for _y in range(-radius, radius, 1):
#         alpha = math.acos(_y / radius)
#         x = radius * math.sin(alpha)
#         length = radius * math.cos(theta) * math.sin(alpha)
#
#         if moon_age < 15:
#             start = (radius - x, radius + _y)
#             end = (radius + length, radius + _y)
#         else:
#             start = (radius - length, radius + _y)
#             end = (radius + x, radius + _y)
#
#         draw.line((start, end), fill=DARK_GRAY)
#
#         sum_x += 2 * x
#         sum_length += end[0] - start[0]
#
#     logger.debug(f'moon phase age: {moon_age} percentage: {round(100 - (sum_length / sum_x) * 100, 1)}')
#
#     image = image.resize((size, size), Image.LANCZOS if AA else Image.BILINEAR)
#     image = pygame.image.fromstring(image.tobytes(), image.size, image.mode)
#
#     x = (SURFACE_WIDTH / 2) - (size / 2)
#
#     surf.blit(image, (x, y))


# def draw_wind_layer(surf, angle, y):
#     # center the wind direction icon and circle on surface
#     DrawImage(surf, images['circle'], y, size=30, fillcolor=WHITE).draw_middle_position_icon()
#     DrawImage(surf, images['arrow'], y, size=30, fillcolor=RED, angle=-angle).draw_middle_position_icon()
#
#     logger.debug(f'wind direction: {angle}')


def draw_statusbar():
    global CONNECTION, READING, UPDATING

    if CONNECTION:
        DrawImage(dynamic_surf, images['wifi'], 5, size=15, fillcolor=BLUE).left()  # noqa
        if pygame.time.get_ticks() >= CONNECTION:
            CONNECTION = None

    if UPDATING:
        DrawImage(dynamic_surf, images['refresh'], 5, size=15, fillcolor=BLUE).right(8)  # noqa
        if pygame.time.get_ticks() >= UPDATING:
            UPDATING = None

    if READING:
        DrawImage(dynamic_surf, images['path'], 5, size=15, fillcolor=BLUE).right(-5)  # noqa
        if pygame.time.get_ticks() >= READING:
            READING = None


def draw_fps():
    DrawString(dynamic_surf, str(int(clock.get_fps())), FONT_SMALL_BOLD, RED, 20).left()


# ToDo: make this useful for touch events
def draw_event(color=RED):

    pos = pygame.mouse.get_pos()

    size = 20
    radius = int(size / 2)
    new_pos = (int(pos[0] - FIT_SCREEN[0] - (radius * ZOOM)), int(pos[1] - FIT_SCREEN[1] - (radius * ZOOM)))
    DrawImage(mouse_surf, images['circle'], size=size, fillcolor=color).draw_absolut_position(new_pos)  # noqa


def create_scaled_surf(surf, aa=False):
    if aa:
        scaled_surf = pygame.transform.smoothscale(surf, (SURFACE_WIDTH, SURFACE_HEIGHT))
    else:
        scaled_surf = pygame.transform.scale(surf, (SURFACE_WIDTH, SURFACE_HEIGHT))

    return scaled_surf


def loop():
    Update.run(first_run=False)

    running = True

    while running:
        tft_surf.fill(BACKGROUND)

        # fill the actual main surface and blit the image/weather layer
        display_surf.fill(BACKGROUND)
        display_surf.blit(hockey_surf, (0, 0))

        # fill the dynamic layer, make it transparent and use draw functions that write to that surface
        dynamic_surf.fill(BACKGROUND)
        dynamic_surf.set_colorkey(BACKGROUND)

        # draw_statusbar()  !!! re-add

        # if SHOW_FPS:
        #     draw_fps()  !!! re-add

        # if ANIMATION:
        #     my_particles.move(dynamic_surf, my_particles_list)

        # finally take the dynamic surface and blit it to the main surface
        display_surf.blit(dynamic_surf, (0, 0))

        # # now do the same for the time layer so it did not interfere with the other layers
        # # fill the layer and make it transparent as well
        # time_surf.fill(BACKGROUND)
        # time_surf.set_colorkey(BACKGROUND)
        #
        # # draw the time to the main layer
        # draw_time_layer()
        # display_surf.blit(time_surf, (0, 0))

        # # draw the mouse events
        # mouse_surf.fill(BACKGROUND)
        # mouse_surf.set_colorkey(BACKGROUND)
        # draw_event(WHITE)

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                running = False

                quit_all()

            elif event.type == pygame.MOUSEBUTTONDOWN:

                if pygame.MOUSEBUTTONDOWN:
                    draw_event()

            elif event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:

                    running = False

                    quit_all()

                elif event.key == pygame.K_SPACE:
                    shot_time = convert_timestamp(time.time(), "%Y-%m-%d %H-%M-%S")
                    pygame.image.save(display_surf, f'screenshot-{shot_time}.png')
                    logger.info(f'Screenshot created at {shot_time}')

        # display_surf.blit(mouse_surf, (0, 0))

        # finally take the main surface and blit it to the tft surface
        tft_surf.blit(create_scaled_surf(display_surf, aa=AA), FIT_SCREEN)

        # update the display with all surfaces merged into the main one
        pygame.display.update()

        # do it as often as FPS configured (30 FPS recommend for particle simulation, 15 runs fine too, 60 is overkill)
        clock.tick(FPS)

    quit_all()


if __name__ == '__main__':
    try:

        # if ANIMATION:
        #     my_particles = Particles()
        #     my_particles_list = my_particles.create_particle_list()

        images = image_factory(LOGO_PATH)

        loop()

    except KeyboardInterrupt:

        quit_all()