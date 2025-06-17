import pygame as pg
import os
from .. import tool
from .. import constants as c

class Menu(tool.State):
    
    def __init__(self):
        tool.State.__init__(self)
    
    def startup(self, current_time:int, persist):
        self.next = c.PLAY
        self.persist = persist
        self.game_info = persist
        self.setupBackground()
        self.setupOptions()
        
    def setupBackground(self):
        frame_rect = (80, 0, 800, 600)
        self.bg_image = tool.get_image(tool.GFX[c.MAIN_MENU_IMAGE], *frame_rect)
        self.bg_rect = self.bg_image.get_rect()
        self.bg_rect.x = 0
        self.bg_rect.y = 0

    def setupOptions(self):
        # survival
        frame_rect = (0, 0, 180, 140)
        self.adventure_frames = [tool.get_image_alpha(tool.GFX[f"{c.OPTION_ADVENTURE}_{i}"], *frame_rect) for i in range(2)]
        self.adventure_image = self.adventure_frames[0]
        self.adventure_rect = self.adventure_image.get_rect()
        self.adventure_rect.x = 50
        self.adventure_rect.y = 400
        self.adventure_highlight_time = 0

        # scoreboard
        littleGame_frame_rect = (0, 0, 150, 150)
        self.littleGame_frames = [tool.get_image_alpha(tool.GFX[f"{c.LITTLEGAME_BUTTON}_{i}"], *littleGame_frame_rect) for i in range(2)]
        self.littleGame_image = self.littleGame_frames[0]
        self.littleGame_rect = self.littleGame_image.get_rect()
        self.littleGame_rect.x = 300
        self.littleGame_rect.y = 400
        self.littleGame_highlight_time = 0

        # exit
        exit_frame_rect = (0, 0, 150, 150)
        self.exit_frames = [tool.get_image_alpha(tool.GFX[f"{c.EXIT}_{i}"], *exit_frame_rect, scale=1.1) for i in range(2)]
        self.exit_image = self.exit_frames[0]
        self.exit_rect = self.exit_image.get_rect()
        self.exit_rect.x = 550
        self.exit_rect.y = 400
        self.exit_highlight_time = 0

        # timer
        self.adventure_start = 0
        self.adventure_timer = 0
        self.adventure_clicked = False
        self.option_button_clicked = False

    def checkHilight(self, x:int, y:int):
        if self.inArea(self.adventure_rect, x, y):
            self.adventure_highlight_time = self.current_time
        elif self.inArea(self.littleGame_rect, x, y):
            self.littleGame_highlight_time = self.current_time
        elif self.inArea(self.exit_rect, x, y):
            self.exit_highlight_time = self.current_time


        self.adventure_image = self.chooseHilightImage(self.adventure_highlight_time, self.adventure_frames)
        self.exit_image = self.chooseHilightImage(self.exit_highlight_time, self.exit_frames)
        self.littleGame_image = self.chooseHilightImage(self.littleGame_highlight_time, self.littleGame_frames)

    def chooseHilightImage(self, hilightTime:int, frames):
        if (self.current_time - hilightTime) < 80:
            index= 1
        else:
            index = 0
        return frames[index]

    def respondAdventureClick(self):
        self.adventure_clicked = True
        self.adventure_timer = self.adventure_start = self.current_time
        self.persist[c.GAME_MODE] = c.MODE_LITTLEGAME

    def respondLittleGameClick(self):
        self.done = True
        self.next = c.SCOREBOARD


    # exit button clicked
    def respondExitClick(self):
        self.done = True
        self.next = c.EXIT


    def update(self, surface:pg.Surface, current_time:int, mouse_pos:list, mouse_click):
        self.current_time = self.game_info[c.CURRENT_TIME] = current_time
        
        surface.blit(self.bg_image, self.bg_rect)
        surface.blit(self.adventure_image, self.adventure_rect)
        surface.blit(self.littleGame_image, self.littleGame_rect)
        surface.blit(self.exit_image, self.exit_rect)
        
        if self.adventure_clicked:
            if ((self.current_time - self.adventure_timer) // 150) % 2:
                self.adventure_image = self.adventure_frames[1]
            else:
                self.adventure_image = self.adventure_frames[0]
            if (self.current_time - self.adventure_start) > 3200:
                self.done = True
        else:
            x, y = pg.mouse.get_pos()
            self.checkHilight(x, y)
            if (self.game_info[c.LEVEL_COMPLETIONS] or self.game_info[c.LITTLEGAME_COMPLETIONS]):
                pass
            if mouse_pos:
                if self.inArea(self.adventure_rect, *mouse_pos):
                    self.respondAdventureClick()
                elif self.inArea(self.littleGame_rect, *mouse_pos):
                    self.respondLittleGameClick()
                elif self.inArea(self.exit_rect, *mouse_pos):
                    self.respondExitClick()
