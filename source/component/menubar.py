import random
import pygame as pg
from .. import tool
from .. import constants as c



def getCardPool(data):
    card_pool = {c.PLANT_CARD_INFO[c.PLANT_CARD_INDEX[card_name]]: data[card_name]
                    for card_name in data}
    return card_pool

class Card():
    def __init__(self, x:int, y:int, index:int, scale:float=0.5, not_recommend=0):
        self.info = c.PLANT_CARD_INFO[index]
        self.loadFrame(self.info[c.CARD_INDEX], scale)
        self.rect = self.orig_image.get_rect()
        self.rect.x = x
        self.rect.y = y
        # 绘制植物阳光消耗大小
        font = pg.font.Font(c.FONT_PATH, 12)
        self.sun_cost_img = font.render(str(self.info[c.SUN_INDEX]), True, c.BLACK)
        self.sun_cost_img_rect = self.sun_cost_img.get_rect()
        sun_cost_img_x = 32 - self.sun_cost_img_rect.w
        self.orig_image.blit(self.sun_cost_img,
                            (sun_cost_img_x, 52, self.sun_cost_img_rect.w, self.sun_cost_img_rect.h))
        
        self.index = index
        self.sun_cost = self.info[c.SUN_INDEX]
        self.frozen_time = self.info[c.FROZEN_TIME_INDEX]
        self.frozen_timer = -self.frozen_time
        self.refresh_timer = 0
        self.select = True
        self.clicked = False
        self.not_recommend = not_recommend
        if self.not_recommend:
            self.orig_image.set_alpha(128)
            self.image = pg.Surface((self.rect.w, self.rect.h))  # 黑底
            self.image.blit(self.orig_image, (0,0), (0, 0, self.rect.w, self.rect.h))
        else:
            self.image = self.orig_image
            self.image.set_alpha(255)

    def loadFrame(self, name, scale):
        frame = tool.GFX[name]
        rect = frame.get_rect()
        width, height = rect.w, rect.h

        self.orig_image = tool.get_image(frame, 0, 0, width, height, c.BLACK, scale)
        self.image = self.orig_image

    def checkMouseClick(self, mouse_pos):
        x, y = mouse_pos
        if (self.rect.x <= x <= self.rect.right and
        self.rect.y <= y <= self.rect.bottom):
            return True
        return False

    def canClick(self, sun_value, current_time):
        if self.sun_cost <= sun_value and (current_time - self.frozen_timer) > self.frozen_time:
            return True
        return False

    def canSelect(self):
        return self.select

    def setSelect(self, can_select):
        self.select = can_select
        if can_select:
            if self.not_recommend % 2:
                self.orig_image.set_alpha(128)
                self.image = pg.Surface((self.rect.w, self.rect.h))  # 黑底
                self.image.blit(self.orig_image, (0,0), (0, 0, self.rect.w, self.rect.h))
            else:
                self.image = self.orig_image
                self.image.set_alpha(255)
        else:
            self.orig_image.set_alpha(64)
            self.image = pg.Surface((self.rect.w, self.rect.h))  # 黑底
            self.image.blit(self.orig_image, (0,0), (0, 0, self.rect.w, self.rect.h))

    def setFrozenTime(self, current_time):
        self.frozen_timer = current_time

    def createShowImage(self, sun_value, current_time):
        # 有关是否满足冷却与阳光条件的图片形式
        time = current_time - self.frozen_timer
        if time < self.frozen_time: #cool down status
            image = pg.Surface((self.rect.w, self.rect.h))  # 黑底
            frozen_image = self.orig_image
            frozen_image.set_alpha(128)
            frozen_height = ((self.frozen_time - time)/self.frozen_time) * self.rect.h
            
            image.blit(frozen_image, (0,0), (0, 0, self.rect.w, frozen_height))
            self.orig_image.set_alpha(192)
            image.blit(self.orig_image, (0,frozen_height),
                       (0, frozen_height, self.rect.w, self.rect.h - frozen_height))
        elif self.sun_cost > sun_value: #disable status
            image = pg.Surface((self.rect.w, self.rect.h))  # 黑底
            self.orig_image.set_alpha(192)
            image.blit(self.orig_image, (0,0), (0, 0, self.rect.w, self.rect.h))
        elif self.clicked:
            image = pg.Surface((self.rect.w, self.rect.h))  # 黑底
            chosen_image = self.orig_image
            chosen_image.set_alpha(128)
            
            image.blit(chosen_image, (0,0), (0, 0, self.rect.w, self.rect.h))
        else:
            image = self.orig_image
            image.set_alpha(255)
        return image

    def update(self, sun_value, current_time):
        if (current_time - self.refresh_timer) >= 250:
            self.image = self.createShowImage(sun_value, current_time)
            self.refresh_timer = current_time

    def draw(self, surface):
        surface.blit(self.image, self.rect)


# 传送带模式的卡片
class MoveCard():
    def __init__(self, x, y, card_name, plant_name, scale=0.5):
        self.loadFrame(card_name, scale)
        self.rect = self.orig_image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.rect.w = 1
        self.clicked = False
        self.image = self.createShowImage()

        self.card_name = card_name
        self.plant_name = plant_name
        self.move_timer = 0
        self.select = True

    def loadFrame(self, name, scale):
        frame = tool.GFX[name]
        rect = frame.get_rect()
        width, height = rect.w, rect.h

        self.orig_image = tool.get_image(frame, 0, 0, width, height, c.BLACK, scale)
        self.orig_rect = self.orig_image.get_rect()
        self.image = self.orig_image

    def checkMouseClick(self, mouse_pos):
        x, y = mouse_pos
        if (self.rect.x <= x <= self.rect.right and
            self.rect.y <= y <= self.rect.bottom):
            return True
        return False

    def createShowImage(self):
        if self.rect.w < self.orig_rect.w: #create a part card image
            image = pg.Surface([self.rect.w, self.rect.h])
            if self.clicked:
                self.orig_image.set_alpha(128)
            else:
                self.orig_image.set_alpha(255)
            image.blit(self.orig_image, (0, 0), (0, 0, self.rect.w, self.rect.h))
            self.rect.w += 1
        else:
            if self.clicked:
                image = pg.Surface([self.rect.w, self.rect.h])  # 黑底
                self.orig_image.set_alpha(128)
                
                image.blit(self.orig_image, (0,0), (0, 0, self.rect.w, self.rect.h))
            else:
                self.orig_image.set_alpha(255)
                image = self.orig_image
        return image

    def update(self, left_x, current_time):
        if self.move_timer == 0:
            self.move_timer = current_time
        elif (current_time - self.move_timer) >= c.CARD_MOVE_TIME:
            if self.rect.x > left_x:
                self.rect.x -= 1
            self.image = self.createShowImage()
            self.move_timer += c.CARD_MOVE_TIME

    def draw(self, surface):
        surface.blit(self.image, self.rect)

# 传送带
class MoveBar():
    def __init__(self, card_pool):
        self.loadFrame(c.MOVEBAR_BACKGROUND)
        self.rect = self.image.get_rect()
        self.rect.x = 20
        self.rect.y = 0
        
        self.card_start_x = self.rect.x + 8
        self.card_end_x = self.rect.right - 5
        self.card_pool = card_pool
        self.card_pool_name = tuple(self.card_pool.keys())
        self.card_pool_weight = tuple(self.card_pool.values())
        self.card_list = []
        self.create_timer = -c.MOVEBAR_CARD_FRESH_TIME

    def loadFrame(self, name):
        frame = tool.GFX[name]
        rect = frame.get_rect()
        frame_rect = (rect.x, rect.y, rect.w, rect.h)

        self.image = tool.get_image(tool.GFX[name], *frame_rect, c.WHITE, 1)

    def createCard(self):
        if len(self.card_list) > 0 and self.card_list[-1].rect.right > self.card_end_x:
            return False
        x = self.card_end_x
        y = 6
        selected_card = random.choices(self.card_pool_name, self.card_pool_weight)[0]
        self.card_list.append(MoveCard(x, y, selected_card[c.CARD_INDEX], selected_card[c.PLANT_NAME_INDEX]))
        return True

    def update(self, current_time):
        self.current_time = current_time
        left_x = self.card_start_x
        for card in self.card_list:
            card.update(left_x, self.current_time)
            left_x = card.rect.right + 1

        if (self.current_time - self.create_timer) > c.MOVEBAR_CARD_FRESH_TIME:
            if self.createCard():
                self.create_timer = self.current_time

    def checkCardClick(self, mouse_pos):
        result = None
        for index, card in enumerate(self.card_list):
            if card.checkMouseClick(mouse_pos):
                result = (card.plant_name, card)
                break
        return result
    
    def checkMenuBarClick(self, mouse_pos):
        x, y = mouse_pos
        if (self.rect.x <= x <= self.rect.right and
            self.rect.y <= y <= self.rect.bottom):
            return True
        return False

    def deleateCard(self, card):
        self.card_list.remove(card)

    def draw(self, surface):
        surface.blit(self.image, self.rect)
        for card in self.card_list:
            card.draw(surface)
