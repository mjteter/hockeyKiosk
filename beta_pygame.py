# import os
# from time import sleep
from typing import Tuple
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

COLOR_BACKGROUND_ID = ['dark', 'gray', 1]
COLOR_BACKGROUND = BACKGROUNDS[COLOR_BACKGROUND_ID[0]][COLOR_BACKGROUND_ID[1]][COLOR_BACKGROUND_ID[2]]

COLOR_BORDER_ID = ['light', 'gray', 5]
COLOR_BORDER = BACKGROUNDS[COLOR_BORDER_ID[0]][COLOR_BORDER_ID[1]][COLOR_BORDER_ID[2]]

COLOR_TAB_TEXT_ACTIVE_ID = ['light', 'gray', 4]
COLOR_TAB_TEXT_ACTIVE = BACKGROUNDS[COLOR_TAB_TEXT_ACTIVE_ID[0]][COLOR_TAB_TEXT_ACTIVE_ID[1]][COLOR_TAB_TEXT_ACTIVE_ID[2]]

COLOR_TAB_TEXT_INACTIVE_ID = ['light', 'gray', 8]
COLOR_TAB_TEXT_INACTIVE = BACKGROUNDS[COLOR_TAB_TEXT_INACTIVE_ID[0]][COLOR_TAB_TEXT_INACTIVE_ID[1]][COLOR_TAB_TEXT_INACTIVE_ID[2]]


COLOR_EMPTY = (0, 0, 0, 0)

FPS = 20
W_SIZE = 480  # Width of window size
H_SIZE = 320  # Height of window size
TOP_MENU_H_SIZE = 40  # height of tabs at top
WINDOW_SIZE = (W_SIZE, H_SIZE)
# HELP = ['Press ESC to enable/disable Menu',
#         'Press ENTER to access a Sub-Menu or use an option',
#         'Press UP/DOWN to move through Menu',
#         'Press LEFT/RIGHT to move through Selectors']


class Logo(pygame.sprite.Sprite):
    def __init__(self, filepath: str, left_top: Tuple[int, int] = (0, 0), height: int = 118, _ratio: float = 1.441):
        super().__init__()

        size = (round(_ratio * height), height)

        raw_logo = pygame.image.load(filepath)
        pixel_rect = raw_logo.get_bounding_rect()  # sometimes pygame adds empty borders
        pixel_surf = pygame.Surface(pixel_rect.size).convert_alpha()
        pixel_surf.fill(COLOR_EMPTY)  # make sure background is transparent
        pixel_surf.blit(raw_logo, (0, 0), pixel_rect)

        cleaned_size = pixel_surf.get_size()

        if cleaned_size[0] / cleaned_size[1] <= _ratio:
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
    def __init__(self, height):
        super().__init__()

        self.surf = pygame.Surface((W_SIZE, height)).convert_alpha()
        self.surf.fill(COLOR_EMPTY)

        self.rect = self.surf.get_rect()
        self.rect.move_ip(0, H_SIZE - height)


class LiveGame(MultiPageBasePage):
    def __init__(self, height):
        super().__init__(height)

        pygame.draw.rect(self.surf, (100, 100, 100, 255), (50, 50, 75, 75), 0)
        pygame.draw.rect(self.surf, (100, 100, 100, 255), (130, 50, 75, 75), 5)
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
            self.menu_font_bold = pygame.font.Font(FONT_PATH + 'JetBrainsMono-ExtraBold.ttf', self.menu_font_size)
            tab_widths = []
            tab_height = 0
            total_width = 0
            for ii in range(self.total_tabs):
                test_font = self.menu_font_bold.render(tabs[ii][0], True, COLOR_TAB_TEXT_ACTIVE)
                tab_widths.append(test_font.get_rect().width)
                tab_height = test_font.get_rect().height
                total_width += test_font.get_rect().width

            if tab_height > self.tab_padded_height or total_width > self.tab_total_padded_width:
                if self.menu_font_size > 50:
                    self.menu_font_size -= 40
                elif self.menu_font_size > 16:
                    self.menu_font_size -= 2
                else:
                    self.menu_font_size -= 1
            # elif self.menu_font_size < 6:
            #     menu_text_fits = True  # bug out on failure to find reasonable font size
            else:
                menu_text_fits = True
                print(tab_widths)
                ii = 0
                while total_width < self.tab_total_padded_width:
                    tab_widths[ii] += 1
                    total_width += 1
                    if ii == self.total_tabs - 1:
                        ii = 0
                    else:
                        ii += 1
                print(tab_widths)

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

        self.menu_font = pygame.font.Font(FONT_PATH + 'JetBrainsMono-Medium.ttf', self.menu_font_size)
        print(tab_rects)
        for ii, (page_title, page) in enumerate(tabs):
            if self.active_tab == ii:  # if active
                if self.selected == ii:  # if active and selected
                    page_text = self.menu_font_bold.render(page_title, True, COLOR_TAB_TEXT_ACTIVE)
                else:  # if active and not selected
                    page_text = self.menu_font.render(page_title, True, COLOR_TAB_TEXT_ACTIVE)


                self.surf.blit(page.surf, page.rect)  # blit active page
            else:  # not active
                if self.selected == ii:  # if not active and selected
                    page_text = self.menu_font_bold.render(page_title, True, COLOR_TAB_TEXT_INACTIVE)
                else:  # if not active and not selected
                    page_text = self.menu_font.render(page_title, True, COLOR_TAB_TEXT_INACTIVE)

            self.menu_surf.blit(page_text, page_text.get_rect(center=tab_rects[ii].center))
            # test = self.menu_font.render(page_title, True, COLOR_TAB_TEXT_ACTIVE)
            # test2 = self.menu_font_bold.render(page_title, True, COLOR_TAB_TEXT_ACTIVE)
            # self.surf.blit(test, test.get_rect())
            # self.surf.blit(test2, (0, 40))
        pygame.draw.rect(self.menu_surf, COLOR_TAB_TEXT_ACTIVE, tab_rects[0], 2)
        

        self.surf.blit(self.menu_surf, self.menu_rect)


def main() -> None:
    """
    Main program.
    """

    pygame.init()
    clock = pygame.time.Clock()

    surface = pygame.display.set_mode(WINDOW_SIZE, pygame.NOFRAME)
    pygame.Surface.convert_alpha(surface)



    live_game = LiveGame(H_SIZE - TOP_MENU_H_SIZE)
    schedule = Schedule(H_SIZE - TOP_MENU_H_SIZE)
    standings = Standings(H_SIZE - TOP_MENU_H_SIZE)
    settings = Settings(H_SIZE - TOP_MENU_H_SIZE)

    page_dict = (('Live Game', live_game),
                 ('Schedule', schedule),
                 ('Standings', standings),
                 ('Settings', settings))
    multi_page = MultiPage(TOP_MENU_H_SIZE, page_dict)

    # away_logo = Logo('resources/logos/WPG_dark.svg', left_top=(15, 55), height=118)
    # home_logo = Logo('resources/logos/PHI_dark.svg', left_top=(15, 187), height=118)

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