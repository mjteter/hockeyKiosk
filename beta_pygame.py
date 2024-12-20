# import os
# from time import sleep
from typing import Tuple, Dict, List
import sys

import pygame
from pygame.locals import *  # for key coordinates

# import pygame_menu


# Constants and global variables
# ABOUT = [f'pygame-menu {pygame_menu.__version__}',
#          f'Author: {pygame_menu.__author__}',
#          '',
#          f'Email: {pygame_menu.__email__}']

PATH = sys.path[0] + '/'
LOGO_PATH = PATH + '/resources/logos/'
FONT_PATH = PATH + '/resources/fonts/'

BACKGROUNDS = {'dark': {'gray': [(0, 0, 3, 255),
                                 (15, 15, 18, 255),
                                 (30, 30, 33, 255),
                                 (45, 45, 48, 255),
                                 (60, 60, 63, 255),
                                 (75, 75, 78, 255),
                                 (90, 90, 93, 255)],
                        'blue': [(0, 7, 84, 255),
                                 (0, 9, 119, 255),
                                 (0, 14, 173, 255)]},
               'light': {'gray': [(255, 255, 255, 255),
                                  (240, 240, 243, 255),
                                  (225, 225, 228, 255),
                                  (210, 210, 213, 255),
                                  (195, 195, 198, 255),
                                  (180, 180, 183, 255),
                                  (165, 165, 168, 255),
                                  (150, 150, 153, 255),
                                  (135, 135, 138, 255)]}
               }

# BORDERS = {'light': {'gray': [[180, 180, 183],
#                               [195, 195, 198],
#                               [210, 210, 213],
#                               [225, 225, 228],
#                               [240, 240, 243],
#                               [255, 255, 255]]}}

# COLOR_BACKGROUND_ID = ['dark', 'gray', 1]
# COLOR_BACKGROUND = BACKGROUNDS[COLOR_BACKGROUND_ID[0]][COLOR_BACKGROUND_ID[1]][COLOR_BACKGROUND_ID[2]]
#
# COLOR_BORDER_ID = ['light', 'gray', 5]
# COLOR_BORDER = BACKGROUNDS[COLOR_BORDER_ID[0]][COLOR_BORDER_ID[1]][COLOR_BORDER_ID[2]]
#
# COLOR_TAB_TEXT_ACTIVE_ID = ['light', 'gray', 4]
# COLOR_TAB_TEXT_ACTIVE = BACKGROUNDS[COLOR_TAB_TEXT_ACTIVE_ID[0]][COLOR_TAB_TEXT_ACTIVE_ID[1]][COLOR_TAB_TEXT_ACTIVE_ID[2]]
#
# COLOR_TAB_TEXT_INACTIVE_ID = ['light', 'gray', 8]
# COLOR_TAB_TEXT_INACTIVE = BACKGROUNDS[COLOR_TAB_TEXT_INACTIVE_ID[0]][COLOR_TAB_TEXT_INACTIVE_ID[1]][COLOR_TAB_TEXT_INACTIVE_ID[2]]

COLOR_BACKGROUND = (15, 15, 18, 255)
COLOR_BORDER = (180, 180, 183, 255)
COLOR_MAIN_FONT = (195, 195, 198, 255)
COLOR_TAB_TEXT_ACTIVE = (195, 195, 198, 255)
COLOR_TAB_TEXT_INACTIVE = (135, 135, 138, 255)
COLOR_SELECTED = (204, 120, 50, 255)

COLOR_EMPTY = (0, 0, 0, 0)
COLOR_BLACK = (0, 0, 0, 255)
COLOR_DARK_GRAY = (66, 66, 66, 255)
COLOR_WHITE = (255, 255, 255, 255)
COLOR_RED = (214, 74, 75, 255)
COLOR_GREEN = (106, 135, 89, 255)
COLOR_BLUE = (52, 152, 219, 255)
COLOR_YELLOW = (187, 181, 41, 255)
COLOR_ORANGE = (204, 120, 50, 255)
COLOR_VIOLET = (152, 118, 170)

FPS = 20
W_SIZE = 480  # Width of window size
H_SIZE = 320  # Height of window size
TOP_MENU_H_SIZE = 40  # height of tabs at top
WINDOW_SIZE = (W_SIZE, H_SIZE)
# HELP = ['Press ESC to enable/disable Menu',
#         'Press ENTER to access a Sub-Menu or use an option',
#         'Press UP/DOWN to move through Menu',
#         'Press LEFT/RIGHT to move through Selectors']


def pyg_draw_rect_multi_border(surface: pygame.Surface,
                               color: Tuple[int, int, int, int],
                               left_top: Tuple[int, int],
                               size: Tuple[int, int],
                               width: Tuple[int, int, int, int]) -> None:
    left = left_top[0]
    top = left_top[1]
    wid = size[0] - 1
    hgt = size[1] - 1
    pygame.Rect()
    # left border
    for ii in range(width[0]):
        pygame.draw.line(surface, color, (left + ii, top), (left + ii, top + hgt), 1)

    # top border
    for ii in range(width[1]):
        pygame.draw.line(surface, color, (left, top + ii), (left + wid, top + ii), 1)

    # right border
    for ii in range(width[2]):
        pygame.draw.line(surface, color, (left + wid - ii, top), (left + wid - ii, top + hgt), 1)

    # bottom border
    for ii in range(width[3]):
        pygame.draw.line(surface, color, (left, top + hgt - ii), (left + wid, top + hgt - ii), 1)
    return


def multi_uniform_text_fill(text_rect_list: List, font_path: str = FONT_PATH + 'JetBrainsMono-Medium.ttf',
                            color: Tuple[int, int, int, int] = COLOR_MAIN_FONT):
    """
    Takes list of ['text', pygame.Rect, loc] couplets and finds the maximum font size that works across all entries
    loc is representation of where text should be located in Rect (tl, tc, tr, ml, mc, mr, bl, bc, br)
    :param text_rect_list:
    :param font_path:
    :param color:
    :return:
    """

    text_fits = False
    font_size = 200
    font_rect_list = []

    while not text_fits:
        font = pygame.font.Font(font_path, font_size)
        font_rect_list = []
        # print(font_size)
        text_fits = True
        for (text, rect, loc) in text_rect_list:
            test_text = font.render(text, True, color)
            font_rect_list.append([test_text, rect, loc])
            width = test_text.get_rect().width
            height = test_text.get_rect().height
            # print(width, rect.width, height, rect.height)
            # print(font.size(text), font.get_height())
            if height > rect.height or width > rect.width:
                text_fits = False

        if not text_fits:
            if font_size > 50:
                font_size -= 10
            elif font_size > 16:
                font_size -= 2
            else:
                font_size -= 1

    return font_rect_list


def render_font_rect_list(surface: pygame.Surface, font_rect_list: List):
    """
    Renders all given text
    :param surface:
    :param font_rect_list:
    :return:
    """

    for (text, rect, loc) in font_rect_list:
        if loc == 'tl':  # top left
            surface.blit(text, text.get_rect(topleft=rect.topleft))
        elif loc == 'tc':  # top center
            surface.blit(text, text.get_rect(midtop=rect.midtop))
        elif loc == 'tr':  # top right
            surface.blit(text, text.get_rect(topright=rect.topright))
        elif loc == 'ml':  # mid left
            surface.blit(text, text.get_rect(midleft=rect.midleft))
        elif loc == 'mr':  # mid right
            surface.blit(text, text.get_rect(midright=rect.midright))
        elif loc == 'bl':  # bottom left
            surface.blit(text, text.get_rect(bottomleft=rect.bottomleft))
        elif loc == 'bc':  # bottom center
            surface.blit(text, text.get_rect(midbottom=rect.midbottom))
        elif loc == 'br':  # bottom right
            surface.blit(text, text.get_rect(bottomright=rect.bottomright))
        else:  # center
            surface.blit(text, text.get_rect(center=rect.center))

    return


class Logo(pygame.sprite.Sprite):
    def __init__(self, filepath: str, left_top: Tuple[int, int] = (0, 0), size: Tuple[int, int] = (170, 118)):
        super().__init__()

        raw_logo = pygame.image.load(filepath)
        pixel_rect = raw_logo.get_bounding_rect()  # sometimes pygame adds empty borders
        pixel_surf = pygame.Surface(pixel_rect.size).convert_alpha()
        pixel_surf.fill(COLOR_EMPTY)  # make sure background is transparent
        pixel_surf.blit(raw_logo, (0, 0), pixel_rect)

        cleaned_size = pixel_surf.get_size()

        if (cleaned_size[0] / cleaned_size[1]) <= (size[0] / size[1]):
            w1 = round(size[1] / cleaned_size[1] * cleaned_size[0])
            h1 = size[1]
        else:
            w1 = size[0]
            h1 = round(size[0] / cleaned_size[0] * cleaned_size[1])

        pixel_surf = pygame.transform.scale(pixel_surf, (w1, h1))

        self.rect = pygame.Rect(left_top, size)
        self.surf = pygame.Surface(self.rect.size).convert_alpha()
        self.surf.fill(COLOR_EMPTY)  # make sure background is transparent
        self.surf.blit(pixel_surf, pixel_surf.get_rect(center=self.surf.get_rect().center))

        # self.rect = self.surf.get_rect()


class MultiPageBasePage(pygame.sprite.Sprite):
    def __init__(self, height: int):
        super().__init__()

        self.surf = pygame.Surface((W_SIZE, height)).convert_alpha()
        self.surf.fill(COLOR_EMPTY)

        self.rect = self.surf.get_rect()
        self.rect.move_ip(0, H_SIZE - height)


class LiveGame(MultiPageBasePage):
    def __init__(self, game_dict: Dict, height: int):
        super().__init__(height)

        # self.font_path = FONT_PATH + 'JetBrainsMono-Medium.ttf'
        self.font_path = FONT_PATH + 'Roboto-Medium.ttf'

        logo_width_rat = 0.35417
        score_width_rat = 0.27083
        font_large_rat = 0.109375
        font_small_rat = 0.0625

        self.border_narrow = 5
        self.border_medium = 10
        self.border = 15

        self.logo_width = round(logo_width_rat * W_SIZE)
        self.logo_height = round((height - 3 * self.border) / 2)

        self.score_width = round(score_width_rat * W_SIZE)
        self.score_height = self.logo_height - 2 * self.border_narrow

        self.data_width = W_SIZE - self.logo_width - self.score_width - 4 * self.border
        self.font_large_height = round(font_large_rat * H_SIZE)
        self.font_small_height = round(font_small_rat * H_SIZE)

        self.away_team = game_dict['awayTeam']
        self.home_team = game_dict['homeTeam']
        self.away_score = str(game_dict['awayScore'])
        self.home_score = str(game_dict['homeScore'])
        self.away_sog = str(game_dict['awaySog'])
        self.home_sog = str(game_dict['homeSog'])
        self.game_state = game_dict['gameState']
        if game_dict['period'] == 1:
            self.period = '1st'
        elif game_dict['period'] == 2:
            self.period = '2nd'
        elif game_dict['period'] == 3:
            self.period = '3rd'
        elif game_dict['period'] == 4:
            self.period = 'OT'
        elif game_dict['period'] == 5:
            self.period = 'SO'
        self.period = self.period + (' Int' if game_dict['inIntermission'] else '')
        self.game_clock = game_dict['clock']
        self.away_situation = game_dict['awaySituation']
        self.home_situation = game_dict['homeSituation']

        away_logo = Logo('resources/logos/' + self.away_team + '_dark.svg',
                         left_top=(self.border, self.border), size=(self.logo_width, self.logo_height))
        home_logo = Logo('resources/logos/' + self.home_team + '_dark.svg',
                         left_top=(self.border, 2 * self.border + self.logo_height),
                         size=(self.logo_width, self.logo_height))

        # away_score_rect = pygame.Rect((2 * self.border + self.logo_width, self.border + self.border_narrow),
        #                               (self.score_width, self.score_height))
        # home_score_rect = pygame.Rect((2 * self.border + self.logo_width,
        #                                2 * self.border + 3 * self.border_narrow + self.score_height),
        #                               (self.score_width, self.score_height))

        away_score_rect = pygame.Rect((away_logo.rect.right + self.border, 0),
                                      (self.score_width, round(height / 2)))
        home_score_rect = pygame.Rect((home_logo.rect.right + self.border,
                                       round(height / 2)),
                                      (self.score_width, round(height / 2)))
        score_render_list = multi_uniform_text_fill([[self.away_score, away_score_rect, 'mc'],
                                                    [self.home_score, home_score_rect, 'mc']],
                                                   font_path=self.font_path, color=COLOR_MAIN_FONT)

        away_sog_rect = pygame.Rect((away_score_rect.right + self.border,
                                     self.border + self.border_narrow), (self.data_width, self.font_large_height))
        home_sog_rect = pygame.Rect((home_score_rect.right + self.border,
                                     height - self.border - self.border_narrow - self.font_large_height),
                                    (self.data_width, self.font_large_height))
        period_rect = pygame.Rect((away_score_rect.right + self.border,
                                   round(height / 2) - self.font_large_height),
                                  (self.data_width, self.font_large_height))
        clock_rect = pygame.Rect((home_score_rect.right + self.border,
                                  round(height / 2)),
                                 (self.data_width, self.font_large_height))
        sog_render_list = multi_uniform_text_fill([[self.away_sog, away_sog_rect, 'tl'],
                                                   [self.home_sog, home_sog_rect, 'bl'],
                                                   [self.period, period_rect, 'bl'],
                                                   [self.game_clock, clock_rect, 'tl']],
                                                  font_path=self.font_path, color=COLOR_MAIN_FONT)

        away_pp_rect = pygame.Rect((away_score_rect.right + self.border,
                                    away_sog_rect.bottom + self.border_narrow),
                                   (self.data_width, self.font_small_height))
        home_pp_rect = pygame.Rect((home_score_rect.right + self.border,
                                    home_sog_rect.top - self.border_narrow - self.font_small_height),
                                   (self.data_width, self.font_small_height))
        pp_rect_list = multi_uniform_text_fill([[self.away_situation, away_pp_rect, 'tl'],
                                                [self.home_situation, home_pp_rect, 'bl']],
                                               font_path=self.font_path, color=COLOR_MAIN_FONT)

        render_font_rect_list(self.surf, score_render_list + sog_render_list + pp_rect_list)

        # for (text, rect, loc) in (score_render_list + sog_render_list + pp_rect_list):
        #     pygame.draw.rect(self.surf, COLOR_GREEN, rect, 1)

        self.surf.blit(away_logo.surf, away_logo.rect)
        self.surf.blit(home_logo.surf, home_logo.rect)
        return


class Schedule(MultiPageBasePage):
    def __init__(self, height):
        super().__init__(height)


class Standings(MultiPageBasePage):
    def __init__(self, height):
        super().__init__(height)


class Settings(MultiPageBasePage):
    def __init__(self, height):
        super().__init__(height)


class MultiPage(pygame.sprite.Sprite):
    def __init__(self, height: int, tabs: Tuple):
        super().__init__()

        # set active tab
        self.active_tab = 0  # this is shown tab
        self.selected = 1  # this is button focus
        self.total_tabs = len(tabs)

        padding = 3
        border_width = 1
        self.tab_padded_height = height - border_width - 2 * padding
        self.tab_total_padded_width = W_SIZE - 1 - border_width * (self.total_tabs - 1) - 2 * padding * self.total_tabs

        # make surface which is assumed to cover full screen.  this will be transparent
        self.surf = pygame.Surface((W_SIZE, H_SIZE)).convert_alpha()
        self.surf.fill(COLOR_EMPTY)
        self.rect = self.surf.get_rect()

        # make top tab bar
        self.menu_surf = pygame.Surface((W_SIZE, height)).convert_alpha()
        self.menu_surf.fill(COLOR_EMPTY)

        pygame.draw.line(self.menu_surf, COLOR_BORDER, (0, height - 1), (W_SIZE, height - 1))

        self.menu_rect = self.menu_surf.get_rect()

        # determine what the correct font size should be
        menu_text_fits = False
        self.menu_font_size = 50
        tab_widths = [10 for ii in range(self.total_tabs)]

        while not menu_text_fits:
            self.menu_font = pygame.font.Font(FONT_PATH + 'JetBrainsMono-Medium.ttf', self.menu_font_size)
            tab_widths = []
            tab_height = 0
            total_width = 0
            for ii in range(self.total_tabs):
                test_font = self.menu_font.render(tabs[ii][0], True, COLOR_TAB_TEXT_ACTIVE)
                tab_widths.append(test_font.get_rect().width)
                tab_height = test_font.get_rect().height
                total_width += test_font.get_rect().width

            if tab_height > self.tab_padded_height or total_width > self.tab_total_padded_width:
                if self.menu_font_size > 50:
                    self.menu_font_size -= 10
                elif self.menu_font_size > 16:
                    self.menu_font_size -= 2
                else:
                    self.menu_font_size -= 1
            # elif self.menu_font_size < 6:
            #     menu_text_fits = True  # bug out on failure to find reasonable font size
            else:
                menu_text_fits = True
                # print(tab_widths)
                ii = 0
                while total_width < self.tab_total_padded_width:
                    tab_widths[ii] += 1
                    total_width += 1
                    if ii == self.total_tabs - 1:
                        ii = 0
                    else:
                        ii += 1
                # print(tab_widths)

        tab_rects = []
        border_lines = []
        tab_left = 0
        for ii in range(self.total_tabs):
            tab_top = 0
            tab_width = tab_widths[ii] + 2 * padding
            tab_height = height - border_width
            if ii == 0:  # first tab
                tab_left = 0
            # elif ii == self.total_tabs - 1:  # last tab
            #     pass
            else:  #middle tabs
                tab_left = tab_left + tab_widths[ii - 1] + 2 * padding + border_width
                border_lines.append(((tab_left - 1, 0), (tab_left - 1, tab_height)))
                pygame.draw.line(self.menu_surf, COLOR_BORDER, border_lines[-1][0], border_lines[-1][1], border_width)
            tab_rects.append(pygame.Rect((tab_left, tab_top), (tab_width, tab_height)))

        self.menu_font_bold = pygame.font.Font(FONT_PATH + 'JetBrainsMono-ExtraBold.ttf', self.menu_font_size)
        # print(tab_rects)
        for ii, (page_title, page) in enumerate(tabs):
            if self.active_tab == ii:  # if active
                page_text = self.menu_font.render(page_title, True, COLOR_TAB_TEXT_ACTIVE)

                self.surf.blit(page.surf, page.rect)  # blit active page
            else:  # not active
                page_text = self.menu_font.render(page_title, True, COLOR_TAB_TEXT_INACTIVE)

            if self.selected == ii:  # if selected
                pygame.draw.rect(self.menu_surf, COLOR_SELECTED, tab_rects[ii], 2)

            self.menu_surf.blit(page_text, page_text.get_rect(center=tab_rects[ii].center))

        # pygame.draw.rect(self.menu_surf, COLOR_ORANGE, tab_rects[0], 2)
        # pyg_draw_rect_multi_border(self.menu_surf, COLOR_TAB_TEXT_ACTIVE, tab_rects[0].topleft, tab_rects[0].size, (2, 2, 1, 1))

        self.surf.blit(self.menu_surf, self.menu_rect)



def main() -> None:
    """
    Main program.
    """

    pygame.init()
    clock = pygame.time.Clock()

    surface = pygame.display.set_mode(WINDOW_SIZE, pygame.NOFRAME)
    pygame.Surface.convert_alpha(surface)

    test_game = {'id': '2024020449', 'awayTeam': 'DET', 'homeTeam': 'PHI', 'awayScore': 1, 'homeScore': 3,
                 'awaySog': 17, 'homeSog': 25, 'gameState': 'LIVE', 'period': 2, 'clock': '02:18',
                 'homeSituation': '5v4', 'awaySituation': '', 'inIntermission': False, 'plays': []}

    live_game = LiveGame(test_game, H_SIZE - TOP_MENU_H_SIZE)
    schedule = Schedule(H_SIZE - TOP_MENU_H_SIZE)
    standings = Standings(H_SIZE - TOP_MENU_H_SIZE)
    settings = Settings(H_SIZE - TOP_MENU_H_SIZE)

    page_dict = (('Live Game', live_game),
                 ('Schedule', schedule),
                 ('Standings', standings),
                 ('Settings', settings))
    multi_page = MultiPage(TOP_MENU_H_SIZE, page_dict)

    # away_logo = Logo('resources/logos/DET_dark.svg', left_top=(15, 55), size=(170, 118))
    # home_logo = Logo('resources/logos/PHI_dark.svg', left_top=(15, 187), size=(170, 118))

    # for file in os.listdir('resources/logos'):
    #     if not file.endswith('.svg'):
    #         continue
    #
    #     surface.fill(COLOR_BACKGROUND)
    #     logo = Logo('resources/logos/' + file)
    #     surface.blit(logo.surf, (0, 0))
    #     pygame.display.update()
    #     pygame.time.wait(2000)

    main_loop = True
    while main_loop:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                main_loop = False
            elif event.type == KEYDOWN:
                if event.key == K_BACKSPACE:
                    main_loop = False

        surface.fill(COLOR_BACKGROUND)

        surface.blit(multi_page.surf, multi_page.rect)
        # surface.blit(away_logo.surf, away_logo.rect)
        # surface.blit(home_logo.surf, home_logo.rect)

        pygame.display.update()
        clock.tick(FPS)
        # if test:
        #     print(clock.get_fps(), 'fps')


    pygame.quit()


if __name__ == '__main__':
    main()