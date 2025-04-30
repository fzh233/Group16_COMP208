import pygame
from settings import *
from support import import_folder
from timer import Timer
from support import resource_path
from sprites import Tree

class Player(pygame.sprite.Sprite):
    @property
    def current_pos(self):
        return self.pos

    @current_pos.setter
    def current_pos(self, value):
        self.pos = pygame.math.Vector2(value)
        self.rect.center = self.pos
        self.hitbox.center = self.pos

    def __init__(self, pos, group, collision_sprites, tree_sprites, interaction_sprites, soil_layer, toggle_shop):
        super().__init__(group)

        # 角色动画与状态
        self.import_assets()
        self.status = 'down_idle'
        self.frame_index = 0
        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(center=pos)
        self.z = LAYERS['main']

        # 移动属性
        self.direction = pygame.math.Vector2()
        self.pos = pygame.math.Vector2(self.rect.center)
        self.speed = 200

        # 碰撞
        self.hitbox = self.rect.copy().inflate(-126, -70)
        self.collision_sprites = collision_sprites

        # 定时器：统一使用和切换
        self.timers = {
            'use': Timer(350, self.use_item),
            'item switch': Timer(200),
        }

        # 工具与种子合并管理
        self.tools = ['hoe', 'axe', 'water']
        self.seeds = ['corn', 'tomato']
        self.inventory = self.tools + self.seeds  # ['hoe','axe','water','corn','tomato']
        self.selected_index = 0
        self.selected_tool = self.tools[0]
        self.selected_seed = self.seeds[0]

        # 背包数量与经济
        self.item_inventory = {
            'wood': 20,
            'apple': 20,
            'corn': 20,
            'tomato': 20,
        }
        self.seed_inventory = {
            'corn': 5,
            'tomato': 5
        }
        self.money = 200

        # 交互与场景引用
        self.tree_sprites = tree_sprites
        self.interaction = interaction_sprites
        self.sleep = False
        self.soil_layer = soil_layer
        self.toggle_shop = toggle_shop

        # 声音
        self.watering = pygame.mixer.Sound(resource_path('audio/water.mp3'))
        self.watering.set_volume(0.2)


    def use_item(self):
        # 根据当前高亮项执行动作
        if self.selected_index < len(self.tools):
            # 工具
            self.selected_tool = self.tools[self.selected_index]
            self.use_tool()
        else:
            # 种子
            self.selected_seed = self.seeds[self.selected_index - len(self.tools)]
            self.use_seed()

    def use_tool(self):
        if self.selected_tool == 'hoe':
            self.soil_layer.get_hit(self.target_pos)
        elif self.selected_tool == 'axe':
            for sprite in self.tree_sprites.sprites():
                if isinstance(sprite, Tree) and sprite.rect.collidepoint(self.target_pos):  # 添加类型检查
                    sprite.damage()
                    if not sprite.alive:
                        self.tree_sprites.remove(sprite)
        elif self.selected_tool == 'water':
            self.soil_layer.water(self.target_pos)
            self.watering.play()

    def use_seed(self):
        if self.seed_inventory[self.selected_seed] > 0:
            self.soil_layer.plant_seed(self.target_pos, self.selected_seed)
            self.seed_inventory[self.selected_seed] -= 1

    def get_target_pos(self):
        self.target_pos = self.rect.center + PLAYER_TOOL_OFFSET[self.status.split('_')[0]]

    def import_assets(self):
        dirs = [
            'up','down','left','right',
            'up_idle','down_idle','left_idle','right_idle',
            'up_hoe','down_hoe','left_hoe','right_hoe',
            'up_axe','down_axe','left_axe','right_axe',
            'up_water','down_water','left_water','right_water'
        ]
        self.animations = {}
        for key in dirs:
            self.animations[key] = import_folder(resource_path(f"images/character/{key}"))


    def animate(self, dt):
        self.frame_index += 4 * dt
        if self.frame_index >= len(self.animations[self.status]):
            self.frame_index = 0
        self.image = self.animations[self.status][int(self.frame_index)]

    def input(self):
        keys = pygame.key.get_pressed()

        # 如果正在使用物品或睡眠中，禁止其他输入
        if not self.timers['use'].active and not self.sleep:
            # 移动方向
            if keys[pygame.K_UP]:
                self.direction.y = -1
                self.status = 'up'
            elif keys[pygame.K_DOWN]:
                self.direction.y = 1
                self.status = 'down'
            else:
                self.direction.y = 0
            if keys[pygame.K_RIGHT]:
                self.direction.x = 1
                self.status = 'right'
            elif keys[pygame.K_LEFT]:
                self.direction.x = -1
                self.status = 'left'
            else:
                self.direction.x = 0

            # 空格使用当前高亮物品（工具或种子）
            if keys[pygame.K_SPACE]:
                self.timers['use'].activate()
                self.direction = pygame.math.Vector2()
                self.frame_index = 0

            # Q/E 切换物品栏高亮
            if (keys[pygame.K_q] or keys[pygame.K_e]) and not self.timers['item switch'].active:
                self.timers['item switch'].activate()
                delta = -1 if keys[pygame.K_q] else 1
                self.selected_index = (self.selected_index + delta) % len(self.inventory)
                # 更新选中项对应的工具/种子，用于状态动画切换
                if self.selected_index < len(self.tools):
                    self.tool_index = self.selected_index
                    self.selected_tool = self.tools[self.tool_index]
                else:
                    self.seed_index = self.selected_index - len(self.tools)
                    self.selected_seed = self.seeds[self.seed_index]

            # 交互
            if keys[pygame.K_TAB]:
                collided = pygame.sprite.spritecollide(self, self.interaction, False)
                if collided:
                    if collided[0].name == 'Trader':
                        self.toggle_shop()
                    else:
                        self.status = 'left_idle'
                        self.sleep = True

    def get_status(self):
        # 空闲状态
        if self.direction.magnitude() == 0:
            self.status = self.status.split('_')[0] + '_idle'
        # 使用时显示工具动画；种子保持 idle
        if self.timers['use'].active:
            if self.selected_index < len(self.tools):
                self.status = self.status.split('_')[0] + '_' + self.selected_tool
            else:
                self.status = self.status.split('_')[0] + '_idle'

    def update_timers(self):
        for t in self.timers.values():
            t.update()

    def collision(self, direction):
        for sprite in self.collision_sprites.sprites():
            if hasattr(sprite, 'hitbox') and sprite.hitbox.colliderect(self.hitbox):
                if direction == 'horizontal':
                    if self.direction.x > 0:
                        self.hitbox.right = sprite.hitbox.left
                    if self.direction.x < 0:
                        self.hitbox.left = sprite.hitbox.right
                    self.rect.centerx = self.hitbox.centerx
                    self.pos.x = self.hitbox.centerx
                else:
                    if self.direction.y > 0:
                        self.hitbox.bottom = sprite.hitbox.top
                    if self.direction.y < 0:
                        self.hitbox.top = sprite.hitbox.bottom
                    self.rect.centery = self.hitbox.centery
                    self.pos.y = self.hitbox.centery

    def move(self, dt):
        if self.direction.magnitude() > 0:
            self.direction = self.direction.normalize()
        self.pos.x += self.direction.x * self.speed * dt
        self.hitbox.centerx = round(self.pos.x)
        self.rect.centerx = self.hitbox.centerx
        self.collision('horizontal')
        self.pos.y += self.direction.y * self.speed * dt
        self.hitbox.centery = round(self.pos.y)
        self.rect.centery = self.hitbox.centery
        self.collision('vertical')

    def update(self, dt):
        self.input()
        self.get_status()
        self.update_timers()
        self.get_target_pos()
        self.move(dt)
        self.animate(dt)

    def save_player_data(self):
        return {
            "pos": tuple(self.pos),
            "inventory": self.item_inventory,
            "seeds":     self.seed_inventory,
            "money":     self.money
        }

    def load_player_data(self,data):
        x,y = data.get("pos",tuple(self.pos))
        self.pos=pygame.math.Vector2(x,y)
        self.rect.center=self.pos; self.hitbox.center=self.pos
        self.item_inventory=data.get("inventory",self.item_inventory)
        self.seed_inventory=data.get("seeds",self.seed_inventory)
        self.money=data.get("money",self.money)
