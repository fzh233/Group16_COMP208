import pygame
from random import choice
from pytmx.util_pygame import load_pygame
from support import import_folder, import_folder_dict
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
        self.frames = import_folder(f'../graphics/fruit/{plant_type}')
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

        self.soil_surfs = import_folder_dict('../graphics/soil/')
        self.water_surfs = import_folder('../graphics/soil_water')

        self.create_soil_grid()
        self.create_hit_rects()

        self.hoe_sound = pygame.mixer.Sound('../audio/hoe.wav')
        self.hoe_sound.set_volume(0.1)
        self.plant_sound = pygame.mixer.Sound('../audio/plant.wav')
        self.plant_sound.set_volume(0.2)

    def create_soil_grid(self):
        tmx_data = self.level.tmx_data
        farmable = tmx_data.get_layer_by_name('Farmable')
        self.grid = [[[] for _ in range(farmable.width)] for _ in range(farmable.height)]
        for x, y, _ in farmable.tiles():
            self.grid[y][x].append('F')

    def create_hit_rects(self):
        self.hit_rects = []
        for ry, row in enumerate(self.grid):
            for rx, cell in enumerate(row):
                if 'F' in cell:
                    rect = pygame.Rect(rx * TILE_SIZE, ry * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    self.hit_rects.append(rect)

    def get_hit(self, point):
        for rect in self.hit_rects:
            if rect.collidepoint(point):
                self.hoe_sound.play()
                x, y = rect.x // TILE_SIZE, rect.y // TILE_SIZE
                if y < 0 or y >= len(self.grid) or x < 0 or x >= len(self.grid[y]):
                    return
                if 'F' in self.grid[y][x]:
                    self.grid[y][x].append('X')
                    self.create_soil_tiles()
                    if self.level.raining:
                        self.water_all()

    def water(self, target_pos):
        for soil in self.soil_sprites.sprites():
            if soil.rect.collidepoint(target_pos):
                x, y = soil.rect.x // TILE_SIZE, soil.rect.y // TILE_SIZE
                self.grid[y][x].append('W')
                WaterTile(soil.rect.topleft, choice(self.water_surfs),
                          [self.all_sprites, self.water_sprites])

    def water_all(self):
        for ry, row in enumerate(self.grid):
            for rx, cell in enumerate(row):
                if 'X' in cell and 'W' not in cell:
                    cell.append('W')
                    WaterTile((rx * TILE_SIZE, ry * TILE_SIZE),
                              choice(self.water_surfs),
                              [self.all_sprites, self.water_sprites])

    def remove_water(self):
        for w in self.water_sprites.sprites():
            w.kill()
        for row in self.grid:
            if 'W' in row:
                row.remove('W')

    def check_watered(self, pos):
        x, y = pos[0] // TILE_SIZE, pos[1] // TILE_SIZE
        return 'W' in self.grid[y][x]

    def plant_seed(self, target_pos, seed):
        for soil in self.soil_sprites.sprites():
            if soil.rect.collidepoint(target_pos):
                x, y = soil.rect.x // TILE_SIZE, soil.rect.y // TILE_SIZE
                if 'P' not in self.grid[y][x]:
                    self.plant_sound.play()
                    self.grid[y][x].append('P')
                    Plant(seed, [self.all_sprites, self.plant_sprites, self.collision_sprites],
                          soil, self.check_watered)

    def update_plants(self):
        for p in self.plant_sprites.sprites():
            p.grow()

    def create_soil_tiles(self):
        self.soil_sprites.empty()
        for ry, row in enumerate(self.grid):
            for rx, cell in enumerate(row):
                if 'X' in cell:
                    # 检查四周标记
                    t = 'X' in self.grid[ry-1][rx]
                    b = 'X' in self.grid[ry+1][rx]
                    l = 'X' in row[rx-1]
                    r = 'X' in row[rx+1]
                    tile = 'o'
                    # 全包围
                    if all((t,r,b,l)): tile = 'x'
                    # … （其余分支同你原来逻辑） …
                    SoilTile((rx*TILE_SIZE, ry*TILE_SIZE),
                             self.soil_surfs[tile],
                             [self.all_sprites, self.soil_sprites])

    # ——— 新增：打包 / 恢复 —————————————————

    def get_state_dict(self):
        """打包当前 soil_layer 状态"""
        plants = []
        for p in self.plant_sprites:
            cx = p.soil.rect.x // TILE_SIZE
            cy = p.soil.rect.y // TILE_SIZE
            plants.append({'x': cx, 'y': cy, 'type': p.plant_type, 'age': p.age})
        return {'grid': self.grid, 'plants': plants}

    def load_state_dict(self, data):
        """根据 get_state_dict 恢复状态"""
        self.grid = data['grid']
        self.soil_sprites.empty()
        self.water_sprites.empty()
        self.plant_sprites.empty()
        self.create_soil_tiles()
        for pd in data['plants']:
            cx = pd['x'] * TILE_SIZE + TILE_SIZE//2
            cy = pd['y'] * TILE_SIZE + TILE_SIZE//2
            self.plant_seed((cx, cy), pd['type'])
            plant = self.plant_sprites.sprites()[-1]
            plant.age = pd['age']
            plant.image = plant.frames[int(plant.age)]
