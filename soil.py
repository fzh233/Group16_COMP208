import pygame
from random import choice
from support import import_folder, import_folder_dict, resource_path

from settings import *

class SoilTile(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft=pos)
        self.z = LAYERS['soil']

class WaterTile(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft=pos)
        self.z = LAYERS['soil water']

class Plant(pygame.sprite.Sprite):
    def __init__(self, plant_type, groups, soil, check_watered):
        super().__init__(groups)
        self.plant_type = plant_type
        self.frames = import_folder(resource_path(f'images/fruit/{plant_type}'))
        self.soil = soil
        self.check_watered = check_watered

        self.age = 0
        self.max_age = len(self.frames) - 1
        self.grow_speed = GROW_SPEED[plant_type]
        self.harvestable = False

        self.image = self.frames[self.age]
        self.y_offset = -16 if plant_type == 'corn' else -8
        self.rect = self.image.get_rect(
            midbottom=self.soil.rect.midbottom + pygame.math.Vector2(0, self.y_offset)
        )
        self.z = LAYERS['ground plant']

    def grow(self):
        if self.check_watered(self.rect.center):
            self.age += self.grow_speed
            if int(self.age) > 0:
                self.z = LAYERS['main']
                self.hitbox = self.rect.copy().inflate(-26, -self.rect.height * 0.4)
            if self.age >= self.max_age:
                self.age = self.max_age
                self.harvestable = True
            self.image = self.frames[int(self.age)]
            self.rect = self.image.get_rect(
                midbottom=self.soil.rect.midbottom + pygame.math.Vector2(0, self.y_offset)
            )

class SoilLayer:
    def __init__(self, all_sprites, collision_sprites, level):
        self.level = level
        self.all_sprites = all_sprites
        self.collision_sprites = collision_sprites
        self.soil_sprites = pygame.sprite.Group()
        self.water_sprites = pygame.sprite.Group()
        self.plant_sprites = pygame.sprite.Group()

        self.soil_surfs = import_folder_dict(resource_path('images/soil/'))
        self.water_surfs = import_folder(resource_path('images/soil_water'))

        self.create_soil_grid()
        self.create_hit_rects()

        self.hoe_sound = pygame.mixer.Sound(resource_path('audio/hoe.wav'))
        self.hoe_sound.set_volume(0.1)

        self.plant_sound = pygame.mixer.Sound(resource_path('audio/plant.wav'))
        self.plant_sound.set_volume(0.2)

    def create_soil_grid(self):
        farmable = self.level.tmx_data.get_layer_by_name('Farmable')
        self.grid = [[[] for _ in range(farmable.width)] for _ in range(farmable.height)]
        for x, y, _ in farmable.tiles():
            self.grid[y][x].append('F')

    def create_hit_rects(self):
        self.hit_rects = []
        for ry, row in enumerate(self.grid):
            if not isinstance(row, list):
                continue
            for rx, cell in enumerate(row):
                if isinstance(cell, list) and 'F' in cell:
                    self.hit_rects.append(pygame.Rect(rx*TILE_SIZE, ry*TILE_SIZE, TILE_SIZE, TILE_SIZE))

    def get_hit(self, point):
        for rect in self.hit_rects:
            if rect.collidepoint(point):
                self.hoe_sound.play()
                x, y = rect.x // TILE_SIZE, rect.y // TILE_SIZE
                cell = self.grid[y][x]
                if 'F' in cell and 'X' not in cell:
                    cell.append('X')
                    self.create_soil_tiles()
                    self.create_hit_rects()
                    if self.level.raining:
                        self.water_all()

    def water(self, target_pos):
        for soil in self.soil_sprites.sprites():
            if soil.rect.collidepoint(target_pos):
                x, y = soil.rect.x // TILE_SIZE, soil.rect.y // TILE_SIZE
                cell = self.grid[y][x]
                if 'W' not in cell:
                    cell.append('W')
                    WaterTile(soil.rect.topleft, choice(self.water_surfs),
                              [self.all_sprites, self.water_sprites])

    def water_all(self):
        for ry, row in enumerate(self.grid):
            if not isinstance(row, list):
                continue
            for rx, cell in enumerate(row):
                if isinstance(cell, list) and 'X' in cell and 'W' not in cell:
                    cell.append('W')
                    WaterTile((rx*TILE_SIZE, ry*TILE_SIZE),
                              choice(self.water_surfs),
                              [self.all_sprites, self.water_sprites])

    def remove_water(self):
        for w in self.water_sprites.sprites():
            w.kill()
        for ry, row in enumerate(self.grid):
            if not isinstance(row, list):
                continue
            for cell in row:
                if isinstance(cell, list) and 'W' in cell:
                    cell.remove('W')

    def check_watered(self, pos):
        x, y = pos[0] // TILE_SIZE, pos[1] // TILE_SIZE
        cell = self.grid[y][x]
        return isinstance(cell, list) and 'W' in cell

    def plant_seed(self, target_pos, seed):
        for soil in self.soil_sprites.sprites():
            if soil.rect.collidepoint(target_pos):
                x, y = soil.rect.x // TILE_SIZE, soil.rect.y // TILE_SIZE
                cell = self.grid[y][x]
                if 'P' not in cell:
                    self.plant_sound.play()
                    cell.append('P')
                    Plant(seed, [self.all_sprites, self.plant_sprites, self.collision_sprites],
                          soil, self.check_watered)

    def update_plants(self):
        for p in self.plant_sprites.sprites():
            p.grow()

    def create_soil_tiles(self):
        # 清除旧 soil 精灵
        for spr in list(self.soil_sprites.sprites()):
            spr.kill()

        for ry, row in enumerate(self.grid):
            if not isinstance(row, list):
                continue
            for rx, cell in enumerate(row):
                if not isinstance(cell, list):
                    continue
                if 'F' in cell and 'X' in cell:
                    # 安全检查上下左右是否为列表，避免 KeyError
                    t = False
                    if ry > 0 and isinstance(self.grid[ry-1], list) and rx < len(self.grid[ry-1]):
                        above = self.grid[ry-1][rx]
                        t = isinstance(above, list) and 'X' in above
                    b = False
                    if ry < len(self.grid)-1 and isinstance(self.grid[ry+1], list) and rx < len(self.grid[ry+1]):
                        below = self.grid[ry+1][rx]
                        b = isinstance(below, list) and 'X' in below
                    l = False
                    if rx > 0 and isinstance(row[rx-1], list):
                        l = 'X' in row[rx-1]
                    r = False
                    if rx < len(row)-1 and isinstance(row[rx+1], list):
                        r = 'X' in row[rx+1]

                    # 你的原 tile 选择逻辑
                    tile = 'o'
                    if all((t, r, b, l)): tile = 'x'
                    elif t and b and l: tile = 'tr'
                    elif t and b and r: tile = 'tl'
                    elif l and r and t: tile = 'br'
                    elif l and r and b: tile = 'bl'
                    elif t and b: tile = 'vertical'
                    elif l and r: tile = 'horizontal'
                    elif b and r: tile = 'tl_corner'
                    elif b and l: tile = 'tr_corner'
                    elif t and r: tile = 'bl_corner'
                    elif t and l: tile = 'br_corner'
                    elif t: tile = 'b'
                    elif b: tile = 't'
                    elif l: tile = 'r'
                    elif r: tile = 'l'

                    SoilTile((rx*TILE_SIZE, ry*TILE_SIZE),
                             self.soil_surfs[tile],
                             [self.all_sprites, self.soil_sprites])

    def get_state_dict(self):
        plants = []
        for p in self.plant_sprites:
            cx = p.soil.rect.x // TILE_SIZE
            cy = p.soil.rect.y // TILE_SIZE
            plants.append({'x':cx, 'y':cy, 'type':p.plant_type, 'age':p.age})
        return {'grid': self.grid, 'plants': plants}

    def load_state_dict(self, data):
        import copy
        raw = data.get('grid')
        if isinstance(raw, list):
            self.grid = copy.deepcopy(raw)

        # 杀掉所有旧精灵
        for spr in list(self.soil_sprites.sprites()): spr.kill()
        for spr in list(self.water_sprites.sprites()): spr.kill()
        for spr in list(self.plant_sprites.sprites()): spr.kill()

        # 重建场景
        self.create_soil_tiles()
        self.create_hit_rects()

        # 恢复水面
        for ry, row in enumerate(self.grid):
            if not isinstance(row, list): continue
            for rx, cell in enumerate(row):
                if isinstance(cell, list) and 'W' in cell:
                    WaterTile((rx*TILE_SIZE, ry*TILE_SIZE),
                              choice(self.water_surfs),
                              [self.all_sprites, self.water_sprites])

        # 恢复植物
        for pd in data.get('plants', []):
            cx = pd['x']*TILE_SIZE + TILE_SIZE//2
            cy = pd['y']*TILE_SIZE + TILE_SIZE//2
            self.plant_seed((cx, cy), pd['type'])
            plant = self.plant_sprites.sprites()[-1]
            plant.age = pd['age']
            plant.image = plant.frames[int(plant.age)]
