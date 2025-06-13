#!/usr/bin/env python
"""精簡版 main.py
啟動後直接進入《NNNuts Bowling》小遊戲
保留完整殭屍與植物定義，僅簡化狀態切換邏輯
"""
import logging
import traceback
import os
import pygame as pg
from logging.handlers import RotatingFileHandler

# 初始化 pygame
os.environ["SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR"] = "0"
pg.init()

from source import tool
from source import constants as c
from source.state import level  # 這裡僅需 Level 狀態
from source.state import mainmenu
def main():
    """程式進入點"""
    # === 狀態機啟動 ===
    game = tool.Control()

    # 只玩堅果保齡球（little game #0）
    game.game_info[c.GAME_MODE] = c.MODE_LITTLEGAME
    game.game_info[c.LITTLEGAME_NUM] = 1

    # 僅註冊 Level 狀態即可
    state_dict = {
                c.MAIN_MENU: mainmenu.Menu(),
                c.LEVEL: level.Level()
                  }
    game.setup_states(state_dict, c.MAIN_MENU)
    game.run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.basicConfig(level=logging.ERROR)
        logging.error("未處理例外：%s", traceback.format_exc())