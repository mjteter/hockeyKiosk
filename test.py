import datetime
import json
import locale
import logging
import math
import os
from pathlib import Path
import random
import sys
import threading
import time

import pygame
import pygame.gfxdraw
import requests
from PIL import Image  # , ImageDraw

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

THREADS = []

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

PRECIPTYPE = 'Snow'
PRECIPCOLOR = WHITE


class Particles(object):
    def __init__(self):
        self.size = int(20 * ZOOM)
        self.count = 20
        self.surf = pygame.Surface((self.size, self.size))

    def create_particle_list(self):

        particle_list = []

        for i in range(self.count):
            x = random.randrange(0, self.size)
            y = random.randrange(0, self.size)
            w = int(1 * ZOOM)
            h = random.randint(int(2 * ZOOM), int(3 * ZOOM))
            speed = random.choice([1, 2, 3])
            color = random.choice(COLOR_LIST)
            direct = random.choice([0, 0, 1])
            particle_list.append([x, y, w, h, speed, color, direct])
        return particle_list

    def move(self, surf, particle_list):
        # Process each snow flake in the list
        self.surf.fill(BACKGROUND)
        self.surf.set_colorkey(BACKGROUND)

        if not PRECIPTYPE == 'Precipitation':

            for i in range(len(particle_list)):

                particle = particle_list[i]
                x, y, w, h, speed, color, direct = particle

                # Draw the snow flake
                if PRECIPTYPE == 'Rain':
                    pygame.draw.rect(self.surf, color, (x, y, w, h), 0)
                else:
                    pygame.draw.rect(self.surf, PRECIPCOLOR, (x, y, 2, 2), 0)

                # Move the snow flake down one pixel
                particle_list[i][1] += speed if PRECIPTYPE == 'Rain' else 1
                if random.choice([True, False]):
                    if PRECIPTYPE == 'Snow':
                        particle_list[i][0] += 1 if direct else 0

                # If the snow flake has moved off the bottom of the screen
                if particle_list[i][1] > self.size:
                    # Reset it just above the top
                    y -= self.size
                    particle_list[i][1] = y
                    # Give it a new x position
                    x = random.randrange(0, self.size)
                    particle_list[i][0] = x

            surf.blit(self.surf, (int(155 * ZOOM), int(140 * ZOOM)))


class Update(object):

    # @staticmethod
    # def update_json():
    #
    #     if PWM:
    #         brightness = get_brightness()
    #         os.system(f'gpio -g pwm {PWM} {brightness}') if PWM is not False else logger.info('not setting pwm')
    #         logger.info(f'set brightness: {brightness}, pwm configured: {PWM}')
    #
    #     global THREADS, CONNECTION_ERROR, CONNECTION
    #
    #     thread = threading.Timer(config["TIMER"]["UPDATE"], Update.update_json)
    #
    #     thread.start()
    #
    #     THREADS.append(thread)
    #
    #     CONNECTION = pygame.time.get_ticks() + 1500  # 1.5 seconds
    #
    #     try:
    #         standings_request_url = f'{SERVER}/standings/now'
    #         schedule_request_url = f'{SERVER}/club-schedule-season/{NHL_TEAM}/now'
    #         roster_request_url = f'{SERVER}/club-stats/{NHL_TEAM}/now'
    #
    #         # current_endpoint = f'{SERVER}/current'
    #         # daily_endpoint = f'{SERVER}/forecast/daily'
    #         # stats_endpoint = f'{SERVER}/subscription/usage'
    #         # units = 'M' if METRIC else 'I'
    #
    #         logger.info(f'connecting to server: {SERVER}')
    #
    #         # options = str(f'&postal_code={WEATHERBIT_POSTALCODE}'
    #         #               f'&country={WEATHERBIT_COUNTRY}'
    #         #               f'&lang={WEATHERBIT_LANG}'
    #         #               f'&units={units}')
    #
    #         # current_request_url = str(f'{current_endpoint}?key={WEATHERBIT_IO_KEY}{options}')
    #         # daily_request_url = str(f'{daily_endpoint}?key={WEATHERBIT_IO_KEY}{options}&days={WEATHERBIT_DAYS}')
    #         # stats_request_url = str(f'{stats_endpoint}?key={WEATHERBIT_IO_KEY}')
    #
    #         # current_data = requests.get(current_request_url, headers=HEADERS).json()
    #         # daily_data = requests.get(daily_request_url, headers=HEADERS).json()
    #         # stats_data = requests.get(stats_request_url, headers=HEADERS).json()
    #
    #         standings_data = Update.clean_standings_response(requests.get(standings_request_url,
    #                                                                       headers=HEADERS).json())
    #         schedule_data = Update.clean_schedule_response(requests.get(schedule_request_url, headers=HEADERS).json())
    #         roster_data = Update.clean_roster_response(requests.get(roster_request_url, headers=HEADERS).json())
    #
    #         game_request_url = f'{SERVER}/gamecenter/{GAME_ID}/play-by-play'
    #         game_data = Update.clean_game_response(requests.get(game_request_url, headers=HEADERS).json())
    #
    #         data = {
    #             'standings': standings_data,
    #             'schedule': schedule_data,
    #             'roster': roster_data,
    #             'game': game_data
    #         }
    #
    #         with open(LOG_PATH / 'latest_hockey.json', 'w+') as outputfile:
    #             json.dump(data, outputfile, indent=2, sort_keys=True)  # noqa
    #
    #         logger.info('json file saved')
    #
    #         CONNECTION_ERROR = False
    #
    #     except (requests.HTTPError, requests.ConnectionError) as update_ex:
    #
    #         CONNECTION_ERROR = True
    #
    #         logger.warning(f'Connection ERROR: {update_ex}')
    #
    #     return

    @staticmethod
    def read_json():

        global THREADS, JSON_DATA, GAME_ID, REFRESH_ERROR, READING

        thread = threading.Timer(config["TIMER"]["RELOAD"], Update.read_json)

        thread.start()

        THREADS.append(thread)

        READING = pygame.time.get_ticks() + 1500  # 1.5 seconds

        # try:
        #
        #     data = open(LOG_PATH / 'latest_hockey.json').read()
        #
        #     new_json_data = json.loads(data)
        #
        #     logger.info('json file read by module')
        #     logger.info(f'{new_json_data}')
        #
        #     JSON_DATA = new_json_data
        #     # ToDo: set GAME_ID here maybe
        #     REFRESH_ERROR = False
        #
        # except IOError as read_ex:
        #
        #     REFRESH_ERROR = True
        #
        #     logger.warning(f'ERROR - json file read by module: {read_ex}')

        Update.icon_path()


    @staticmethod
    def icon_path():

        # # global WEATHERICON, FORECASTICON_DAY_1, \
        # #     FORECASTICON_DAY_2, FORECASTICON_DAY_3, PRECIPTYPE, PRECIPCOLOR, UPDATING
        # global AWAY_LOGO, HOME_LOGO, UPDATING
        #
        # icon_extension = '.png'
        #
        # updated_list = []
        #
        # # icon = JSON_DATA['current']['data'][0]['weather']['icon']
        #
        # away_logo = str(JSON_DATA['game']['awayTeam']) + LOGO_SUFFIX
        # home_logo = str(JSON_DATA['game']['homeTeam']) + LOGO_SUFFIX
        # # forecast_icon_3 = JSON_DATA['daily']['data'][3]['weather']['icon']
        #
        # logos = (away_logo, home_logo)
        #
        # logger.debug(logos)
        #
        # logger.debug(f'validating path: {logos}')
        #
        # for icon in logos:
        #     full_icon = icon + icon_extension
        #     if os.path.isfile(LOGO_PATH / full_icon):
        #
        #         logger.debug(f'TRUE : {icon}')
        #
        #         updated_list.append(icon)
        #
        #     else:
        #
        #         logger.warning(f'FALSE : {icon}')
        #
        #         updated_list.append('unknown')
        #
        # AWAY_LOGO = updated_list[0]
        # HOME_LOGO = updated_list[1]
        # # FORECASTICON_DAY_2 = updated_list[2]
        # # FORECASTICON_DAY_3 = updated_list[3]
        #
        # global PATH_ERROR
        #
        # if any("unknown" in s for s in updated_list):
        #
        #     PATH_ERROR = True
        #
        # else:
        #
        #     PATH_ERROR = False
        #
        # logger.info(f'update path for icons: {updated_list}')

        Update.get_precip_type()
        # Update.create_surface()

    @staticmethod
    def get_precip_type():

        global JSON_DATA, PRECIPCOLOR, PRECIPTYPE

        pop = 1
        rain = 2
        snow = 1

        if pop == 0:

            PRECIPTYPE = 'Precipitation'
            PRECIPCOLOR = GREEN

        else:

            if pop > 0 and rain > snow:

                PRECIPTYPE = 'Rain'
                PRECIPCOLOR = BLUE

            elif pop > 0 and snow > rain:

                PRECIPTYPE = 'Snow'
                PRECIPCOLOR = WHITE

        logger.info(f'update PRECIPPOP to: {pop} %')
        logger.info(f'update PRECIPTYPE to: {PRECIPTYPE}')
        logger.info(f'update PRECIPCOLOR to: {PRECIPCOLOR}')

        Update.create_surface()

    @staticmethod
    def create_surface():
        # schedule = JSON_DATA['schedule']
        # standings = JSON_DATA['standings']
        # roster = JSON_DATA['roster']
        # game_pbp = JSON_DATA['game']
        #
        # away_score = str(game_pbp['awayScore'])
        # home_score = str(game_pbp['homeScore'])
        # away_sog = str(game_pbp['awaySog'])
        # home_sog = str(game_pbp['homeSog'])
        # game_state = game_pbp['gameState']
        # if game_pbp['period'] == 1:
        #     period = '1st'
        # elif game_pbp['period'] == 2:
        #     period = '2nd'
        # elif game_pbp['period'] == 3:
        #     period = '3rd'
        # elif game_pbp['period'] == 4:
        #     period = 'OT'
        # elif game_pbp['period'] == 5:
        #     period = 'SO'
        # else:
        #     period = ' '
        # period += ' Int' if game_pbp['inIntermission'] else ''
        # game_clock = game_pbp['clock']
        # away_strength = str(game_pbp['awayStrength'])
        # home_strength = str(game_pbp['homeStrength'])
        # away_situation = game_pbp['awaySituation']
        # home_situation = game_pbp['homeSituation']
        # situation_clock = game_pbp['situationClock']
        #
        # if away_situation:
        #     away_full_sit = away_strength + 'v' + home_strength + ' ' + ','.join(away_situation) + ' ' + situation_clock
        # else:
        #     away_full_sit = ''
        #
        # if home_situation:
        #     home_full_sit = home_strength + 'v' + away_strength + ' ' + ','.join(home_situation) + ' ' + situation_clock
        # else:
        #     home_full_sit = ''

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

        # DrawImage(new_surf, images['wifi'], 5, size=(15, 15), fillcolor=RED if CONNECTION_ERROR else GREEN).left()
        # DrawImage(new_surf, images['refresh'], 5, size=(15, 15), fillcolor=RED if REFRESH_ERROR else GREEN).right(8)
        # DrawImage(new_surf, images['path'], 5, size=(15, 15), fillcolor=RED if PATH_ERROR else GREEN).right(-5)

        # DrawImage(new_surf, images[WEATHERICON], 68, size=100).center(2, 0, offset=10)

        # if not ANIMATION:
        #     if PRECIPTYPE == config['LOCALE']['RAIN_STR']:
        #
        #         DrawImage(new_surf, images['preciprain'], size=20).draw_position(pos=(155, 140))
        #
        #     elif PRECIPTYPE == config['LOCALE']['SNOW_STR']:
        #
        #         DrawImage(new_surf, images['precipsnow'], size=20).draw_position(pos=(155, 140))

        # DrawImage(new_surf, images[AWAY_LOGO], 40 + 10, size=(188, 125)).left()
        # DrawImage(new_surf, images[HOME_LOGO], 40 + 2 * 10 + 125, size=(188, 125)).left()
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

        # DrawString(new_surf, away_score, FONT_SCORE, MAIN_FONT, 40 + 0).left(188 + 10)
        # DrawString(new_surf, home_score, FONT_SCORE, MAIN_FONT, 40 + 1 * 10 + 125).left(188 + 10)

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
            # Update.update_json()
        else:
            # Update.update_json()
            Update.read_json()

def create_scaled_surf(surf, aa=False):
    if aa:
        scaled_surf = pygame.transform.smoothscale(surf, (SURFACE_WIDTH, SURFACE_HEIGHT))
    else:
        scaled_surf = pygame.transform.scale(surf, (SURFACE_WIDTH, SURFACE_HEIGHT))

    return scaled_surf


def loop():
    # Update.run(first_run=False)

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

        if ANIMATION:
            my_particles.move(dynamic_surf, my_particles_list)

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

            # elif event.type == pygame.MOUSEBUTTONDOWN:
            #
            #     if pygame.MOUSEBUTTONDOWN:
            #         draw_event()

            elif event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:

                    running = False

                    quit_all()

                # elif event.key == pygame.K_SPACE:
                #     shot_time = convert_timestamp(time.time(), "%Y-%m-%d %H-%M-%S")
                #     pygame.image.save(display_surf, f'screenshot-{shot_time}.png')
                #     logger.info(f'Screenshot created at {shot_time}')

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

        if ANIMATION:
            my_particles = Particles()
            my_particles_list = my_particles.create_particle_list()

        # images = image_factory(LOGO_PATH)

        loop()

    except KeyboardInterrupt:

        quit_all()