import logging
import traceback
import os
import pygame as pg
from logging.handlers import RotatingFileHandler

# initialize pygame
os.environ["SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR"] = "0"
pg.init()

#include 
from source import constants as c
from source.state import level ,screen, mainmenu 
import source.tool as tool

def main():
    # start
    game = tool.Control()

    state_dict = {  c.MAIN_MENU:    mainmenu.Menu(),
                        c.PLAY:        level.Level(),
                        c.ENDSCREEN:     screen.EndScreen(),
                        c.SCOREBOARD:   screen.ScoreScreen()
                        }
    game.setup_states(state_dict, c.MAIN_MENU)
    game.run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.basicConfig(level=logging.ERROR)
        logging.error("未處理例外：%s", traceback.format_exc())