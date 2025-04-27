import pygame, sys
from random import randint
from settings import *
from support import resource_path

class PixelButton:
    def __init__(self, x, y, text, callback):
        self.rect = pygame.Rect(x, y, BUTTON_WIDTH, BUTTON_HEIGHT)
        self.text = text
        self.callback = callback
        self.hovered = False
        self.visible = False
        self.target_x = x  # 用于动画的最终位置

        # 像素噪声纹理（创建小斑点）
        self.texture = pygame.Surface((BUTTON_WIDTH, BUTTON_HEIGHT))
        for _ in range(30):  # 随机添加深色像素点
            x = randint(2, BUTTON_WIDTH-3)
            y = randint(2, BUTTON_HEIGHT-3)
            self.texture.set_at((x,y), UI_COLORS['brown_dark'])
            
    def draw(self, surface):
        if not self.visible:
            return
            
        # 绘制边框（深棕色）
        pygame.draw.rect(surface, UI_COLORS['brown_dark'], 
                       self.rect.inflate(4,4), 2, border_radius=3)
        
        # 填充底色（浅棕色）
        fill_rect = self.rect.copy()
        if self.hovered:
            fill_color = UI_COLORS['beige']  # 悬停时使用米色
        else:
            fill_color = UI_COLORS['brown_light']
            
        pygame.draw.rect(surface, fill_color, fill_rect, border_radius=3)
        
        # 添加纹理
        surface.blit(self.texture, self.rect.topleft, special_flags=pygame.BLEND_RGBA_MULT)
        
        # 绘制文字（带1像素阴影）
        font = pygame.font.Font(resource_path('font/PixeloidSans.ttf'), UI_FONT_SIZE)  # 使用像素字体
        text_surf = font.render(self.text, True, UI_COLORS['brown_dark'])
        text_rect = text_surf.get_rect(center=(self.rect.centerx+1, self.rect.centery+1))
        surface.blit(text_surf, text_rect)
        
        text_surf = font.render(self.text, True, UI_COLORS['text'])
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
        
        # 添加高光线（顶部1像素）
        pygame.draw.line(surface, UI_COLORS['beige'],
                        (self.rect.left+2, self.rect.top+1),
                        (self.rect.right-2, self.rect.top+1), 1)

    def handle_event(self, event):
        if not self.visible:
            return
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and self.hovered:
            self.callback()

class PauseMenu:
    def __init__(self, level):
        self.level = level
        self.buttons = []
        self.is_open = False
        self.animation_progress = 0  # 0-1 的动画进度
        
        # 主按钮
        self.main_button = PixelButton(
            x=-BUTTON_WIDTH,  # 初始在屏幕外
            y=MENU_OFFSET,
            text="ESC",
            callback=self.toggle_menu
        )
        
        # 子按钮
        buttons_data = [
            ("Save", self.save),
            ("Load", self.load),
            ("Quit", self.quit)
        ]
        for i, (text, cb) in enumerate(buttons_data):
            btn = PixelButton(
                x=-BUTTON_WIDTH,
                y=MENU_OFFSET + (BUTTON_HEIGHT + 5) * (i+1),
                text=text,
                callback=cb
            )
            self.buttons.append(btn)

    def toggle_menu(self):
        self.is_open = not self.is_open
        self.main_button.visible = True
        
    def save(self):
        self.level.save(0)  # 默认保存到槽位0
        self.toggle_menu()
        
    def load(self):
        self.level.load(0)  # 默认从槽位0加载
        self.toggle_menu()
        
    def quit(self):
        pygame.quit()
        sys.exit()

    def update(self, dt):
        # 平滑动画
        target_x = MENU_OFFSET if self.is_open else -BUTTON_WIDTH
        self.animation_progress = min(1, self.animation_progress + dt*5)
        
        # 主按钮动画
        self.main_button.rect.x = pygame.math.lerp(
            self.main_button.rect.x, target_x, self.animation_progress
        )
        
        # 子按钮动画（延迟出现）
        for i, btn in enumerate(self.buttons):
            btn.target_x = MENU_OFFSET if self.is_open else -BUTTON_WIDTH
            btn.rect.x = pygame.math.lerp(
                btn.rect.x, btn.target_x, self.animation_progress
            )
            btn.visible = self.is_open

    def draw(self, surface):
        self.main_button.draw(surface)
        for btn in self.buttons:
            btn.draw(surface)

    def handle_event(self, event):
        self.main_button.handle_event(event)
        for btn in self.buttons:
            btn.handle_event(event)