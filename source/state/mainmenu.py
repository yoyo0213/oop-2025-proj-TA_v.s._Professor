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
        # 1、形参中加单星号，即f(*x)则表示x为元组，所有对x的操作都应将x视为元组类型进行。
        # 2、双星号同上，区别是x视为字典。
        # 3、在变量前加单星号表示将元组（列表、集合）拆分为单个元素。
        # 4、双星号同上，区别是目标为字典，字典前加单星号的话可以得到“键”。
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

        # menu
        option_button_frame_rect = (0, 0, 81, 31)
        self.option_button_frames = [tool.get_image_alpha(tool.GFX[f"{c.OPTION_BUTTON}_{i}"], *option_button_frame_rect) for i in range(2)]
        self.option_button_image = self.option_button_frames[0]
        self.option_button_rect = self.option_button_image.get_rect()
        self.option_button_rect.x = 560
        self.option_button_rect.y = 490
        self.option_button_highlight_time = 0

        # help
        help_frame_rect = (0, 0, 48, 22)
        self.help_frames = [tool.get_image_alpha(tool.GFX[f"{c.HELP}_{i}"], *help_frame_rect) for i in range(2)]
        self.help_image = self.help_frames[0]
        self.help_rect = self.help_image.get_rect()
        self.help_rect.x = 653
        self.help_rect.y = 520
        self.help_hilight_time = 0
        
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


    # 点击到退出按钮，修改转态的done属性
    def respondExitClick(self):
        self.done = True
        self.next = c.EXIT

    # 帮助按钮点击
    def respondHelpClick(self):
        self.done = True
        self.next = c.HELP_SCREEN



    def respondOptionButtonClick(self):
        self.option_button_clicked = True


   
    def update(self, surface:pg.Surface, current_time:int, mouse_pos:list, mouse_click):
        self.current_time = self.game_info[c.CURRENT_TIME] = current_time
        
        surface.blit(self.bg_image, self.bg_rect)
        surface.blit(self.adventure_image, self.adventure_rect)
        surface.blit(self.littleGame_image, self.littleGame_rect)
        surface.blit(self.exit_image, self.exit_rect)
        if self.game_info[c.LEVEL_COMPLETIONS] or self.game_info[c.LITTLEGAME_COMPLETIONS]:
            pass
        # 点到冒险模式后播放动画
        if self.adventure_clicked:
            # 乱写一个不用信号标记的循环播放 QwQ
            if ((self.current_time - self.adventure_timer) // 150) % 2:
                self.adventure_image = self.adventure_frames[1]
            else:
                self.adventure_image = self.adventure_frames[0]
            if (self.current_time - self.adventure_start) > 3200:
                self.done = True
        # 点到选项按钮后显示菜单
        else:
            # 先检查选项高亮预览
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
                elif self.inArea(self.help_rect, *mouse_pos):
                    self.respondHelpClick()
