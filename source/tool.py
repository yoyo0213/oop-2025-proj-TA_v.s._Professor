import logging
import os
import json
from abc import abstractmethod
import pygame as pg
from pygame.locals import *
from . import constants as c
logger = logging.getLogger("main")

# state base class (abstract)
class State():
    def __init__(self):
        self.start_time = 0
        self.current_time = 0
        self.done = False   # not dome
        self.next = None    # next state name
        self.persist = {}   # imformation needed to persist between states

    # initialization operation
    @abstractmethod #need to be defined in subclass
    def startup(self, current_time:int, persist:dict):
        pass
    def cleanup(self):
        self.done = False
        return self.persist
    @abstractmethod
    def update(self, surface:pg.Surface, keys, current_time:int):
        pass

    # tools: check if a position of mouse click  is in a rectangle
    def inArea(self, rect:pg.Rect, x:int, y:int):
        if (rect.x <= x <= rect.right and
            rect.y <= y <= rect.bottom):
            return True
        else:
            return False

    # tools: save user data -> abando
    """
    def saveUserData(self):
        with open(c.USERDATA_PATH, "w", encoding="utf-8") as f:
            userdata = {}
            for i in self.game_info:
                if i in c.INIT_USERDATA:
                    userdata[i] = self.game_info[i]
            data_to_save = json.dumps(userdata, sort_keys=True, indent=4)
            f.write(data_to_save)
"""
# main control 
class Control():
    def __init__(self):
        self.screen = pg.display.get_surface()
        self.done = False
        self.clock = pg.time.Clock()    # 创建一个对象来帮助跟踪时间
        self.keys = pg.key.get_pressed()
        self.mouse_pos = None
        self.mouse_click = [False, False]  # value:[left mouse click, right mouse click]
        self.current_time = 0.0
        self.state_dict = {}
        self.state_name = None
        self.state = None
        """ upload user data -> abandon this part
        try:
            # 存在存档即导入
            # 先自动修复读写权限(Python权限规则和Unix不一样，420表示unix的644，Windows自动忽略不支持项)
            os.chmod(c.USERDATA_PATH, 420)
            with open(c.USERDATA_PATH, encoding="utf-8") as f:
                userdata = json.load(f)
        except FileNotFoundError:
            self.setupUserData()
        except json.JSONDecodeError:
            logger.warning("用户存档解码错误！程序将新建初始存档！\n")
            self.setupUserData()
        else:   # 没有引发异常才执行
            self.game_info = {}
            # 导入数据，保证了可运行性，但是放弃了数据向后兼容性，即假如某些变量在以后改名，在导入时可能会被重置
            need_to_rewrite = False
            for key in c.INIT_USERDATA:
                if key in userdata:
                    self.game_info[key] = userdata[key]
                else:
                    self.game_info[key] = c.INIT_USERDATA[key]
                    need_to_rewrite = True
            if need_to_rewrite:
                with open(c.USERDATA_PATH, "w", encoding="utf-8") as f:
                    savedata = json.dumps(self.game_info, sort_keys=True, indent=4)
                    f.write(savedata)
                    """
        # establish game_info
        self.game_info = c.INIT_USERDATA.copy()
        self.game_info[c.CURRENT_TIME] = 0

        # setup fps
        self.fps = 50 * self.game_info[c.GAME_RATE]
    """ user data setup function -- abandoned
    def setupUserData(self):
        if not os.path.exists(os.path.dirname(c.USERDATA_PATH)):
            os.makedirs(os.path.dirname(c.USERDATA_PATH))
        with open(c.USERDATA_PATH, "w", encoding="utf-8") as f:
            savedata = json.dumps(c.INIT_USERDATA, sort_keys=True, indent=4)
            f.write(savedata)
        self.game_info = c.INIT_USERDATA.copy() # 内部全是不可变对象，浅拷贝即可
    """
    def setup_states(self, state_dict:dict, start_state):
        self.state_dict = state_dict
        self.state_name = start_state
        self.state = self.state_dict[self.state_name]
        self.state.startup(self.current_time, self.game_info)

    def update(self):
        # 自 pygame_init() 调用以来的毫秒数 * 游戏速度倍率，即游戏时间
        self.current_time = pg.time.get_ticks() * self.game_info[c.GAME_RATE]
        if self.state.done:
            self.flip_state()
            
        self.state.update(self.screen, self.current_time, self.mouse_pos, self.mouse_click)
        self.mouse_pos = None
        self.mouse_click[0] = False
        self.mouse_click[1] = False

    # changing state
    def flip_state(self):
        if self.state.next == c.EXIT:
            pg.quit()
            os._exit(0)
        self.state_name = self.state.next
        persist = self.state.cleanup()
        self.state = self.state_dict[self.state_name]
        self.state.startup(self.current_time, persist)

    def event_loop(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.done = True
            elif event.type == pg.KEYDOWN:
                self.keys = pg.key.get_pressed()
                if event.key == pg.K_f:
                    pg.display.set_mode(c.SCREEN_SIZE, pg.HWSURFACE|pg.FULLSCREEN)
                elif event.key == pg.K_u:
                    pg.display.set_mode(c.SCREEN_SIZE)
            elif event.type == pg.KEYUP:
                self.keys = pg.key.get_pressed()
            elif event.type == pg.MOUSEBUTTONDOWN:
                self.mouse_pos = pg.mouse.get_pos()
                self.mouse_click[0], _, self.mouse_click[1] = pg.mouse.get_pressed()
                # self.mouse_click[0]->left
                # self.mouse_click[1]->right
                #print(f"click position: ({self.mouse_pos[0]:3}, {self.mouse_pos[1]:3}) left and right click status: {self.mouse_click}")


    def run(self):
        while not self.done:
            self.event_loop()
            self.update()
            pg.display.update()
            self.clock.tick(self.fps)


"""------------------------------------------------------------------------"""
#below are some tools to load images
def get_image(  sheet:pg.Surface, x:int, y:int, width:int, height:int,
                colorkey:tuple[int]=c.BLACK, scale:int=1) -> pg.Surface:
        image = pg.Surface([width, height])
        rect = image.get_rect()

        image.blit(sheet, (0, 0), (x, y, width, height))
        if colorkey:
            image.set_colorkey(colorkey)
        image = pg.transform.scale(image,
                                   (int(rect.width*scale),
                                    int(rect.height*scale)))
        return image

def get_image_alpha(sheet:pg.Surface, x:int, y:int, width:int, height:int,
                    colorkey:tuple[int]=c.BLACK, scale:int=1) -> pg.Surface:
    image = pg.Surface([width, height], SRCALPHA)
    rect = image.get_rect()

    image.blit(sheet, (0, 0), (x, y, width, height))
    image.set_colorkey(colorkey)
    image = pg.transform.scale(image,
                                (int(rect.width*scale),
                                int(rect.height*scale)))
    return image  
        
def load_image_frames(  directory:str, image_name:str,
                        colorkey:tuple[int], accept:tuple[str]) -> list[pg.Surface]:
    frame_list = []
    tmp = {}
    # image_name is "Peashooter", pic name is "Peashooter_1", get the index 1
    index_start = len(image_name) + 1 
    frame_num = 0
    for pic in os.listdir(directory):
        name, ext = os.path.splitext(pic)
        if ext.lower() in accept:
            index = int(name[index_start:])
            img = pg.image.load(os.path.join(directory, pic))
            if img.get_alpha():
                img = img.convert_alpha()
            else:
                img = img.convert()
                img.set_colorkey(colorkey)
            tmp[index]= img
            frame_num += 1

    for i in range(frame_num):  
        frame_list.append(tmp[i])
    return frame_list

# colorkeys 是设置图像中的某个颜色值为透明,这里用来消除白边
def load_all_gfx(   directory:str, colorkey:tuple[int]=c.WHITE,
                    accept:tuple[str]=(".png", ".jpg", ".bmp", ".gif", ".webp")) -> dict[str:pg.Surface]:
    graphics = {}
    for name1 in os.listdir(directory):
        # subfolders under the folder resources\graphics
        dir1 = os.path.join(directory, name1)
        if os.path.isdir(dir1):
            for name2 in os.listdir(dir1):
                dir2 = os.path.join(dir1, name2)
                if os.path.isdir(dir2):
                # e.g. subfolders under the folder resources\graphics\Zombies
                    for name3 in os.listdir(dir2):
                        dir3 = os.path.join(dir2, name3)
                        # e.g. subfolders or pics under the folder resources\graphics\Zombies\ConeheadZombie
                        if os.path.isdir(dir3):
                            # e.g. it"s the folder resources\graphics\Zombies\ConeheadZombie\ConeheadZombieAttack
                            image_name, _ = os.path.splitext(name3)
                            graphics[image_name] = load_image_frames(dir3, image_name, colorkey, accept)
                        else:
                            # e.g. pics under the folder resources\graphics\Plants\Peashooter
                            image_name, _ = os.path.splitext(name2)
                            graphics[image_name] = load_image_frames(dir2, image_name, colorkey, accept)
                            break
                else:
                # e.g. pics under the folder resources\graphics\Screen
                    name, ext = os.path.splitext(name2)
                    if ext.lower() in accept:
                        img = pg.image.load(dir2)
                        if img.get_alpha():
                            img = img.convert_alpha()
                        else:
                            img = img.convert()
                            img.set_colorkey(colorkey)
                        graphics[name] = img
    return graphics

pg.display.set_caption(c.ORIGINAL_CAPTION)  
SCREEN = pg.display.set_mode(c.SCREEN_SIZE) 
if os.path.exists(c.ORIGINAL_LOGO):  
    pg.display.set_icon(pg.image.load(c.ORIGINAL_LOGO))

GFX = load_all_gfx(c.PATH_IMG_DIR)
#print (GFX)
