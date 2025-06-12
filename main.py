#!/usr/bin/env python
import os
import pygame as pg
from source import tool
from source.state.level import Level
from source import constants as c

os.environ["SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR"] = "0"
pg.init()

if __name__ == "__main__":
    game = tool.Control()
    state_dict = { c.LEVEL: Level() }
    game.setup_states(state_dict, c.LEVEL)
    game.run()