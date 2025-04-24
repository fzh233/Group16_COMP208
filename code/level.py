import pygame
import pytmx
from random import randint
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, LAYERS
from save_load import SaveLoadSystem   # 你的本地存档系统
from save_system import SaveSystem     # 云端存档系统
from soil import SoilLayer
from player import Player
from overlay import Overlay
from transition import Transition
from sky import Rain, Sky
from menu import Menu
from sprites import Generic, Water, WildFlower, Tree, Interaction, Particle
from menu_ui import *

def deep_normalize(obj):
    """
    对任何从本地 JSON / Firebase 拉下来的对象
    • 把所有「键都是数字」的 dict → list  
    • 把所有 list 内部递归处理  
    • 把所有 None → []  
    最终保证：
        - grid 是 list[list[list[str]]]  
        - cell 永远是 list[str]
    """
    # None → 空列表
    if obj is None:
        return []
    # dict of numeric keys → list
    if isinstance(obj, dict) and all(str(k).isdigit() for k in obj.keys()):
        max_idx = max(int(k) for k in obj.keys())
        lst = []
        for i in range(max_idx+1):
            # 可能 key 是 int 或 str
            val = obj.get(i, obj.get(str(i)))
            lst.append(deep_normalize(val))
        return lst
    # list → 对每个元素递归
    if isinstance(obj, list):
        return [deep_normalize(item) for item in obj]
    # 其它原样返回（对你的场景，剩下应该是 list[str] 这种了）
    return obj

def normalize_grid(raw):
    """
    把任何从本地 JSON 或 Firebase 取回的 raw（可能是：
      • dict-of-dict    — Firebase 把数组当对象存的
      • 嵌套 list       — 本地 JSON 正常读出的
      • None            — 空数组在 DB 变成 null
    ）一锅端，最终输出 list-of-list-of-list[str]。
    """
    # 如果是 None 或非 dict/list，直接返回空矩阵
    if raw is None or not isinstance(raw, (dict, list)):
        return []

    # 如果是 dict，把它当成“数组转对象”的层级来还原
    if isinstance(raw, dict):
        # 先把行按数字 key 排序
        row_keys = [k for k in raw if str(k).isdigit()]
        grid = []
        for rk in sorted(row_keys, key=lambda k: int(k)):
            row_raw = raw.get(rk)
            # 单行可能也是 dict 或 list 或 None
            if isinstance(row_raw, dict):
                col_keys = [c for c in row_raw if str(c).isdigit()]
                row = []
                for ck in sorted(col_keys, key=lambda c: int(c)):
                    cell = row_raw.get(ck)
                    # cell 可能是 None、list、dict（极端情况），只对 list/dict 处理
                    row.append(cell if isinstance(cell, list) else (cell if cell else []))
            elif isinstance(row_raw, list):
                row = row_raw
            else:
                row = []
            grid.append(row)
    else:
        # 本身就是 list（可能嵌套不规则）
        grid = raw

    # 最后：把所有 None 一律换成 []；如果某行长度不一，也补齐 []
    max_cols = max((len(r) for r in grid), default=0)
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell is None:
                row[x] = []
        if len(row) < max_cols:
            row.extend([[]] * (max_cols - len(row)))

    return grid

class Level:
    def __init__(self, auth=None, save_mode='local'):
        """
        :param auth: FirebaseAuth 实例，用于云存档；若 None 则不启用云存档
        :param save_mode: 'local' 或 'cloud'
        """
        self.auth = auth
        self.save_mode = save_mode
        self.pause_menu = PauseMenu(self)
        
        self.raining = False
        # 1) 本地存档系统
        self.save_system = SaveLoadSystem(self)
        # 包装一个局部方法，只接 slot，自动获取 game_state
        self.save_local = lambda slot: self.save_system.save_game(slot, self.get_game_state())
        self.load_local = lambda slot: self.save_system.load_game(slot)

        # 2) 云端存档系统（只有登录且 save_mode='cloud' 时启用）
        if self.save_mode == 'cloud' and auth and auth.user.get('localId'):
            self.cloud_system = SaveSystem(auth)
            self.save_cloud = lambda slot: self.cloud_system.save_game(slot, self.get_game_state())
            self.load_cloud = lambda slot: self.cloud_system.load_game(slot)
        else:
            self.cloud_system = None
            self.save_cloud = lambda slot: None
            self.load_cloud = lambda slot: None

        # 3) 初始化画面、地图
        pygame.init()
        self.display_surface = pygame.display.get_surface()
        tmx_path = '../data/map.tmx'
        self.tmx_data = pytmx.load_pygame(tmx_path)

        # 4) 各种精灵组
        self.all_sprites         = CameraGroup()
        self.collision_sprites   = pygame.sprite.Group()
        self.tree_sprites        = pygame.sprite.Group()
        self.interaction_sprites = pygame.sprite.Group()

        # 5) 土壤层
        self.soil_layer = SoilLayer(self.all_sprites, self.collision_sprites, self)

        # 6) 先搭建场景，再尝试从存档恢复
        self.setup()

        # 7) 读取初始存档：优先云端槽0，否则本地槽0
        init_state = None
        if self.cloud_system:
            init_state = self.load_cloud(0)
        if not init_state:
            init_state = self.load_local(0)
        if init_state:
            self.apply_game_state(init_state)

        # 8) 其他界面、天气、商店……
        self.overlay    = Overlay(self.player)
        self.transition = Transition(self.reset, self.player)
        self.rain       = Rain(self.all_sprites)
        self.raining    = randint(0,10) > 7
        self.soil_layer.raining = self.raining
        self.sky        = Sky()
        self.menu       = Menu(self.player, self.toggle_shop)
        self.shop_active= False

        # 9) 背景音乐
        self.success = pygame.mixer.Sound('../audio/success.wav')
        self.success.set_volume(0.3)
        self.music   = pygame.mixer.Sound('../audio/music.mp3')
        self.music.play(loops=-1)

    def setup(self):
        """把地图瓦片、树、玩家、交互点加入精灵组。"""
        tmx = self.tmx_data
        # 地面
        Generic((0, 0),
                pygame.image.load('../graphics/world/ground.png').convert_alpha(),
                [self.all_sprites],
                z=LAYERS['ground'])
        # 房屋层
        for layer in ['HouseFloor','HouseFurnitureBottom']:
            for x,y,surf in tmx.get_layer_by_name(layer).tiles():
                Generic((x*TILE_SIZE,y*TILE_SIZE), surf, [self.all_sprites],
                        z=LAYERS['house bottom'])
        for layer in ['HouseWalls','HouseFurnitureTop']:
            for x,y,surf in tmx.get_layer_by_name(layer).tiles():
                Generic((x*TILE_SIZE,y*TILE_SIZE), surf, [self.all_sprites])
        # 栅栏
        for x,y,surf in tmx.get_layer_by_name('Fence').tiles():
            Generic((x*TILE_SIZE,y*TILE_SIZE), surf,
                    [self.all_sprites,self.collision_sprites])
        # 水块
        water_frames = [surf for _,_,surf in tmx.get_layer_by_name('Water').tiles()]
        for x,y,_ in tmx.get_layer_by_name('Water').tiles():
            Water((x*TILE_SIZE,y*TILE_SIZE), water_frames, [self.all_sprites])
        # 树木
        for obj in tmx.get_layer_by_name('Trees'):
            Tree(pos=(obj.x,obj.y),
                 surf=obj.image,
                 groups=[self.all_sprites,self.collision_sprites,self.tree_sprites],
                 name=obj.name,
                 player_add=self.player_add)
        # 野花
        for obj in tmx.get_layer_by_name('Decoration'):
            WildFlower((obj.x,obj.y), obj.image,
                       [self.all_sprites,self.collision_sprites])
        # 碰撞瓦片
        for x,y,_ in tmx.get_layer_by_name('Collision').tiles():
            surf = pygame.Surface((TILE_SIZE,TILE_SIZE))
            surf.fill('black')
            Generic((x*TILE_SIZE,y*TILE_SIZE), surf, [self.collision_sprites])
        # 玩家 & 交互
        for obj in tmx.get_layer_by_name('Player'):
            if obj.name=='Start':
                self.player = Player(
                    pos=(obj.x,obj.y),
                    group=self.all_sprites,
                    collision_sprites=self.collision_sprites,
                    tree_sprites=self.tree_sprites,
                    interaction_sprites=self.interaction_sprites,
                    soil_layer=self.soil_layer,
                    toggle_shop=self.toggle_shop)
            elif obj.name in ('Bed','Trader'):
                Interaction((obj.x,obj.y),(obj.width,obj.height),
                            [self.interaction_sprites], obj.name)

    def player_add(self, item):
        """玩家获得物品时调用"""
        self.player.item_inventory[item] += 1
        self.success.play()

    def toggle_shop(self):
        self.shop_active = not self.shop_active

    def reset(self):
        """新一天开始时的重置"""
        self.soil_layer.update_plants()
        self.soil_layer.remove_water()
        self.raining = randint(0,10)>7
        self.soil_layer.raining = self.raining
        if self.raining:
            self.soil_layer.water_all()
        for tree in self.tree_sprites:
            for apple in tree.apple_sprites:
                apple.kill()
            tree.create_fruit()
        self.sky.start_color = [255,255,255]

    def plant_collision(self):
        """检测并收获成熟植物"""
        for plant in self.soil_layer.plant_sprites:
            if plant.harvestable and plant.rect.colliderect(self.player.hitbox):
                self.player_add(plant.plant_type)
                plant.kill()
                Particle(plant.rect.topleft, plant.image,
                         self.all_sprites, z=LAYERS['main'])
                x = plant.rect.centerx // TILE_SIZE
                y = plant.rect.centery  // TILE_SIZE
                self.soil_layer.grid[y][x].remove('P')

    def get_game_state(self):
        """打包要保存的全量状态"""
        return {
            'player': self.player.save_player_data(),
            'soil':   self.soil_layer.grid,
            'map':    {'rain': self.raining}
        }

    def apply_game_state(self, state):
        """根据 state 恢复玩家、土壤、天气"""
        # 玩家
        p = state.get('player',{})
        pos = p.get('pos',(self.player.pos.x,self.player.pos.y))
        self.player.current_pos = pos
        self.player.item_inventory = p.get('inventory', self.player.item_inventory)
        self.player.seed_inventory  = p.get('seeds',     self.player.seed_inventory)
        self.player.money           = p.get('money',     self.player.money)
        # 天气
        m = state.get('map',{})
        self.raining = m.get('rain', self.raining)
        self.soil_layer.raining = self.raining
        # 土壤
        raw = state.get('soil')
        if raw is not None:
            # 1) 深度 normalize，把所有 dict→list, None→[]
            grid = deep_normalize(raw)
            # 2) 赋值并重建瓦片 & hit_rects
            self.soil_layer.grid = grid
            self.soil_layer.create_soil_tiles()
            self.soil_layer.create_hit_rects()

    def save(self, slot):
        """按 1/2/3 手动存档"""
        self.save_local(slot)                # 本地
        if self.cloud_system:
            self.save_cloud(slot)            # 云端（覆盖相应槽位）

    def load(self, slot):
        """按 4/5/6 快速读档：优先云端再本地"""
        data = None
        if self.cloud_system:
            data = self.load_cloud(slot)
        if not data:
            data = self.load_local(slot)
        if data:
            self.apply_game_state(data)

    def run(self, dt):
        """每帧更新与渲染"""
        self.display_surface.fill('black')
        self.all_sprites.custom_draw(self.player)

        if not self.pause_menu.is_open:  # 只有菜单关闭时更新游戏
            if self.shop_active:
                self.menu.update()
            else:
                self.all_sprites.update(dt)
                self.plant_collision()

        # 更新和绘制菜单
        self.pause_menu.update(dt)
        self.pause_menu.draw(self.display_surface)
        
        if self.shop_active:
            self.menu.update()
        else:
            self.all_sprites.update(dt)
            self.plant_collision()

        self.overlay.display()
        if self.raining and not self.shop_active:
            self.rain.update()
        self.sky.display(dt)

        # 每 30 秒自动云端存档到槽 0
        if self.cloud_system:
            self.cloud_system.auto_save_if_due(self.get_game_state())

        if self.player.sleep:
            self.transition.play()


class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()

    def custom_draw(self, player):
        self.offset.x = player.rect.centerx - SCREEN_WIDTH/2
        self.offset.y = player.rect.centery  - SCREEN_HEIGHT/2
        for layer in LAYERS.values():
            for spr in sorted(self.sprites(), key=lambda s: s.rect.centery):
                if spr.z == layer:
                    off = spr.rect.copy()
                    off.center -= self.offset
                    self.display_surface.blit(spr.image, off)
