import pygame
import pygame_menu

# Constants and global variables
ABOUT = [f'pygame-menu {pygame_menu.__version__}',
         f'Author: {pygame_menu.__author__}',
         '',
         f'Email: {pygame_menu.__email__}']
COLOR_BACKGROUND = [15, 15, 218]
FPS = 20
W_SIZE = 480  # Width of window size
H_SIZE = 320  # Height of window size
WINDOW_SIZE = (W_SIZE, H_SIZE)
# HELP = ['Press ESC to enable/disable Menu',
#         'Press ENTER to access a Sub-Menu or use an option',
#         'Press UP/DOWN to move through Menu',
#         'Press LEFT/RIGHT to move through Selectors']


def main(test: bool = False) -> None:
    """
    Main program.

    :param test: Indicate function is being tested
    """

    pygame.init()
    clock = pygame.time.Clock()

    surface = pygame.display.set_mode(WINDOW_SIZE, pygame.NOFRAME)

    away_rect = pygame.Rect((15, 55), (170, 118))
    home_rect = pygame.Rect((15, 187), (170, 118))

    away_team_logo = pygame.image.load('resources/logos/UTA_dark.svg').convert_alpha()
    away_size = away_team_logo.get_size()

    if away_size[0] < away_size[1]:
        w1 = round(118 / away_size[1] * away_size[0])
        h1 = 118
    else:
        w1 = 170
        h1 = round(170 / away_size[0] * away_size[1])
    away_size = (w1, h1)
    away_team_logo = pygame.transform.scale(away_team_logo, away_size)

    home_team_logo = pygame.image.load('resources/logos/PHI_light.svg').convert(16, 0)  # .convert_alpha()
    home_size = home_team_logo.get_size()
    print(home_size)

    if home_size[0] < home_size[1]:
        w1 = round(118 / home_size[1] * home_size[0])
        h1 = 118
    else:
        w1 = 170
        h1 = round(170 / home_size[0] * home_size[1])
    home_size = (w1, h1)
    print(home_size)
    home_team_logo = pygame.transform.scale(home_team_logo, home_size)
    print(home_team_logo.get_size())
    print(home_team_logo.get_rect())

    main_loop = True
    while main_loop:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                main_loop = False

        surface.fill(COLOR_BACKGROUND)
        surface.blit(away_team_logo, away_team_logo.get_rect(center=away_rect.center))  # team_logo.get_rect(center=surface.get_rect().center))
        surface.blit(home_team_logo, home_team_logo.get_rect(center=home_rect.center))
        pygame.display.update()
        clock.tick(FPS)


    pygame.quit()


if __name__ == '__main__':
    main()