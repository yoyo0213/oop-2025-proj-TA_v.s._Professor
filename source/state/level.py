import os
import pygame as pg
import random
import logging
from .. import tool
from .. import constants as c
from ..component import map, plant, zombie, menubar
logger = logging.getLogger("main")

class Level(tool.State):
    def __init__(self):
        tool.State.__init__(self)
        self._logged_reset= False
        self._logged_first_wave = False
        self.start_time =0
        self.total_time =0
    def startup(self, current_time, persist):
        self.game_info = persist
        self.persist = self.game_info
        self.game_info[c.CURRENT_TIME] = current_time
        self.start_time = current_time
        # 暂停状态
        self.pause = False
        self.pause_time = 0

        # 默认显然不用显示菜单
        self.show_game_menu = False

        # 导入地图参数
        self.loadMap()
        self.map = map.Map(self.map_data[c.BACKGROUND_TYPE])
        self.map_x_len = self.map.width
        self.map_y_len = self.map.height
        self.setupBackground()
        self.initState()

    def loadMap(self):
        if self.game_info[c.GAME_MODE] == c.MODE_LITTLEGAME:
            if 0 <= self.game_info[c.LITTLEGAME_NUM] < map.TOTAL_LITTLE_GAME:
                self.map_data = map.LITTLE_GAME_MAP_DATA[self.game_info[c.LITTLEGAME_NUM]]
                pg.display.set_caption(f"{self.map_data[c.GAME_TITLE]}—survival mode ")
            else:
                self.game_info[c.LITTLEGAME_NUM] = 1
                self.map_data = map.LITTLE_GAME_MAP_DATA[self.game_info[c.LITTLEGAME_NUM]]
        self.has_shovel = self.map_data[c.SHOVEL]


    def setupBackground(self):
        img_index = self.map_data[c.BACKGROUND_TYPE]
        self.background_type = img_index
        self.background = tool.GFX[c.BACKGROUND_NAME][img_index]
        self.bg_rect = self.background.get_rect()

        self.level = pg.Surface((self.bg_rect.w, self.bg_rect.h)).convert()
        self.viewport = tool.SCREEN.get_rect(bottom=self.bg_rect.bottom)
        self.viewport.x += c.BACKGROUND_OFFSET_X


    def setupGroups(self):
        self.sun_group = pg.sprite.Group()
        self.head_group = pg.sprite.Group()

        # 改用列表生成器直接生成内容，不再在这里使用for循环
        self.plant_groups = [pg.sprite.Group() for i in range(self.map_y_len)]
        self.zombie_groups = [pg.sprite.Group() for i in range(self.map_y_len)]
        self.hypno_zombie_groups = [pg.sprite.Group() for i in range(self.map_y_len)] # 被魅惑的僵尸
        self.bullet_groups = [pg.sprite.Group() for i in range(self.map_y_len)]


    # 按照规则生成每一波僵尸
    # 将波刷新和一波中的僵尸生成分开
    # useableZombie是指可用的僵尸种类的元组
    # inevitableZombie指在本轮必然出现的僵尸，输入形式为字典: {波数1:(僵尸1, 僵尸2……), 波数2:(僵尸1, 僵尸2……)……}
    def createWaves(self, useable_zombies, num_flags, survival_rounds=0, inevitable_zombie_dict=None):

        waves = []

        self.num_flags = num_flags

        # 权重值，c.CREATE_ZOMBIE_DICT[zombie][1]即为对应的权重
        weights = [c.CREATE_ZOMBIE_DICT[zombie][1] for zombie in useable_zombies]

        # 按照原版pvz设计的僵尸容量函数，是从无尽解析的，但是普通关卡也可以遵循
        for wave in range(1, 10 * num_flags + 1):
            zombie_volume = int(int((wave + survival_rounds*20)*0.8)/2) + 1
            zombie_list = []

            # 大波僵尸情况
            if wave % 10 == 0:
                # 容量增大至2.5倍
                zombie_volume = int(zombie_volume*2.5)
                # 先生成旗帜僵尸
                zombie_list.append(c.FLAG_ZOMBIE)
                zombie_volume -= c.CREATE_ZOMBIE_DICT[c.FLAG_ZOMBIE][0]

            # 传送带模式应当增大僵尸容量
            if (self.bar_type != c.CHOOSEBAR_STATIC):
                zombie_volume += 2

            if inevitable_zombie_dict and (wave in inevitable_zombie_dict):
                for new_zombie in inevitable_zombie_dict[wave]:
                    zombie_list.append(new_zombie)
                    zombie_volume -= c.CREATE_ZOMBIE_DICT[new_zombie][0]
                if zombie_volume < 0:
                    logger.warning(f"第{wave}波中手动设置的僵尸级别总数超过上限！")

            # 防止因为僵尸最小等级过大，使得总容量无法完全利用，造成死循环的检查机制
            min_cost = c.CREATE_ZOMBIE_DICT[min(useable_zombies, key=lambda x:c.CREATE_ZOMBIE_DICT[x][0])][0]

            while (zombie_volume >= min_cost) and (len(zombie_list) < 50):
                new_zombie = random.choices(useable_zombies, weights)[0]
                # 普通僵尸、路障僵尸、铁桶僵尸有概率生成水中变种
                if self.background_type in c.POOL_EQUIPPED_BACKGROUNDS:
                    # 有泳池第一轮的第四波设定上生成水生僵尸
                    if survival_rounds == 0 and wave == 4:
                        if new_zombie in c.CONVERT_ZOMBIE_IN_POOL:
                            new_zombie = c.CONVERT_ZOMBIE_IN_POOL[new_zombie]
                    elif survival_rounds > 0 or wave > 4:
                        if random.randint(1, 3) == 1:  # 1/3概率水上，暂时人为设定
                            if new_zombie in c.CONVERT_ZOMBIE_IN_POOL:
                                new_zombie = c.CONVERT_ZOMBIE_IN_POOL[new_zombie]
                    # 首先几轮不出水生僵尸
                    elif new_zombie in c.WATER_ZOMBIE:
                        continue
                if c.CREATE_ZOMBIE_DICT[new_zombie][0] <= zombie_volume:
                    zombie_list.append(new_zombie)
                    zombie_volume -= c.CREATE_ZOMBIE_DICT[new_zombie][0]
            waves.append(zombie_list)

        self.waves = waves
        self.created_zombie_from_pool = False

    def refreshWaves(self, current_time, survival_rounds=0):
        """
        刷新波次；支援無盡生存模式：
        ─打完 NUM_FLAGS 面旗幟、場上殭屍清空 → 直接重開下一輪，
        並以 self.survival_rounds 逐輪遞增難度。
        """
        if (self.game_info[c.GAME_MODE] == c.MODE_LITTLEGAME and
            self.wave_num >= self.map_data[c.NUM_FLAGS] * 10):
            if any(len(g) for g in self.zombie_groups):
                return
            if not self._logged_reset:
                print("▶▶ [RESET TRIGGERED]",
                      "mode=", self.game_info[c.GAME_MODE],
                      "flags=", self.map_data[c.NUM_FLAGS],
                      "old_wave=", self.wave_num)
            self._logged_reset = False
            self._logged_reset=False
            self.survival_rounds += 1
            self.createWaves(
            useable_zombies=self.map_data[c.INCLUDED_ZOMBIES],
            num_flags=self.map_data[c.NUM_FLAGS],
            survival_rounds=self.survival_rounds
        )
        # now immediately queue the first wave of the new round
            self.wave_num     = 1
            self.wave_time    = current_time
            self.wave_zombies = self.waves[0]               # ← assign the new wave
            self.zombie_num   = len(self.wave_zombies)      # ← update count                  # ← (optional) play sound
            self.level_progress_zombie_head_image_rect.x = \
                self.level_progress_bar_image_rect.x + 75
            return
    # ------------------------------------------------------------
    # 以下皆為原本波次刷新邏輯（僅微調縮排與註解）
    # ------------------------------------------------------------
        if self.wave_num == 0:
            if self.wave_time == 0:
                self.wave_time = current_time
            else:
                delay = 18000 if survival_rounds == 0 and self.bar_type == c.CHOOSEBAR_STATIC else 6000
                if current_time - self.wave_time >= delay:
                    self.wave_num += 1
                    self.wave_time = current_time
                    if 0 <= self.wave_num - 1 < len(self.waves):
                        self.wave_zombies = self.waves[self.wave_num - 1]
                        self.zombie_num = len(self.wave_zombies)
            return

        if self.wave_num % 10 != 9:
            #delay = 25000 + random.randint(0, 6000)
            delay=100
            if self.bar_type == c.CHOOSEBAR_BOWLING:
                delay = 12500 + random.randint(0, 3000)
            if current_time - self.wave_time >= delay:
                self.wave_num += 1
                self.wave_time = current_time
                if 0 <= self.wave_num - 1 < len(self.waves):
                    self.wave_zombies = self.waves[self.wave_num - 1]
                    self.zombie_num = len(self.wave_zombies)
        else:
            #delay = 45000
            delay=200
            if self.bar_type != c.CHOOSEBAR_STATIC:
                delay = 25000
            if current_time - self.wave_time >= delay:
                self.wave_num += 1
                self.wave_time = current_time
                if 0 <= self.wave_num - 1 < len(self.waves):
                    self.wave_zombies = self.waves[self.wave_num - 1]
                    self.zombie_num = len(self.wave_zombies)
                    
            elif current_time - self.wave_time >= (delay - 2000):
                self.show_hugewave_approching_time = current_time

        zombie_nums = sum(len(g) for g in self.zombie_groups)
        if (self.zombie_num and zombie_nums / self.zombie_num < random.uniform(0.15, 0.25) and
            current_time - self.wave_time > 4000):
            if self.bar_type == c.CHOOSEBAR_STATIC:
                if current_time - 43000 < self.wave_time:
                    self.wave_time = current_time - 43000
            else:
                if current_time - 23000 < self.wave_time:
                    self.wave_time = current_time - 23000

    def setupCars(self):
        self.cars = []
        for i in range(self.map_y_len):
            y = self.map.getMapGridPos(0, i)[1]
            self.cars.append(plant.Car(-45, y+20, i))

    # 更新函数每帧被调用，将鼠标事件传入给状态处理函数
    def update(self, surface, current_time, mouse_pos, mouse_click):
        self.current_time = self.game_info[c.CURRENT_TIME] = self.gameTime(current_time)
        if self.state == c.CHOOSE:
            self.choose(mouse_pos, mouse_click)
        elif self.state == c.PLAY:
            self.play(mouse_pos, mouse_click)

        self.draw(surface)

    def gameTime(self, current_time):
        # 扣除暂停时间
        if not self.pause:
            self.before_pause_time = current_time - self.pause_time
        else:
            self.pause_time = current_time - self.before_pause_time
        return self.before_pause_time

    def initBowlingMap(self):
        for x in range(3, self.map_x_len):
            for y in range(self.map_y_len):
                self.map.setMapGridType(x, y, c.MAP_UNAVAILABLE) # 将坚果保龄球红线右侧设置为不可种植任何植物

    def initState(self):
        if c.CHOOSEBAR_TYPE in self.map_data:
            self.bar_type = self.map_data[c.CHOOSEBAR_TYPE]
        else:
            self.bar_type = c.CHOOSEBAR_STATIC

        if self.bar_type == c.CHOOSEBAR_STATIC:
            self.initChoose()
        else:
            card_pool = menubar.getCardPool(self.map_data[c.CARD_POOL])
            self.initPlay(card_pool)
            if self.bar_type == c.CHOOSEBAR_BOWLING:
                self.initBowlingMap()

        self.setupLittleMenu()

    def initChoose(self):
        self.state = c.CHOOSE
        self.panel = menubar.Panel(c.CARDS_TO_CHOOSE, self.map_data[c.INIT_SUN_NAME], self.background_type)


    def choose(self, mouse_pos, mouse_click):
        # 如果暂停
        if self.show_game_menu:
            self.pauseAndCheckMenuOptions(mouse_pos, mouse_click)
            return

        elif mouse_pos and mouse_click[0]:
            self.panel.checkCardClick(mouse_pos)
            if self.panel.checkStartButtonClick(mouse_pos):
                self.initPlay(self.panel.getSelectedCards())
            elif self.inArea(self.little_menu_rect, *mouse_pos):
                self.show_game_menu = True

    def initPlay(self, card_list):


        self.survival_rounds = 0
        self.state = c.PLAY
        if self.bar_type == c.CHOOSEBAR_STATIC:
            self.menubar = menubar.MenuBar(card_list, self.map_data[c.INIT_SUN_NAME])
        else:
            self.menubar = menubar.MoveBar(card_list)

        # 是否拖住植物或者铲子
        self.drag_plant = False
        self.drag_shovel = False

        self.hint_image = None
        self.hint_plant = False

        # 用种下植物的名称与位置元组判断是否需要刷新僵尸的攻击对象
        # 种植植物后应当刷新僵尸的攻击对象，当然，默认初始时不用刷新
        self.new_plant_and_positon = None

        if self.background_type in c.DAYTIME_BACKGROUNDS and self.bar_type == c.CHOOSEBAR_STATIC:
            self.produce_sun = True
            self.fallen_sun = 0 # 已掉落的阳光
        else:
            self.produce_sun = False
        self.sun_timer = self.current_time

        self.removeMouseImage()
        self.setupGroups()
        if self.map_data[c.SPAWN_ZOMBIES] == c.SPAWN_ZOMBIES_LIST:
            self.setupZombies()
        else:
            # 僵尸波数数据及僵尸生成数据
            self.wave_num = 0   # 还未出现僵尸时定义为0
            self.wave_time = 0
            self.wave_zombies = []
            self.zombie_num = 0

            # 暂时没有生存模式，所以 survival_rounds = 0
            if c.INEVITABLE_ZOMBIE_DICT in self.map_data:
                self.createWaves(   useable_zombies=self.map_data[c.INCLUDED_ZOMBIES],
                                    num_flags=self.map_data[c.NUM_FLAGS],
                                    survival_rounds=0,
                                    inevitable_zombie_dict=self.map_data[c.INEVITABLE_ZOMBIE_DICT])
            else:
                self.survival_rounds = 0
                self.createWaves(   useable_zombies=self.map_data[c.INCLUDED_ZOMBIES],
                                    num_flags=self.map_data[c.NUM_FLAGS],
                                    survival_rounds=self.survival_rounds)
        self.setupCars()

        # 地图有铲子才添加铲子
        if self.has_shovel:
            #  导入小铲子
            frame_rect = (0, 0, 71, 67)
            self.shovel = tool.get_image_alpha(tool.GFX[c.SHOVEL], *frame_rect, c.BLACK, 1.1)
            self.shovel_rect = self.shovel.get_rect()
            frame_rect = (0, 0, 77, 75)
            self.shovel_positon = (608, 1)
            self.shovel_box = tool.get_image_alpha(tool.GFX[c.SHOVEL_BOX], *frame_rect, c.BLACK, 1.1)
            self.shovel_box_rect = self.shovel_box.get_rect()
            self.shovel_rect.x = self.shovel_box_rect.x = self.shovel_positon[0]
            self.shovel_rect.y = self.shovel_box_rect.y = self.shovel_positon[1] 

        self.setupLevelProgressBarImage()

        self.setupHugeWaveApprochingImage()
        self.show_hugewave_approching_time = -2000 # 防止设置为0时刚刚打开游戏就已经启动红字

        if self.map_data[c.BACKGROUND_TYPE] == c.BACKGROUND_NIGHT:
            # 判断墓碑数量等级
            # 0为无墓碑，1为少量墓碑，2为中等量墓碑，3为大量墓碑
            if c.GRADE_GRAVES in self.map_data:
                grade_graves = self.map_data[c.GRADE_GRAVES]
            # 缺省为少量墓碑
            else:
                grade_graves = 1

            grave_volume = c.GRAVES_GRADE_INFO[grade_graves]
            self.grave_set = set()
            while len(self.grave_set) < grave_volume:
                map_x = random.randint(4, 8)    # 注意是从0开始编号
                map_y = random.randint(0, 4)
                self.grave_set.add((map_x, map_y))
            if self.grave_set:
                for i in self.grave_set:
                    map_x, map_y = i
                    posX, posY = self.map.getMapGridPos(map_x, map_y)
                    self.plant_groups[map_y].add(plant.Grave(posX, posY))
                    self.map.map[map_y][map_x][c.MAP_PLANT].add(c.GRAVE)
            self.grave_zombie_created = False
            self.new_grave_added = False


    # 小菜单
    def setupLittleMenu(self):
        # 具体运行游戏必定有个小菜单, 导入菜单和选项
        frame_rect = (0, 0, 108, 31)
        self.little_menu = tool.get_image_alpha(tool.GFX[c.LITTLE_MENU], *frame_rect, c.BLACK, 1.1)
        self.little_menu_rect = self.little_menu.get_rect()
        self.little_menu_rect.x = 690
        self.little_menu_rect.y = 0 

        # 弹出的菜单框
        frame_rect = (0, 0, 500, 500)
        self.big_menu = tool.get_image_alpha(tool.GFX[c.BIG_MENU], *frame_rect, c.BLACK, 1.1)
        self.big_menu_rect = self.big_menu.get_rect()
        self.big_menu_rect.x = 150
        self.big_menu_rect.y = 0

        # 返回按钮，用字体渲染实现，增强灵活性
        # 建立一个按钮大小的surface对象
        self.return_button = pg.Surface((376, 96))
        self.return_button.set_colorkey(c.BLACK)    # 避免多余区域显示成黑色
        self.return_button_rect = self.return_button.get_rect()
        self.return_button_rect.x = 220
        self.return_button_rect.y = 440
        font = pg.font.Font(c.FONT_PATH, 40)
        font.bold = True
        text = font.render("resume", True, c.YELLOWGREEN)
        text_rect = text.get_rect()
        text_rect.x = 105
        text_rect.y = 18
        self.return_button.blit(text, text_rect)

        # 重新开始按钮
        frame_rect = (0, 0, 207, 45)
        self.restart_button = tool.get_image_alpha(tool.GFX[c.RESTART_BUTTON], *frame_rect, c.BLACK, 1.1)
        self.restart_button_rect = self.restart_button.get_rect()
        self.restart_button_rect.x = 295
        self.restart_button_rect.y = 325

        # 主菜单按钮
        frame_rect = (0, 0, 206, 43)
        self.mainMenu_button = tool.get_image_alpha(tool.GFX[c.MAINMENU_BUTTON], *frame_rect, c.BLACK, 1.1)
        self.mainMenu_button_rect = self.mainMenu_button.get_rect()
        self.mainMenu_button_rect.x = 299
        self.mainMenu_button_rect.y = 372

       

    def pauseAndCheckMenuOptions(self, mouse_pos, mouse_click):
        # 设置暂停状态
        self.pause = True
        # 暂停播放音乐
        pg.mixer.music.pause()
        if mouse_click[0]:
            # 返回键
            if self.inArea(self.return_button_rect, *mouse_pos):
                # 终止暂停，停止显示菜单
                self.pause = False
                self.show_game_menu = False
                
            # 重新开始键
            elif self.inArea(self.restart_button_rect, *mouse_pos):
                self.done = True
                self.next = c.PLAY
                
            # 主菜单键
            elif self.inArea(self.mainMenu_button_rect, *mouse_pos):
                self.done = True
                self.next = c.MAIN_MENU
                self.persist = self.game_info
                self.persist[c.CURRENT_TIME] = 0
                


    # 一大波僵尸来袭图片显示
    def setupHugeWaveApprochingImage(self):
        frame_rect = (0, 0, 492, 80)
        self.huge_wave_approching_image = tool.get_image_alpha(tool.GFX[c.HUGE_WAVE_APPROCHING], *frame_rect, c.BLACK, 1)
        self.huge_wave_approching_image_rect = self.huge_wave_approching_image.get_rect()
        self.huge_wave_approching_image_rect.x = 140    # 猜的
        self.huge_wave_approching_image_rect.y = 250    # 猜的

    # 关卡进程显示设置
    def setupLevelProgressBarImage(self):
        # 注意：定位一律采用与主进度条的相对位置

        # 主进度条
        frame_rect = (0, 0, 158, 26)
        self.level_progress_bar_image = tool.get_image_alpha(tool.GFX[c.LEVEL_PROGRESS_BAR], *frame_rect, c.BLACK, 1)
        self.level_progress_bar_image_rect = self.level_progress_bar_image.get_rect()
        self.level_progress_bar_image_rect.x = 600
        self.level_progress_bar_image_rect.y = 574

        # 僵尸头
        frame_rect = (0, 0, 23, 25)
        self.level_progress_zombie_head_image = tool.get_image_alpha(tool.GFX[c.LEVEL_PROGRESS_ZOMBIE_HEAD], *frame_rect, c.BLACK, 1)
        self.level_progress_zombie_head_image_rect = self.level_progress_zombie_head_image.get_rect()
        self.level_progress_zombie_head_image_rect.x = self.level_progress_bar_image_rect.x + 75
        self.level_progress_zombie_head_image_rect.y = self.level_progress_bar_image_rect.y - 3

        # 旗帜（这里只包括最后一面）
        frame_rect = (0, 0, 20, 18)
        self.level_progress_flag = tool.get_image_alpha(tool.GFX[c.LEVEL_PROGRESS_FLAG], *frame_rect, c.BLACK, 1)
        self.level_progress_flag_rect = self.level_progress_flag.get_rect()
        self.level_progress_flag_rect.x = self.level_progress_bar_image_rect.x - 78
        self.level_progress_flag_rect.y = self.level_progress_bar_image_rect.y - 3

    # 用小铲子移除植物
    def shovelRemovePlant(self, mouse_pos):
        x, y = mouse_pos
        map_x, map_y = self.map.getMapIndex(x, y)
        if not self.map.isValid(map_x, map_y):
            return
        for i in self.plant_groups[map_y]:
            if (x >= i.rect.x and x <= i.rect.right and
                y >= i.rect.y and y <= i.rect.bottom):
                if i.name in c.NON_PLANT_OBJECTS:
                    continue
                if i.name in c.SKIP_ZOMBIE_COLLISION_CHECK_WHEN_WORKING:
                    if i.start_boom:
                        continue
                # 优先移除花盆、睡莲上的植物而非花盆、睡莲本身
                if len(self.map.map[map_y][map_x][c.MAP_PLANT]) >= 2:
                    if c.LILYPAD in self.map.map[map_y][map_x][c.MAP_PLANT]:
                        if i.name == c.LILYPAD:
                            continue
                    elif "花盆（未实现）" in self.map.map[map_y][map_x][c.MAP_PLANT]:
                        if i.name == "花盆（未实现）":
                            continue
                self.killPlant(i, shovel=True)
                # 使用后默认铲子复原
                self.drag_shovel = not self.drag_shovel
                self.removeMouseImagePlus()
                return

    def play(self, mouse_pos, mouse_click):
        # 如果暂停
        if self.show_game_menu:
            self.pauseAndCheckMenuOptions(mouse_pos, mouse_click)
            return

        if self.map_data[c.SPAWN_ZOMBIES] == c.SPAWN_ZOMBIES_LIST:
            # 旧僵尸生成方式
            if self.zombie_start_time == 0:
                self.zombie_start_time = self.current_time
            elif len(self.zombie_list) > 0:
                data = self.zombie_list[0]
                if data[0] <= (self.current_time - self.zombie_start_time):
                    self.createZombie(data[1], data[2])
                    self.zombie_list.remove(data)
        else:
            # 新僵尸生成方式
            self.refreshWaves(self.current_time)
            if self.wave_zombies and self.wave_num > 0:  # 仅在 wave_num > 0 时生成殭屍
                print(f"[SPAWN WAVE] flag={(self.wave_num-1)//10+1} "
              f"wave={self.wave_num} "
              f"count={len(self.wave_zombies)}")
                for i in self.wave_zombies:
                    self.createZombie(i)
                self.wave_zombies = []  # 生成後清空，避免重複生成

        for i in range(self.map_y_len):
            self.bullet_groups[i].update(self.game_info)
            self.plant_groups[i].update(self.game_info)
            self.zombie_groups[i].update(self.game_info)
            self.hypno_zombie_groups[i].update(self.game_info)
            for zombie in self.hypno_zombie_groups[i]:
                if zombie.rect.x > c.SCREEN_WIDTH:
                    zombie.kill()

        self.head_group.update(self.game_info)
        self.sun_group.update(self.game_info)
        
        if self.produce_sun:
            if (self.current_time - self.sun_timer) > min(c.PRODUCE_SUN_INTERVAL + 100*self.fallen_sun, 9500) + random.randint(0, 2750):
                self.sun_timer = self.current_time
                map_x, map_y = self.map.getRandomMapIndex()
                x, y = self.map.getMapGridPos(map_x, map_y)
                self.sun_group.add(plant.Sun(x, 0, x, y))
                self.fallen_sun += 1

        clicked_sun = False
        clicked_cards_or_map = False
        if not self.drag_plant and not self.drag_shovel and mouse_pos and mouse_click[0]:
            for sun in self.sun_group:
                if sun.checkCollision(*mouse_pos):
                    self.menubar.increaseSunValue(sun.sun_value)
                    clicked_sun = True
                    

        # 拖动植物或者铲子
        if not self.drag_plant and mouse_pos and mouse_click[0] and not clicked_sun:
            self.click_result = self.menubar.checkCardClick(mouse_pos)
            if self.click_result:
                self.setupMouseImage(self.click_result[0], self.click_result[1])
                self.click_result[1].clicked = True
                clicked_cards_or_map = True
                
        elif self.drag_plant:
            if mouse_click[1]:
                self.removeMouseImage()
                clicked_cards_or_map = True
                self.click_result[1].clicked = False
            elif mouse_click[0]:
                if self.menubar.checkMenuBarClick(mouse_pos):
                    self.click_result[1].clicked = False
                    self.removeMouseImage()
                else:
                    self.addPlant()
            elif mouse_pos is None:
                self.setupHintImage()
        elif self.drag_shovel:
            if mouse_click[1]:
                self.removeMouseImagePlus()

        # 检查是否点击菜单
        if mouse_click[0] and (not clicked_sun) and (not clicked_cards_or_map):
            if self.inArea(self.little_menu_rect, *mouse_pos):
                self.show_game_menu = True
            elif self.has_shovel:
                if self.inArea(self.shovel_box_rect, *mouse_pos):
                    self.drag_shovel = not self.drag_shovel
                    if not self.drag_shovel:
                        self.removeMouseImagePlus()
                elif self.drag_shovel:
                    self.shovelRemovePlant(mouse_pos)

        for car in self.cars:
            if car:
                car.update(self.game_info)

        self.menubar.update(self.current_time)

        # 检查碰撞
        self.checkBulletCollisions()
        self.checkZombieCollisions()
        self.checkPlants()
        self.checkCarCollisions()
        self.checkGameState()


    def createZombie(self, name, map_y=None):
        # 有指定时按照指定生成，无指定时随机位置生成
        # 0:白天 1:夜晚 2:泳池 3:浓雾 4:屋顶 5:月夜 6:坚果保龄球
        if map_y == None:
            # 情况复杂：分水路和陆路，不能简单实现，需要另外加判断
            # 0, 1, 4, 5路为陆路，2, 3路为水路
            if self.map_data[c.BACKGROUND_TYPE] in c.POOL_EQUIPPED_BACKGROUNDS:
                if name in c.WATER_ZOMBIE:
                    map_y = random.randint(2, 3)
                elif name == "这里应该换成气球僵尸的名字（最好写调用的变量名，最好不要直接写，保持风格统一）":
                    map_y = random.randint(0, 5)
                else:   # 陆生僵尸
                    map_y = random.randint(0, 3)
                    if map_y >= 2:   # 后两路的map_y应当+2
                        map_y += 2
            elif self.map_data[c.BACKGROUND_TYPE] == c.BACKGROUND_SINGLE:
                map_y = 2
            elif self.map_data[c.BACKGROUND_TYPE] == c.BACKGROUND_TRIPLE:
                map_y = random.randint(1, 3)
            else:
                map_y = random.randint(0, 4)

        if self.map_data[c.SPAWN_ZOMBIES] == c.SPAWN_ZOMBIES_AUTO:
            # 旗帜波出生点右移
            if self.wave_num % 10:
                huge_wave_move = 0
            else:
                huge_wave_move = 40
        else:
            huge_wave_move = 0
        x, y = self.map.getMapGridPos(0, map_y)

        # 新增的僵尸也需要在这里声明
        match name:
            case c.NORMAL_ZOMBIE:
                self.zombie_groups[map_y].add(zombie.NormalZombie(c.ZOMBIE_START_X + random.randint(-20, 20) + huge_wave_move, y, self.head_group))
            case c.CONEHEAD_ZOMBIE:
                self.zombie_groups[map_y].add(zombie.ConeHeadZombie(c.ZOMBIE_START_X + random.randint(-20, 20) + huge_wave_move, y, self.head_group))
            case c.BUCKETHEAD_ZOMBIE:
                self.zombie_groups[map_y].add(zombie.BucketHeadZombie(c.ZOMBIE_START_X + random.randint(-20, 20) + huge_wave_move, y, self.head_group))
            case c.FLAG_ZOMBIE:
                self.zombie_groups[map_y].add(zombie.FlagZombie(c.ZOMBIE_START_X, y, self.head_group))
            case c.NEWSPAPER_ZOMBIE:
                self.zombie_groups[map_y].add(zombie.NewspaperZombie(c.ZOMBIE_START_X + random.randint(-20, 20) + huge_wave_move, y, self.head_group))
            case c.FOOTBALL_ZOMBIE:
                self.zombie_groups[map_y].add(zombie.FootballZombie(c.ZOMBIE_START_X + random.randint(-20, 20) + huge_wave_move, y, self.head_group))
            case c.DUCKY_TUBE_ZOMBIE:
                self.zombie_groups[map_y].add(zombie.DuckyTubeZombie(c.ZOMBIE_START_X + random.randint(-20, 20) + huge_wave_move, y, self.head_group))
            case c.CONEHEAD_DUCKY_TUBE_ZOMBIE:
                self.zombie_groups[map_y].add(zombie.ConeHeadDuckyTubeZombie(c.ZOMBIE_START_X + random.randint(-20, 20) + huge_wave_move, y, self.head_group))
            case c.BUCKETHEAD_DUCKY_TUBE_ZOMBIE:
                self.zombie_groups[map_y].add(zombie.BucketHeadDuckyTubeZombie(c.ZOMBIE_START_X + random.randint(-20, 20) + huge_wave_move, y, self.head_group))
            case c.SCREEN_DOOR_ZOMBIE:
                self.zombie_groups[map_y].add(zombie.ScreenDoorZombie(c.ZOMBIE_START_X + random.randint(-20, 20) + huge_wave_move, y, self.head_group))
            case c.POLE_VAULTING_ZOMBIE:
                # 本来撑杆跳生成位置不同，对齐左端可认为修正了一部分（看作移动了70），只需要相对修改即可
                self.zombie_groups[map_y].add(zombie.PoleVaultingZombie(c.ZOMBIE_START_X + random.randint(0, 10) + huge_wave_move, y, self.head_group))
            case c.ZOMBONI:
                # 冰车僵尸生成位置不同
                self.zombie_groups[map_y].add(zombie.Zomboni(c.ZOMBIE_START_X + random.randint(0, 10) + huge_wave_move, y, self.plant_groups[map_y], self.map, plant.IceFrozenPlot))
            case c.SNORKELZOMBIE:
                # 潜水僵尸生成位置不同
                self.zombie_groups[map_y].add(zombie.SnorkelZombie(c.ZOMBIE_START_X + random.randint(0, 10) + huge_wave_move, y, self.head_group))

    # 能否种植物的判断：
    # 先判断位置是否合法 isValid(map_x, map_y)
    # 再判断位置是否可用 isMovable(map_x, map_y)
    def canSeedPlant(self, plant_name):
        x, y = pg.mouse.get_pos()
        return self.map.checkPlantToSeed(x, y, plant_name)

    # 种植物
    def addPlant(self):
        pos = self.canSeedPlant(self.plant_name)
        if pos is None:
            return

        # 恢复植物卡片样式
        self.click_result[1].clicked = False

        if self.hint_image is None:
            self.setupHintImage()
        x, y = self.hint_rect.centerx, self.hint_rect.bottom
        map_x, map_y = self.map.getMapIndex(x, y)

        # 新植物也需要在这里声明
        match self.plant_name:
            case c.SUNFLOWER:
                new_plant = plant.SunFlower(x, y, self.sun_group)
            case c.PEASHOOTER:
                new_plant = plant.PeaShooter(x, y, self.bullet_groups[map_y])
            case c.SNOWPEASHOOTER:
                new_plant = plant.SnowPeaShooter(x, y, self.bullet_groups[map_y])
            case c.WALLNUT:
                new_plant = plant.WallNut(x, y)
            case c.CHERRYBOMB:
                new_plant = plant.CherryBomb(x, y)
            case c.THREEPEASHOOTER:
                new_plant = plant.ThreePeaShooter(x, y, self.bullet_groups, map_y, self.map.background_type)
            case c.REPEATERPEA:
                new_plant = plant.RepeaterPea(x, y, self.bullet_groups[map_y])
            case c.CHOMPER:
                new_plant = plant.Chomper(x, y)
            case c.PUFFSHROOM:
                new_plant = plant.PuffShroom(x, y, self.bullet_groups[map_y])
            case c.POTATOMINE:
                new_plant = plant.PotatoMine(x, y)
            case c.SQUASH:
                new_plant = plant.Squash(x, y, self.map.map[map_y][map_x][c.MAP_PLANT])
            case c.SPIKEWEED:
                new_plant = plant.Spikeweed(x, y)
            case c.JALAPENO:
                new_plant = plant.Jalapeno(x, y)
            case c.SCAREDYSHROOM:
                new_plant = plant.ScaredyShroom(x, y, self.bullet_groups[map_y])
            case c.SUNSHROOM:
                new_plant = plant.SunShroom(x, y, self.sun_group)
            case c.ICESHROOM:
                new_plant = plant.IceShroom(x, y)
            case c.HYPNOSHROOM:
                new_plant = plant.HypnoShroom(x, y)
            case c.WALLNUTBOWLING:
                new_plant = plant.WallNutBowling(x, y, map_y, self)
            case c.REDWALLNUTBOWLING:
                new_plant = plant.RedWallNutBowling(x, y)
            case c.LILYPAD:
                new_plant = plant.LilyPad(x, y)
            case c.TORCHWOOD:
                new_plant = plant.TorchWood(x, y, self.bullet_groups[map_y])
            case c.STARFRUIT:
                new_plant = plant.StarFruit(x, y, self.bullet_groups[map_y], self)
            case c.COFFEEBEAN:
                new_plant = plant.CoffeeBean(x, y, self.plant_groups[map_y], self.map.map[map_y][map_x], self.map, map_x)
            case c.SEASHROOM:
                new_plant = plant.SeaShroom(x, y, self.bullet_groups[map_y])
            case c.TALLNUT:
                new_plant = plant.TallNut(x, y)
            case c.TANGLEKLEP:
                new_plant = plant.TangleKlep(x, y)
            case c.DOOMSHROOM:
                if self.map.grid_height_size == c.GRID_Y_SIZE:
                    new_plant = plant.DoomShroom(x, y, self.map.map[map_y][map_x][c.MAP_PLANT], explode_y_range=2)
                else:
                    new_plant = plant.DoomShroom(x, y, self.map.map[map_y][map_x][c.MAP_PLANT], explode_y_range=3)
            case c.GRAVEBUSTER:
                new_plant = plant.GraveBuster(x, y, self.plant_groups[map_y], self.map, map_x)
            case c.FUMESHROOM:
                new_plant = plant.FumeShroom(x, y, self.bullet_groups[map_y], self.zombie_groups[map_y])
            case c.GARLIC:
                new_plant = plant.Garlic(x, y)
            case c.PUMPKINHEAD:
                new_plant = plant.PumpkinHead(x, y)
            case c.GIANTWALLNUT:
                new_plant = plant.GiantWallNut(x, y)


        if ((new_plant.name in c.CAN_SLEEP_PLANTS)
        and (self.background_type in c.DAYTIME_BACKGROUNDS)):
            new_plant.setSleep()
            mushroom_sleep = True
        else:
            mushroom_sleep = False
        self.plant_groups[map_y].add(new_plant)
        # 种植植物后应当刷新僵尸的攻击对象
        # 用元组表示植物的名称和格子坐标
        self.new_plant_and_positon = (new_plant.name, (map_x, map_y))
        if self.bar_type == c.CHOOSEBAR_STATIC:
            self.menubar.decreaseSunValue(self.select_plant.sun_cost)
            self.menubar.setCardFrozenTime(self.plant_name)
        else:
            self.menubar.deleateCard(self.select_plant)

        if self.bar_type != c.CHOOSEBAR_BOWLING:    # 坚果保龄球关卡无需考虑格子被占用的情况
            self.map.addMapPlant(map_x, map_y, self.plant_name, sleep=mushroom_sleep)
        self.removeMouseImage()

        # print(self.new_plant_and_positon)

        # 播放种植音效
        

    def setupHintImage(self):
        pos = self.canSeedPlant(self.plant_name)
        if pos and self.mouse_image:
            if (self.hint_image and pos[0] == self.hint_rect.x and
                pos[1] == self.hint_rect.y):
                return
            width, height = self.mouse_rect.w, self.mouse_rect.h
            image = pg.Surface([width, height])
            image.blit(self.mouse_image, (0, 0), (0, 0, width, height))
            image.set_colorkey(c.BLACK)
            image.set_alpha(128)
            self.hint_image = image
            self.hint_rect = image.get_rect()
            # 花盆、睡莲图片应当下移一些
            if self.plant_name in {c.LILYPAD, "花盆（未实现）", c.TANGLEKLEP}:
                self.hint_rect.centerx = pos[0]
                self.hint_rect.bottom = pos[1] + 25
            else:
                self.hint_rect.centerx = pos[0]
                self.hint_rect.bottom = pos[1]
            self.hint_plant = True
        else:
            self.hint_plant = False

    def setupMouseImage(self, plant_name, select_plant, colorkey=c.BLACK):
        frame_list = tool.GFX[plant_name]
        if plant_name in c.PLANT_RECT:
            data = c.PLANT_RECT[plant_name]
            x, y, width, height = data["x"], data["y"], data["width"], data["height"]
        else:
            x, y = 0, 0
            rect = frame_list[0].get_rect()
            width, height = rect.w, rect.h

        self.mouse_image = tool.get_image(frame_list[0], x, y, width, height, colorkey, 1)
        self.mouse_rect = self.mouse_image.get_rect()
        self.drag_plant = True
        self.plant_name = plant_name
        self.select_plant = select_plant

    def removeMouseImage(self):
        self.drag_plant = False
        self.mouse_image = None
        self.hint_image = None
        self.hint_plant = False

    def removeMouseImagePlus(self):
        self.drag_shovel = False
        self.shovel_rect.x = self.shovel_positon[0]
        self.shovel_rect.y = self.shovel_positon[1]

    def checkBulletCollisions(self):
        for i in range(self.map_y_len):
            for bullet in self.bullet_groups[i]:
                if bullet.name == c.FUME:
                    continue
                collided_func = pg.sprite.collide_mask
                if bullet.state == c.FLY:
                    # 利用循环而非内建精灵组碰撞判断函数，处理更加灵活，可排除已死亡僵尸
                    for zombie in self.zombie_groups[i]:
                        if (zombie.name == c.SNORKELZOMBIE) and (zombie.frames == zombie.swim_frames):
                            continue
                        if collided_func(zombie, bullet):
                            if zombie.state != c.DIE:
                                zombie.setDamage(bullet.damage, effect=bullet.effect, damage_type=bullet.damage_type)
                                bullet.setExplode()
                                # 火球有溅射伤害
                                if bullet.name == c.BULLET_FIREBALL:
                                    for rangeZombie in self.zombie_groups[i]:
                                        if abs(rangeZombie.rect.x - bullet.rect.x) <= (c.GRID_X_SIZE // 2):
                                            rangeZombie.setDamage(c.BULLET_DAMAGE_FIREBALL_RANGE, effect=None, damage_type=c.ZOMBIE_DEAFULT_DAMAGE)
                                break


    def checkZombieCollisions(self):
        for i in range(self.map_y_len):
            for zombie in self.zombie_groups[i]:
                if zombie.name == c.ZOMBONI:
                    continue
                if zombie.name in {c.POLE_VAULTING_ZOMBIE} and (not zombie.jumped):
                    collided_func = pg.sprite.collide_rect_ratio(0.6)
                else:
                    collided_func = pg.sprite.collide_mask
                if zombie.state != c.WALK:
                    # 非啃咬时不用刷新
                    if zombie.state != c.ATTACK:
                        continue
                    # 没有新的植物种下时不用刷新
                    if not self.new_plant_and_positon:
                        continue
                    # 被攻击对象是植物时才可能刷新
                    if zombie.prey_is_plant:
                        # 新植物种在被攻击植物同一格时才可能刷新
                        if (zombie.prey_map_x, zombie.prey_map_y) == self.new_plant_and_positon[1]:
                            # 如果被攻击植物是睡莲和花盆，同一格种了植物必然刷新
                            # 如果被攻击植物不是睡莲和花盆，同一格种了南瓜头才刷新
                            if ((zombie.prey.name not in {c.LILYPAD, "花盆（未实现）"})
                            and (self.new_plant_and_positon[0] != c.PUMPKINHEAD)):
                                continue
                        else:
                            continue
                    else:
                        continue
                if zombie.can_swim and (not zombie.swimming):
                    continue
                
                # 以下代码为了实现各个功能，较为凌乱
                attackable_common_plants = []
                attackable_backup_plants = []
                # 利用更加精细的循环判断啃咬优先顺序
                for plant in self.plant_groups[i]:
                    if collided_func(plant, zombie):
                        # 优先攻击南瓜头
                        if plant.name == c.PUMPKINHEAD:
                            target_plant = plant
                            break
                        # 衬底植物情形
                        elif plant.name in {c.LILYPAD, "花盆（未实现）"}:
                            attackable_backup_plants.append(plant)
                        # 一般植物情形
                        # 同时也忽略了不可啃食对象
                        elif plant.name not in c.CAN_SKIP_ZOMBIE_COLLISION_CHECK:
                            attackable_common_plants.append(plant)
                        # 在生效状态下忽略啃食碰撞但其他状况下不能忽略的情形
                        elif plant.name in c.SKIP_ZOMBIE_COLLISION_CHECK_WHEN_WORKING:
                            if not plant.start_boom:
                                attackable_common_plants.append(plant)
                else:
                    if attackable_common_plants:
                        # 默认为最右侧的一个植物
                        target_plant = max(attackable_common_plants, key=lambda i: i.rect.x)
                        map_x, map_y = self.map.getMapIndex(target_plant.rect.centerx, target_plant.rect.centery)
                        if self.map.isValid(map_x, map_y):
                            if c.PUMPKINHEAD in self.map.map[map_y][map_x][c.MAP_PLANT]:
                                for actual_target_plant in self.plant_groups[i]:
                                    # 检测同一格的其他植物
                                    if self.map.getMapIndex(actual_target_plant.rect.centerx, actual_target_plant.rect.bottom) == (map_x, map_y):
                                        if actual_target_plant.name == c.PUMPKINHEAD:
                                            target_plant = actual_target_plant
                                            break
                    elif attackable_backup_plants:
                        target_plant = max(attackable_backup_plants, key=lambda i: i.rect.x)
                        map_x, map_y = self.map.getMapIndex(target_plant.rect.centerx, target_plant.rect.centery)
                        if len(self.map.map[map_y][map_x][c.MAP_PLANT]) >= 2:
                            for actual_target_plant in self.plant_groups[i]:
                                # 检测同一格的其他植物
                                if self.map.getMapIndex(actual_target_plant.rect.centerx, actual_target_plant.rect.bottom) == (map_x, map_y):
                                    if actual_target_plant.name == c.PUMPKINHEAD:
                                        target_plant = actual_target_plant
                                        break
                                    elif actual_target_plant.name not in {c.LILYPAD, "花盆（未实现）"}:
                                        attackable_common_plants.append(actual_target_plant)
                            else:
                                if attackable_common_plants:
                                    target_plant = attackable_common_plants[-1]
                    else:
                        target_plant = None

                if target_plant:
                    zombie.prey_map_x, zombie.prey_map_y = self.map.getMapIndex(target_plant.rect.centerx, target_plant.rect.centery)
                    # 撑杆跳的特殊情况
                    if zombie.name in {c.POLE_VAULTING_ZOMBIE} and (not zombie.jumped):
                        if target_plant.name == c.GIANTWALLNUT:
                            zombie.health = 0
                            
                        elif not zombie.jumping:
                            zombie.jump_map_x = min(self.map_x_len - 1, zombie.prey_map_x)
                            zombie.jump_map_y = min(self.map_y_len - 1, zombie.prey_map_y)
                            jump_x = target_plant.rect.x - c.GRID_X_SIZE * 0.6
                            if c.TALLNUT in self.map.map[zombie.jump_map_y][zombie.jump_map_x][c.MAP_PLANT]:
                                zombie.setJump(False, jump_x)
                            else:
                                zombie.setJump(True, jump_x)
                        else:
                            if c.TALLNUT in self.map.map[zombie.jump_map_y][zombie.jump_map_x][c.MAP_PLANT]:
                                zombie.setJump(False, zombie.jump_x)
                            else:
                                zombie.setJump(True, zombie.jump_x)
                        continue

                    if target_plant.name == c.WALLNUTBOWLING:
                        if target_plant.canHit(i):
                            # target_plant.vel_y不为0，有纵向速度，表明已经发生过碰撞，对铁门秒杀（这里实现为忽略二类防具攻击）
                            if target_plant.vel_y and zombie.name == c.SCREEN_DOOR_ZOMBIE:
                                zombie.setDamage(c.WALLNUT_BOWLING_DAMAGE, damage_type=c.ZOMBIE_COMMON_DAMAGE)
                            else:
                                zombie.setDamage(c.WALLNUT_BOWLING_DAMAGE, damage_type=c.ZOMBIE_WALLNUT_BOWLING_DANMAGE)
                            target_plant.changeDirection(i)
                            
                    elif target_plant.name == c.REDWALLNUTBOWLING:
                        if target_plant.state == c.IDLE:
                            target_plant.setAttack()
                    elif target_plant.name == c.GIANTWALLNUT:
                        zombie.health = 0
                        
                    elif zombie.target_y_change:
                        # 大蒜作用正在生效的僵尸不进行传递
                        continue
                    elif target_plant.name == c.GARLIC:
                        zombie.setAttack(target_plant)
                        # 向吃过大蒜的僵尸传入level
                        zombie.level = self
                        zombie.to_change_group = True
                        zombie.map_y = i
                        if i == 0:
                            _move = 1
                        elif i == self.map_y_len - 1:
                            _move = -1
                        else:
                            _move = random.randint(0, 1)*2 - 1
                            if self.map.map[i][0][c.MAP_PLOT_TYPE] != self.map.map[i + _move][0][c.MAP_PLOT_TYPE]:
                                _move = -(_move)
                        zombie.target_map_y = i + _move
                        zombie.target_y_change = _move * self.map.grid_height_size
                    else:
                        zombie.setAttack(target_plant)

            for hypno_zombie in self.hypno_zombie_groups[i]:
                if hypno_zombie.health <= 0:
                    continue
                collided_func = pg.sprite.collide_mask
                zombie_list = pg.sprite.spritecollide(  hypno_zombie, self.zombie_groups[i],
                                                        False, collided_func)
                for zombie in zombie_list:
                    if zombie.state == c.DIE:
                        continue
                    # 正常僵尸攻击被魅惑的僵尸
                    if zombie.state == c.WALK:
                        zombie.setAttack(hypno_zombie, False)
                    # 被魅惑的僵尸攻击正常僵尸
                    if hypno_zombie.state == c.WALK:
                        hypno_zombie.setAttack(zombie, False)

        else:
            self.new_plant_and_positon = None    # 生效后需要解除刷新设置

    def checkCarCollisions(self):
        for i in range(len(self.cars)):
            if self.cars[i]:
                for zombie in self.zombie_groups[i]:
                    if (zombie and zombie.state != c.DIE and (not zombie.losthead)
                    and (pg.sprite.collide_mask(zombie, self.cars[i]))):
                        self.cars[i].setWalk()
                    if (pg.sprite.collide_mask(zombie, self.cars[i]) or
                    self.cars[i].rect.x <= zombie.rect.right <= self.cars[i].rect.right):
                        zombie.health = 0
                if self.cars[i].dead:
                    self.cars[i] = None

    def boomZombies(self, x, map_y, y_range, x_range, effect=None):
        for i in range(self.map_y_len):
            if abs(i - map_y) > y_range:
                continue
            for zombie in self.zombie_groups[i]:
                if ((abs(zombie.rect.centerx - x) <= x_range) or
                    ((zombie.rect.right - (x-x_range) > 20) or (zombie.rect.right - (x-x_range))/zombie.rect.width > 0.2, ((x+x_range) - zombie.rect.left > 20) or ((x+x_range) - zombie.rect.left)/zombie.rect.width > 0.2)[zombie.rect.x > x]):  # 这代码不太好懂，后面是一个判断僵尸在左还是在右，前面是一个元组，[0]是在左边的情况，[1]是在右边的情况
                    if effect == c.BULLET_EFFECT_UNICE:
                        zombie.ice_slow_ratio = 1
                    zombie.setDamage(1800, damage_type=c.ZOMBIE_ASH_DAMAGE)
                    if zombie.health <= 0:
                        zombie.setBoomDie()

    def freezeZombies(self, plant):

        for i in range(self.map_y_len):
            for zombie in self.zombie_groups[i]:
                zombie.setFreeze(plant.trap_frames[0])
                zombie.setDamage(20, damage_type=c.ZOMBIE_RANGE_DAMAGE)    # 寒冰菇还有全场20的伤害

    def killPlant(self, target_plant, shovel=False):
        x, y = target_plant.getPosition()
        map_x, map_y = self.map.getMapIndex(x, y)

        # 用铲子铲不用触发植物功能
        if not shovel:
            if target_plant.name == c.HYPNOSHROOM and target_plant.state != c.SLEEP:
                if target_plant.zombie_to_hypno:
                    zombie = target_plant.zombie_to_hypno
                    zombie.setHypno()
                    self.zombie_groups[map_y].remove(zombie)
                    self.hypno_zombie_groups[map_y].add(zombie)
            # 对于墓碑：移除存储在墓碑集合中的坐标
            # 注意这里是在描述墓碑而非墓碑吞噬者
            elif target_plant.name == c.GRAVE:
                self.grave_set.remove((map_x, map_y))
            elif ((target_plant.name in {    c.DOOMSHROOM, c.ICESHROOM,
                                            c.POTATOMINE, })
                and (target_plant.boomed)):
                # 毁灭菇的情况：爆炸时为了防止蘑菇云被坑掩盖没有加入坑，这里毁灭菇死亡（即爆炸动画结束）后再加入
                if target_plant.name == c.DOOMSHROOM:
                    self.plant_groups[map_y].add(plant.Hole(target_plant.original_x, target_plant.original_y, self.map.map[map_y][map_x][c.MAP_PLOT_TYPE]))
            elif target_plant.name not in c.PLANT_DIE_SOUND_EXCEPTIONS:
                pass
        else:
            pass

        # 整理地图信息
        if self.bar_type != c.CHOOSEBAR_BOWLING:
            self.map.removeMapPlant(map_x, map_y, target_plant.name)
        # 将睡眠植物移除后更新睡眠状态
        if target_plant.state == c.SLEEP:
            self.map.map[map_y][map_x][c.MAP_SLEEP] = False

        # 避免僵尸在用铲子移除植物后还在原位啃食
        target_plant.health = 0
        target_plant.kill()

    def checkPlant(self, target_plant, i):
        zombie_len = len(self.zombie_groups[i])
        # 不用检查攻击状况的情况
        if not target_plant.attack_check:
            pass
        elif target_plant.name == c.THREEPEASHOOTER:
            if target_plant.state == c.IDLE:
                if zombie_len > 0:
                    target_plant.setAttack()
                elif (i-1) >= 0 and len(self.zombie_groups[i-1]) > 0:
                    target_plant.setAttack()
                elif (i+1) < self.map_y_len and len(self.zombie_groups[i+1]) > 0:
                    target_plant.setAttack()
            elif target_plant.state == c.ATTACK:
                if zombie_len > 0:
                    pass
                elif (i-1) >= 0 and len(self.zombie_groups[i-1]) > 0:
                    pass
                elif (i+1) < self.map_y_len and len(self.zombie_groups[i+1]) > 0:
                    pass
                else:
                    target_plant.setIdle()
        elif target_plant.name == c.CHOMPER:
            for zombie in self.zombie_groups[i]:
                if target_plant.canAttack(zombie):
                    target_plant.setAttack(zombie, self.zombie_groups[i])
                    break
        elif target_plant.name == c.POTATOMINE:
            for zombie in self.zombie_groups[i]:
                if target_plant.canAttack(zombie):
                    target_plant.setAttack()
                    break
            if target_plant.start_boom and (not target_plant.boomed):
                for zombie in self.zombie_groups[i]:
                    # 双判断：发生碰撞或在攻击范围内
                    if ((pg.sprite.collide_mask(zombie, target_plant)) or
                        (abs(zombie.rect.centerx - target_plant.rect.centerx) <= target_plant.explode_x_range)):
                        zombie.setDamage(1800, damage_type=c.ZOMBIE_RANGE_DAMAGE)
                target_plant.boomed = True
        elif target_plant.name == c.SQUASH:
            for zombie in self.zombie_groups[i]:
                if target_plant.canAttack(zombie):
                    target_plant.setAttack(zombie, self.zombie_groups[i])
                    break
        elif target_plant.name == c.SPIKEWEED:
            can_attack = False
            for zombie in self.zombie_groups[i]:
                if target_plant.canAttack(zombie):
                    can_attack = True
                    break
            if target_plant.state == c.IDLE and can_attack:
                target_plant.setAttack(self.zombie_groups[i])
            elif target_plant.state == c.ATTACK and not can_attack:
                target_plant.setIdle()
        elif target_plant.name == c.SCAREDYSHROOM:
            need_cry = False
            can_attack = False
            for zombie in self.zombie_groups[i]:
                if target_plant.needCry(zombie):
                    need_cry = True
                    break
                elif target_plant.canAttack(zombie):
                    can_attack = True
            if need_cry:
                if target_plant.state != c.CRY:
                    target_plant.setCry()
            elif can_attack:
                if target_plant.state != c.ATTACK:
                    target_plant.setAttack()
            elif target_plant.state != c.IDLE:
                target_plant.setIdle()
        elif target_plant.name == c.STARFRUIT:
            can_attack = False
            for zombie_group in self.zombie_groups: # 遍历循环所有僵尸
                for zombie in zombie_group:
                    if target_plant.canAttack(zombie):
                        can_attack = True
                        break
            if target_plant.state == c.IDLE and can_attack:
                target_plant.setAttack()
            elif (target_plant.state == c.ATTACK and not can_attack):
                target_plant.setIdle()
        elif target_plant.name == c.TANGLEKLEP:
            for zombie in self.zombie_groups[i]:
                if target_plant.canAttack(zombie):
                    target_plant.setAttack(zombie, self.zombie_groups[i])
                    break
        # 灰烬植物与寒冰菇
        elif target_plant.name in c.ASH_PLANTS_AND_ICESHROOM:
            if target_plant.start_boom and (not target_plant.boomed):
                # 这样分成两层是因为场上灰烬植物肯定少，一个一个判断代价高，先笼统判断灰烬即可
                if target_plant.name in {c.REDWALLNUTBOWLING, c.CHERRYBOMB}:
                    self.boomZombies(target_plant.rect.centerx, i, target_plant.explode_y_range,
                                    target_plant.explode_x_range)
                elif (target_plant.name == c.DOOMSHROOM):
                    x, y = target_plant.original_x, target_plant.original_y
                    map_x, map_y = self.map.getMapIndex(x, y)
                    self.boomZombies(target_plant.rect.centerx, i, target_plant.explode_y_range,
                                    target_plant.explode_x_range)
                    for item in self.plant_groups[map_y]:
                        checkMapX, _ = self.map.getMapIndex(item.rect.centerx, item.rect.bottom)
                        if map_x == checkMapX:
                            item.health = 0
                    # 为了防止坑显示在蘑菇云前面，这里先不生成坑，仅填位置
                    self.map.map[map_y][map_x][c.MAP_PLANT].add(c.HOLE)
                elif target_plant.name == c.JALAPENO:
                    self.boomZombies(target_plant.rect.centerx, i, target_plant.explode_y_range,
                                    target_plant.explode_x_range, effect=c.BULLET_EFFECT_UNICE)
                    # 消除冰道
                    for item in self.plant_groups[i]:
                        if item.name == c.ICEFROZENPLOT:
                            item.health = 0
                elif target_plant.name == c.ICESHROOM:
                    self.freezeZombies(target_plant)
                target_plant.boomed = True
        else:
            can_attack = False
            if (zombie_len > 0):
                for zombie in self.zombie_groups[i]:
                    if target_plant.canAttack(zombie):
                        can_attack = True
                        break
            if target_plant.state == c.IDLE and can_attack:
                target_plant.setAttack()
            elif (target_plant.state == c.ATTACK and (not can_attack)):
                target_plant.setIdle()
    
    def checkPlants(self):
        for i in range(self.map_y_len):
            for plant in self.plant_groups[i]:
                if plant.state != c.SLEEP:
                    self.checkPlant(plant, i)
                if plant.health <= 0:
                    self.killPlant(plant)
    def checkLose(self):
        for i in range(self.map_y_len):
            for zombie in self.zombie_groups[i]:
                if zombie.rect.right < -20 and (not zombie.losthead) and (zombie.state != c.DIE):
                    self.next = c.MODE_LEADERBOARD   
                    self.done = True
                    return True
        return False

    def checkGameState(self):
        
        if self.checkLose():
            self.next = c.ENDSCREEN
            self.game_info[c.LEVEL_NUM] = self.current_time-self.start_time #記錄總遊玩時間
            self.done = True


    def drawMouseShow(self, surface):
        if self.hint_plant:
            surface.blit(self.hint_image, self.hint_rect)
        x, y = pg.mouse.get_pos()
        self.mouse_rect.centerx = x
        self.mouse_rect.centery = y
        surface.blit(self.mouse_image, self.mouse_rect)

    def drawMouseShowPlus(self, surface):   # 拖动铲子时的显示
        x, y = pg.mouse.get_pos()
        self.shovel_rect.centerx = x
        self.shovel_rect.centery = y
        # 铲子接近植物时会高亮提示
        map_x, map_y = self.map.getMapIndex(x, y)
        surface.blit(self.shovel, self.shovel_rect)
        if not self.map.isValid(map_x, map_y):
            return
        for i in self.plant_groups[map_y]:
            if (x >= i.rect.x and x <= i.rect.right and
                y >= i.rect.y and y <= i.rect.bottom):
                if i.name in c.NON_PLANT_OBJECTS:
                    continue
                if i.name in c.SKIP_ZOMBIE_COLLISION_CHECK_WHEN_WORKING:
                    if i.start_boom:
                        continue
                # 优先选中睡莲、花盆上的植物
                if len(self.map.map[map_y][map_x][c.MAP_PLANT]) >= 2:
                    if c.LILYPAD in self.map.map[map_y][map_x][c.MAP_PLANT]:
                        if i.name == c.LILYPAD:
                            continue
                    elif "花盆（未实现）" in self.map.map[map_y][map_x][c.MAP_PLANT]:
                        if i.name == "花盆（未实现）":
                            continue
                i.highlight_time = self.current_time
                return

    def drawZombieFreezeTrap(self, i, surface):
        for zombie in self.zombie_groups[i]:
            zombie.drawFreezeTrap(surface)


    def showLevelProgress(self, surface):
        # 画进度条框
        surface.blit(self.level_progress_bar_image, self.level_progress_bar_image_rect)

        # 按照当前波数生成僵尸头位置
        self.level_progress_zombie_head_image_rect.x = self.level_progress_bar_image_rect.x - int((150 * self.wave_num) / (self.map_data[c.NUM_FLAGS] * 10)) + 145      # 常数为拟合值
        self.level_progress_zombie_head_image_rect.y = self.level_progress_bar_image_rect.y - 3      # 常数为拟合值

        # 填充的进度条信息
        # 常数为拟合值
        filled_bar_rect = (self.level_progress_zombie_head_image_rect.x + 3, self.level_progress_bar_image_rect.y + 6, int((150 * self.wave_num) / (self.map_data[c.NUM_FLAGS] * 10)) + 5, 9)
        # 画填充的进度条
        pg.draw.rect(surface, c.YELLOWGREEN, filled_bar_rect)
        
        # 画旗帜
        for i in range(self.num_flags):
            self.level_progress_flag_rect.x = self.level_progress_bar_image_rect.x + int((150*i)/self.num_flags) + 5   # 常数是猜的
            # 当指示进度的僵尸头在旗帜左侧时升高旗帜
            if self.level_progress_flag_rect.x - 7 >= self.level_progress_zombie_head_image_rect.x:
                self.level_progress_flag_rect.y = self.level_progress_bar_image_rect.y - 15  # 常数是猜的
            else:
                self.level_progress_flag_rect.y = self.level_progress_bar_image_rect.y - 3  # 常数是猜的
            surface.blit(self.level_progress_flag, self.level_progress_flag_rect)

        # 画僵尸头
        surface.blit(self.level_progress_zombie_head_image, self.level_progress_zombie_head_image_rect)

    def showAllContentOfMenu(self, surface):
        # 绘制不可变内容
        surface.blit(self.big_menu, self.big_menu_rect)
        surface.blit(self.return_button, self.return_button_rect)
        surface.blit(self.restart_button, self.restart_button_rect)
        surface.blit(self.mainMenu_button, self.mainMenu_button_rect)

    def draw(self, surface):
        self.level.blit(self.background, self.viewport, self.viewport)
        surface.blit(self.level, (0,0), self.viewport)
        if self.state == c.CHOOSE:
            self.panel.draw(surface)
            # 画小菜单
            surface.blit(self.little_menu, self.little_menu_rect)
            if self.show_game_menu:
                self.showAllContentOfMenu(surface)
        # 以后可能需要插入一个预备的状态（预览显示僵尸、返回战场）
        elif self.state == c.PLAY:
            if self.has_shovel:
                # 画铲子
                surface.blit(self.shovel_box, self.shovel_box_rect)
                surface.blit(self.shovel, self.shovel_rect)
            # 画小菜单
            surface.blit(self.little_menu, self.little_menu_rect)

            self.menubar.draw(surface)
            for i in range(self.map_y_len):
                self.plant_groups[i].draw(surface)
                self.zombie_groups[i].draw(surface)
                self.hypno_zombie_groups[i].draw(surface)
                self.bullet_groups[i].draw(surface)
                self.drawZombieFreezeTrap(i, surface)
                if self.cars[i]:
                    self.cars[i].draw(surface)
            self.head_group.draw(surface)
            self.sun_group.draw(surface)

            if self.drag_plant:
                self.drawMouseShow(surface)

            if self.has_shovel and self.drag_shovel:
                self.drawMouseShowPlus(surface)

            if self.show_game_menu:
                self.showAllContentOfMenu(surface)

            if self.map_data[c.SPAWN_ZOMBIES] == c.SPAWN_ZOMBIES_AUTO:
                self.showLevelProgress(surface)
                if self.current_time - self.show_hugewave_approching_time <= 2000:
                    surface.blit(self.huge_wave_approching_image, self.huge_wave_approching_image_rect)

            # 顯示遊戲進行時間在左下角
            elapsed_seconds = (self.current_time-self.start_time) // 1000
            minutes = elapsed_seconds // 60
            seconds = elapsed_seconds % 60
            time_str = f"{minutes:02d}:{seconds:02d}"
            font = pg.font.Font(c.FONT_PATH, 20)
            time_surf = font.render(f"{time_str}", True, c.RED)
            time_rect = time_surf.get_rect()
            time_rect.x = 50
            time_rect.y = surface.get_height() - time_rect.height - 3
            surface.blit(time_surf, time_rect)
