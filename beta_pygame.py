import os
# from time import sleep
from typing import Tuple

import pygame
from pygame.locals import *  # for key coordinates
import pygame_menu


# Constants and global variables
ABOUT = [f'pygame-menu {pygame_menu.__version__}',
         f'Author: {pygame_menu.__author__}',
         '',
         f'Email: {pygame_menu.__email__}']

BACKGROUNDS = {'dark': {'gray': [[0, 0, 3],
                                [15, 15, 18],
                                [30, 30, 33],
                                [45, 45, 48],
                                [60, 60, 63],
                                [75, 75, 78],
                                [90, 90, 93]],
                        'blue': [[0, 7, 84],
                                 [0, 9, 119],
                                 [0, 14, 173]]},
               'light': {'gray': [[180, 180, 183],
                                  [195, 195, 198],
                                  [210, 210, 213],
                                  [225, 225, 228],
                                  [240, 240, 243],
                                  [255, 255, 255]]}
               }

# BORDERS = {'light': {'gray': [[180, 180, 183],
#                               [195, 195, 198],
#                               [210, 210, 213],
#                               [225, 225, 228],
#                               [240, 240, 243],
#                               [255, 255, 255]]}}

COLOR_BACKGROUND_ID = ['dark', 'gray', 1]
COLOR_BACKGROUND = BACKGROUNDS[COLOR_BACKGROUND_ID[0]][COLOR_BACKGROUND_ID[1]][COLOR_BACKGROUND_ID[2]]

COLOR_BORDER_ID = ['light', 'gray', 3]
COLOR_BORDER = BACKGROUNDS[COLOR_BORDER_ID[0]][COLOR_BORDER_ID[1]][COLOR_BORDER_ID[2]]

FPS = 20
W_SIZE = 480  # Width of window size
H_SIZE = 320  # Height of window size
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
        pixel_surf.fill((0, 0, 0, 0))  # make sure background is transparent
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
        self.surf.fill((0, 0, 0, 0))  # make sure background is transparent
        self.surf.blit(pixel_surf, pixel_surf.get_rect(center=self.surf.get_rect().center))

        # self.rect = self.surf.get_rect()


def main(test: bool = False) -> None:
    """
    Main program.

    :param test: Indicate function is being tested
    """

    pygame.init()
    clock = pygame.time.Clock()

    surface = pygame.display.set_mode(WINDOW_SIZE, pygame.NOFRAME)
    pygame.Surface.convert_alpha(surface)

    # away_rect = pygame.Rect((15, 55), (170, 118))
    # home_rect = pygame.Rect((15, 187), (170, 118))
    #
    # away_team_logo = pygame.image.load('resources/logos/TBL_dark.svg').convert_alpha()
    # away_size = away_team_logo.get_size()
    #
    # if away_size[0] < away_size[1]:
    #     w1 = round(118 / away_size[1] * away_size[0])
    #     h1 = 118
    # else:
    #     w1 = 170
    #     h1 = round(170 / away_size[0] * away_size[1])
    # away_size = (w1, h1)
    # away_team_logo = pygame.transform.scale(away_team_logo, away_size)

    # home_logo_raw = pygame.image.load('resources/logos/TBL_dark.svg')  # .convert_alpha()
    # pixel_rect = home_logo_raw.get_bounding_rect()
    # home_logo = pygame.Surface(pixel_rect.size).convert_alpha()
    # home_logo.fill((0, 0, 0, 0))
    # home_logo.blit(home_logo_raw, (0, 0), pixel_rect)
    #
    # print(1, pixel_rect.size)
    # home_size = home_logo.get_size()
    # print(2, home_size)
    #
    # if home_size[0] / home_size[1] < 1.441:
    #     w1 = round(118 / home_size[1] * home_size[0])
    #     h1 = 118
    # else:
    #     w1 = 170
    #     h1 = round(170 / home_size[0] * home_size[1])
    # home_size = (w1, h1)
    # print(3, home_size)
    # home_logo = pygame.transform.scale(home_logo, home_size)
    # print(4, home_logo_raw.get_size())
    # print(5, home_logo_raw.get_rect())

    away_logo = Logo('resources/logos/WPG_dark.svg', left_top=(15, 55), height=118)
    home_logo = Logo('resources/logos/PHI_dark.svg', left_top=(15, 187), height=118)


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
        # surface.blit(away_team_logo, away_team_logo.get_rect(center=away_rect.center))  # team_logo.get_rect(center=surface.get_rect().center))
        surface.blit(away_logo.surf, away_logo.rect)
        # surface.blit(home_logo, home_logo.get_rect(center=home_rect.center))
        # surface.blit(home_logo.surf, home_logo.surf.get_rect(center=home_rect.center))
        # surface.blit(home_logo.surf, home_rect)
        surface.blit(home_logo.surf, home_logo.rect)
        pygame.display.update()
        clock.tick(FPS)
        if test:
            print(clock.get_fps(), 'fps')


    pygame.quit()


if __name__ == '__main__':
    main(test=True)