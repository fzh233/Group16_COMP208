import pygame
import pytmx
from random import randint
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, LAYERS
from save_load import SaveLoadSystem
from save_system import SaveSystem
from soil import SoilLayer
from player import Player
from overlay import Overlay
from transition import Transition
from sky import Rain, Sky
from menu import Menu
from sprites import Generic, Water, WildFlower, Tree, Interaction, Particle
from menu_ui import *
from support import resource_path

class Level:
    def __init__(self, auth=None, save_mode='local'):
        self.auth = auth
        self.save_mode = save_mode
        self.pause_menu = PauseMenu(self)

        self.raining = False

        #change
        # 本地存档系统
        self.save_system = SaveLoadSystem(self)
        self.save_local = lambda slot: self.save_system.save_game(slot, self.get_game_state())
        self.load_local = lambda slot: self.save_system.load_game(slot)

        # 云端存档系统（登录+模式为 cloud 时启用）
        if self.save_mode == 'cloud' and auth and auth.user.get('localId'):
            self.cloud_system = SaveSystem(auth)
            self.save_cloud = lambda slot: self.cloud_system.save_game(slot, self.get_game_state())
            self.load_cloud = lambda slot: self.cloud_system.load_game(slot)
        else:
            self.cloud_system = None
            self.save_cloud = lambda slot: None
            self.load_cloud = lambda slot: None

        # 初始化地图与场景
        pygame.init()
        self.display_surface = pygame.display.get_surface()
        tmx_path = (resource_path('data/map.tmx'))
        self.tmx_data = pytmx.load_pygame(tmx_path)

        self.all_sprites = CameraGroup()
        self.collision_sprites = pygame.sprite.Group()
        self.tree_sprites = pygame.sprite.Group()
        self.interaction_sprites = pygame.sprite.Group()

        self.soil_layer = SoilLayer(self.all_sprites, self.collision_sprites, self)
        self.setup()

        self.overlay = Overlay(self.player)
        self.transition = Transition(self.reset, self.player)
        self.rain = Rain(self.all_sprites)
        self.raining = randint(0,10) > 7
        self.soil_layer.raining = self.raining
        self.sky = Sky()
        self.menu = Menu(self.player, self.toggle_shop)
        self.shop_active = False

        self.success = pygame.mixer.Sound(resource_path('audio/success.wav'))
        self.success.set_volume(0.3)
        self.music = pygame.mixer.Sound(resource_path('audio/music.mp3'))
        self.music.play(loops=-1)

        # ✅ 优先加载云端槽 0 → 若失败则加载本地槽 0
        init_state = None
        if self.cloud_system:
            init_state = self.load_cloud(0)
        if not init_state:
            init_state = self.load_local(0)
        if init_state:
            self.apply_game_state(init_state)
            
    def setup(self):
        tmx = self.tmx_data
        Generic((0, 0), pygame.image.load(resource_path('images/world/ground.png')).convert_alpha(),
                [self.all_sprites], z=LAYERS['ground'])

        for layer in ['HouseFloor', 'HouseFurnitureBottom']:
            for x, y, surf in tmx.get_layer_by_name(layer).tiles():
                Generic((x*TILE_SIZE, y*TILE_SIZE), surf, [self.all_sprites], z=LAYERS['house bottom'])

        for layer in ['HouseWalls', 'HouseFurnitureTop']:
            for x, y, surf in tmx.get_layer_by_name(layer).tiles():
                Generic((x*TILE_SIZE, y*TILE_SIZE), surf, [self.all_sprites])

        for x, y, surf in tmx.get_layer_by_name('Fence').tiles():
            Generic((x*TILE_SIZE, y*TILE_SIZE), surf, [self.all_sprites, self.collision_sprites])

        water_frames = [surf for _, _, surf in tmx.get_layer_by_name('Water').tiles()]
        for x, y, _ in tmx.get_layer_by_name('Water').tiles():
            Water((x*TILE_SIZE, y*TILE_SIZE), water_frames, [self.all_sprites])

        for obj in tmx.get_layer_by_name('Trees'):
            Tree((obj.x, obj.y), obj.image,
                 [self.all_sprites, self.collision_sprites, self.tree_sprites],
                 obj.name, self.player_add)

        for obj in tmx.get_layer_by_name('Decoration'):
            WildFlower((obj.x, obj.y), obj.image,
                       [self.all_sprites, self.collision_sprites])

        for x, y, _ in tmx.get_layer_by_name('Collision').tiles():
            surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
            surf.fill('black')
            Generic((x*TILE_SIZE, y*TILE_SIZE), surf, [self.collision_sprites])

        for obj in tmx.get_layer_by_name('Player'):
            if obj.name == 'Start':
                self.player = Player(
                    pos=(obj.x, obj.y),
                    group=self.all_sprites,
                    collision_sprites=self.collision_sprites,
                    tree_sprites=self.tree_sprites,
                    interaction_sprites=self.interaction_sprites,
                    soil_layer=self.soil_layer,
                    toggle_shop=self.toggle_shop)
            elif obj.name in ('Bed', 'Trader'):
                Interaction((obj.x, obj.y), (obj.width, obj.height),
                            [self.interaction_sprites], obj.name)

    def player_add(self, item):
        self.player.item_inventory[item] += 1
        self.success.play()

    def toggle_shop(self):
        self.shop_active = not self.shop_active

    def reset(self):
        self.soil_layer.update_plants()
        self.soil_layer.remove_water()
        self.raining = randint(0,10) > 7
        self.soil_layer.raining = self.raining
        if self.raining:
            self.soil_layer.water_all()
        for tree in self.tree_sprites:
            # 添加类型检查确保是Tree实例
            if isinstance(tree, Tree):
                if hasattr(tree, 'apple_sprites'):
                    for apple in tree.apple_sprites:
                        apple.kill()
                    tree.create_fruit()
        
        self.sky.start_color = [255,255,255]

    def plant_collision(self):
        for plant in self.soil_layer.plant_sprites:
            if plant.harvestable and plant.rect.colliderect(self.player.hitbox):
                self.player_add(plant.plant_type)
                plant.kill()
                Particle(plant.rect.topleft, plant.image, self.all_sprites, z=LAYERS['main'])
                x = plant.rect.centerx // TILE_SIZE
                y = plant.rect.centery // TILE_SIZE
                self.soil_layer.grid[y][x].remove('P')

    def get_game_state(self):
        apples = []
        for tree in self.tree_sprites:
            if isinstance(tree, Tree) and tree.alive:
                for apple in tree.apple_sprites.sprites():
                    apples.append({
                        "tree_x": tree.rect.x,
                        "tree_y": tree.rect.y,
                        "apple_pos": (apple.rect.x - tree.rect.x, apple.rect.y - tree.rect.y)
                    })
                    
            return {
            'player': self.player.save_player_data(),
            'soil':   self.soil_layer.get_state_dict(),  # ← 保存完整土壤和植物状态
            "apples": apples,
            'map':    {'rain': self.raining},
            'sky':    {'start_color': self.sky.start_color}
    }

    def apply_game_state(self, state):
        # ✅ 玩家状态
        p = state.get('player', {})
        pos = p.get('pos', (self.player.pos.x, self.player.pos.y))
        self.player.current_pos = pos
        self.player.item_inventory = p.get('inventory', self.player.item_inventory)
        self.player.seed_inventory = p.get('seeds', self.player.seed_inventory)
        self.player.money = p.get('money', self.player.money)

        # 天气
        m = state.get('map',{})
        self.raining = m.get('rain', self.raining)
        self.soil_layer.raining = self.raining

        # 土壤与植物
        soil_data = state.get('soil')
        if soil_data is not None:
            self.soil_layer.load_state_dict(soil_data)

        # —— 安全清除并重建树木 —— 
        apple_backup = []
        for spr in list(self.tree_sprites):
            if isinstance(spr, Tree):
                apples = [(apple.rect.x - spr.rect.x, apple.rect.y - spr.rect.y) for apple in spr.apple_sprites]
                apple_backup.append((spr.rect.topleft, apples))
            spr.kill()
        for obj in self.tmx_data.get_layer_by_name('Trees'):
            tree = Tree(
                pos=(obj.x,obj.y),
                surf=obj.image,
                groups=[self.all_sprites,self.collision_sprites,self.tree_sprites],
                name=obj.name,
                player_add=self.player_add
            )
            for (pos, apples) in apple_backup:
                if tree.rect.topleft == pos:
                    for dx, dy in apples:
                        Generic(
                            pos=(tree.rect.x + dx, tree.rect.y + dy),
                            surf=tree.apple_surf,
                            groups=[tree.apple_sprites, self.all_sprites],
                            z=LAYERS['fruit']
                        )

        # 天空渐变色
        sky_data = state.get('sky',{})
        if 'start_color' in sky_data:
            self.sky.start_color = sky_data['start_color']
            
        apple_data = state.get("apples", [])
        for data in apple_data:
            tree_x, tree_y = data["tree_x"], data["tree_y"]
            apple_dx, apple_dy = data["apple_pos"]
            for tree in self.tree_sprites:
                if tree.rect.x == tree_x and tree.rect.y == tree_y:
                    apple = Generic(
                        pos=(tree.rect.x + apple_dx, tree.rect.y + apple_dy),
                        surf=tree.apple_surf,
                        groups=[tree.apple_sprites, self.all_sprites],
                        z=LAYERS['fruit']
                    )

    def load(self, slot):
        data = None
        if self.cloud_system:
            data = self.load_cloud(slot)
        if not data:
            data = self.load_local(slot)
        if data:
            self.apply_game_state(data)

    def save(self, slot):
        """通用保存接口：根据 save_mode 调用本地或云端存档"""
        if self.save_mode == 'cloud' and self.cloud_system:
            self.save_cloud(slot)
        else:
            self.save_local(slot)

    def run(self, dt):
        self.display_surface.fill('black')
        self.all_sprites.custom_draw(self.player)

        if not self.pause_menu.is_open:
            if self.shop_active:
                self.menu.update()
            else:
                self.all_sprites.update(dt)
                self.plant_collision()

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

        # 自动云存档
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
        self.offset.x = player.rect.centerx - SCREEN_WIDTH / 2
        self.offset.y = player.rect.centery - SCREEN_HEIGHT / 2
        for layer in LAYERS.values():
            for spr in sorted(self.sprites(), key=lambda s: s.rect.centery):
                if spr.z == layer:
                    offset_rect = spr.rect.copy()
                    offset_rect.center -= self.offset
                    self.display_surface.blit(spr.image, offset_rect)
