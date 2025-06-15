import os
import pygame as pg
from abc import abstractmethod
from .. import tool
from .. import constants as c
from . import scoreborard as sb

class Screen(tool.State):
    def __init__(self):
        tool.State.__init__(self)

    @abstractmethod
    def startup(self, current_time, persist):
        pass

    def setupImage(self, name, frame_rect=(0, 0, 800, 600), color_key=c.BLACK):
        # 背景图本身
        self.image = tool.get_image(tool.GFX[name], *frame_rect, colorkey=color_key)
        self.rect = self.image.get_rect()
        self.rect.x = 0
        self.rect.y = 0

        # 按钮
        frame_rect = (0, 0, 111, 26)
        ## 主菜单按钮
        self.main_menu_button_image = tool.get_image_alpha(tool.GFX[c.UNIVERSAL_BUTTON], *frame_rect)
        self.main_menu_button_image_rect = self.main_menu_button_image.get_rect()
        self.main_menu_button_image_rect.x = 620
        ### 主菜单按钮上的文字
        font = pg.font.Font(c.FONT_PATH, 18)
        main_menu_text = font.render("主菜单", True, c.NAVYBLUE)
        main_menu_text_rect = main_menu_text.get_rect()
        main_menu_text_rect.x = 29
        ## 继续按钮
        self.next_button_image = tool.get_image_alpha(tool.GFX[c.UNIVERSAL_BUTTON], *frame_rect)
        self.next_button_image_rect = self.next_button_image.get_rect()
        self.next_button_image_rect.x = 70
        ### 继续按钮上的文字
        if name == c.GAME_VICTORY_IMAGE:
            next_text = font.render("下一关", True, c.NAVYBLUE)
            next_text_rect = next_text.get_rect()
            next_text_rect.x = 29
            self.next_button_image_rect.y = self.main_menu_button_image_rect.y = 555
        else:
            next_text = font.render("重新开始", True, c.NAVYBLUE)
            next_text_rect = next_text.get_rect()
            next_text_rect.x = 21
            self.next_button_image_rect.y = self.main_menu_button_image_rect.y = 530
        self.next_button_image.blit(next_text, next_text_rect)
        self.main_menu_button_image.blit(main_menu_text, main_menu_text_rect)
        self.image.blit(self.next_button_image, self.next_button_image_rect)
        self.image.blit(self.main_menu_button_image, self.main_menu_button_image_rect)

    def update(self, surface, current_time, mouse_pos, mouse_click):
        surface.fill(c.WHITE)
        surface.blit(self.image, self.rect)
        if mouse_pos:
            # 点到继续
            if self.inArea(self.next_button_image_rect, *mouse_pos):
                self.next = c.LEVEL
                self.done = True
            # 点到主菜单
            elif self.inArea(self.main_menu_button_image_rect, *mouse_pos):
                self.next = c.MAIN_MENU
                self.done = True

class HelpScreen(tool.State):
    def __init__(self):
        tool.State.__init__(self)

    def startup(self, current_time, persist):
        self.start_time = current_time
        self.persist = persist
        self.game_info = persist
        self.setupImage()
        pg.display.set_caption("pypvz: 帮助")

    def setupImage(self):
        # 主体
        frame_rect = (-100, -50, 800, 600)
        self.image = tool.get_image(tool.GFX[c.HELP_SCREEN_IMAGE], *frame_rect, colorkey=(0, 255, 255))
        self.rect = self.image.get_rect()
        self.rect.x = 0
        self.rect.y = 0
        
        # 主菜单按钮
        frame_rect = (0, 0, 111, 26)
        self.main_menu_button_image = tool.get_image_alpha(tool.GFX[c.UNIVERSAL_BUTTON], *frame_rect)
        self.main_menu_button_image_rect = self.main_menu_button_image.get_rect()
        self.main_menu_button_image_rect.x = 343
        self.main_menu_button_image_rect.y = 500
        ### 主菜单按钮上的文字
        font = pg.font.Font(c.FONT_PATH, 18)
        main_menu_text = font.render("Menu", True, c.NAVYBLUE)
        main_menu_text_rect = main_menu_text.get_rect()
        main_menu_text_rect.x = 29
        self.main_menu_button_image.blit(main_menu_text, main_menu_text_rect)
        self.image.blit(self.main_menu_button_image, self.main_menu_button_image_rect)

    def update(self, surface, current_time, mouse_pos, mouse_click):
        surface.fill(c.BLACK)
        surface.blit(self.image, self.rect)
        if mouse_pos:
            # 检查主菜单点击
            if self.inArea(self.main_menu_button_image_rect, *mouse_pos):
                self.next = c.MAIN_MENU
                self.done = True
class EndScreen(tool.State):
    def __init__(self):
        super().__init__()
        self.total_time = 0
        self.input_name = ""
        self.active = True
        self.saved = False

    def startup(self, current_time, persist):
        self.start_time = current_time
        self.persist = persist
        self.game_info = persist
        # 遊戲時間存在 self.game_info[c.LEVEL_NUM]
        self.total_time = self.game_info[c.LEVEL_NUM] // 1000
        self.scoreboard = sb.Scoreboard()

    def setupImage(self,surface):
        surface.fill((0, 0, 0))
        font = pg.font.Font(c.FONT_PATH, 36)
        small_font = pg.font.Font(c.FONT_PATH, 24)

        # 繪製輸入框（矩形或底線）
        input_box_rect = pg.Rect(220, 290, 300, 40)  # 固定輸入框位置與大小
        pg.draw.rect(surface, (255, 255, 255), input_box_rect, 2)  # 白色邊框，線寬=2
        # 顯示輸入提示
        prompt = "Enter your name："
        prompt_surf = small_font.render(prompt, True, (255, 255, 255))
        surface.blit(prompt_surf, (220, 250))
        # 顯示遊戲時間
        minutes = self.total_time // 60
        seconds = self.total_time % 60
        time_str = f"Survival Time: {minutes:02d}:{seconds:02d}"
        time_surf = font.render(time_str, True, (255, 255, 0))
        surface.blit(time_surf, (220, 120))

        

    def update(self, surface, current_time, mouse_pos, mouse_click):
        font = pg.font.Font(c.FONT_PATH, 36)
        small_font = pg.font.Font(c.FONT_PATH, 24)
        self.setupImage(surface)

        if self.active and not self.saved:
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_RETURN:
                        # save to json
                        self.scoreboard.add_score(self.input_name, self.total_time)
                        self.saved = True
                        self.active = False
                    elif event.key == pg.K_BACKSPACE:
                        self.input_name = self.input_name[:-1]
                    else:
                        if len(self.input_name) < 10 and event.unicode.isprintable():
                            self.input_name += event.unicode
            
            # 顯示已輸入的名字
            name_surf = font.render(self.input_name, True, c.WHITE)
            surface.blit(name_surf, (225, 290))

        # successfully saved message
        if self.saved:
            saved_surf = small_font.render("Saved. Press to continue", True, (255, 255, 255))
            surface.blit(saved_surf, (220, 350))
            for event in pg.event.get():
                if event.type == pg.KEYDOWN:
                    self.next = c.SCOREBOARD
                    self.done = True

class ScoreScreen(tool.State):
    def __init__(self):
        tool.State.__init__(self)

    def startup(self, current_time, persist):
        self.start_time = current_time
        self.persist = persist
        self.game_info = persist
        self.setupImage()
        pg.display.set_caption("pypvz: 排行榜")
        # load the scoreboard
        self.scoreboard = sb.Scoreboard()

    def setupImage(self):
        # background
        frame_rect = (-100, -50, 800, 600)
        self.image = tool.get_image(tool.GFX[c.GAME_LOSE_IMAGE], *frame_rect, colorkey=(0, 255, 255))
        self.rect = self.image.get_rect()
        self.rect.x = 0
        self.rect.y = 0
        # clear all data button
        fram_rect = (0, 0, 111, 26)
        self.clear_button_image = tool.get_image_alpha(tool.GFX[c.UNIVERSAL_BUTTON], *fram_rect)
        self.clear_button_image_rect = self.clear_button_image.get_rect()
        self.clear_button_image_rect.x = 400
        self.clear_button_image_rect.y = 500
        font = pg.font.Font(c.FONT_PATH, 16)
        clear_button_text = font.render("clear all data", True, c.NAVYBLUE)
        clear_button_text_rect = clear_button_text.get_rect()
        clear_button_text_rect.x = 8
        self.clear_button_image.blit(clear_button_text, clear_button_text_rect)
        self.image.blit(self.clear_button_image, self.clear_button_image_rect)

        # go back to main menu 
        button_rect = (0, 0, 111, 26)
        self.main_menu_button_image = tool.get_image_alpha(tool.GFX[c.UNIVERSAL_BUTTON], *button_rect)
        self.main_menu_button_image_rect = self.main_menu_button_image.get_rect()
        self.main_menu_button_image_rect.x = 200
        self.main_menu_button_image_rect.y = 500
        font = pg.font.Font(c.FONT_PATH, 18)
        main_menu_text = font.render("return", True, c.NAVYBLUE)
        main_menu_text_rect = main_menu_text.get_rect()
        main_menu_text_rect.x = 29
        self.main_menu_button_image.blit(main_menu_text, main_menu_text_rect)
        self.image.blit(self.main_menu_button_image, self.main_menu_button_image_rect)
    def clear_scores(self):
        self.scoreboard.clear_scores()
    
    def update(self, surface, current_time, mouse_pos, mouse_click):
        surface.fill(c.BLACK)
        surface.blit(self.image, self.rect)

        # 顯示排行榜資料
        font = pg.font.Font(c.FONT_PATH, 24)
        scores = self.scoreboard.get_top_scores()

        for i, entry in enumerate(scores):
            text = f"{i+1}. {entry['name']} - {entry['survival time']} 秒 - {entry['time']}"
            text_surface = font.render(text, True, c.WHITE)
            surface.blit(text_surface, (100, 120 + i * 30))
        # click
        if mouse_pos:
            if self.inArea(self.main_menu_button_image_rect, *mouse_pos):
                if mouse_click:
                    self.next = c.MAIN_MENU
                    self.done = True
            elif self.inArea(self.clear_button_image_rect, *mouse_pos):
                if mouse_click:
                    self.clear_scores()

