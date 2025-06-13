#!/usr/bin/env python

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

    # 只玩堅果保齡球（little game #0）
    game.game_info[c.GAME_MODE] = c.MODE_LITTLEGAME
    game.game_info[c.LITTLEGAME_NUM] = 1

    # 僅註冊 Level 狀態即可
    state_dict = {  c.MAIN_MENU:    mainmenu.Menu(),
                        c.GAME_VICTORY: screen.GameVictoryScreen(),
                        c.GAME_LOSE:    screen.GameLoseScreen(),
                        c.LEVEL:        level.Level(),
                        c.SCOREBOARD:   screen.ScoreboardScreen(),
                        c.HELP_SCREEN:  screen.HelpScreen(),
                        }
    game.setup_states(state_dict, c.MAIN_MENU)
    game.run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.basicConfig(level=logging.ERROR)
        logging.error("未處理例外：%s", traceback.format_exc())