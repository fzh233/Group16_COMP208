# login_screen.py

import pygame, random, re, sys
from pygame import Rect
from firebase_auth import FirebaseAuth

class LoginScreen:
    def __init__(self, screen: pygame.Surface, auth: FirebaseAuth):
        self.screen = screen
        self.auth = auth
        sw, sh = screen.get_size()

        # 背景资源
        self.bg = pygame.image.load("../graphics/environment/login1.png").convert()
        self.bg = pygame.transform.scale(self.bg, (sw, sh))
        
        # 云朵动画
        self.cloud_img = pygame.image.load("../graphics/environment/cloud0.png").convert_alpha()
        self.clouds = [{
            "x": -200,
            "y": random.uniform(50, 200),
            "speed": random.uniform(40, 90),
            "scale": random.uniform(0.9, 1.1)
        } for _ in range(4)]

        # 字体配置
        self.title_font = pygame.font.Font("../font/PixeloidSans.ttf", 60)
        self.ui_font = pygame.font.Font("../font/PixeloidSans.ttf", 28)
        self.small_font = pygame.font.Font("../font/PixeloidSans.ttf", 20)

        # 输入框配置
        self.inputs = [
            {
                "label": "Email",
                "rect": Rect(sw//2-200, sh//2-60, 400, 45),
                "txt": "",
                "active": True
            },
            {
                "label": "Password", 
                "rect": Rect(sw//2-200, sh//2, 400, 45),
                "txt": "",
                "active": False
            }
        ]

        # 按钮配置
        self.buttons = {
            "login": {
                "rect": Rect(sw//2-220, sh//2+80, 180, 50),
                "color": (30, 120, 30),
                "text": "LOGIN"
            },
            "register": {
                "rect": Rect(sw//2+40, sh//2+80, 180, 50),
                "color": (80, 80, 200),
                "text": "REGISTER"
            }
        }

        # 错误提示
        self.error_msg = ""
        self.cursor_visible = True
        self.cursor_timer = 0

    def draw(self, dt):
        sw, sh = self.screen.get_size()
        self.screen.blit(self.bg, (0,0))
        
        # 绘制云朵动画
        for c in self.clouds:
            c["x"] += c["speed"] * dt
            if c["x"] > sw+50: c["x"] = -200
            img = pygame.transform.rotozoom(self.cloud_img, 0, c["scale"])
            self.screen.blit(img, (c["x"], c["y"]))

        # 绘制标题
        title = self.title_font.render("FARMING ISLAND", True, (30,30,30))
        self.screen.blit(title, (sw//2-title.get_width()//2, 100))

        # 绘制输入框
        for inp in self.inputs:
            # 输入框边框
            border_color = (0, 120, 200) if inp["active"] else (150, 150, 150)
            pygame.draw.rect(self.screen, border_color, inp["rect"], 2, border_radius=5)
            
            # 输入文本
            display_text = inp["txt"]
            if inp["label"] == "Password":
                display_text = "*" * len(display_text)
            text_surf = self.ui_font.render(display_text, True, (255,255,255))
            self.screen.blit(text_surf, (inp["rect"].x+10, inp["rect"].y+10))

            # 绘制标签
            label = self.small_font.render(inp["label"]+":", True, (255,255,255))
            self.screen.blit(label, (inp["rect"].x-120, inp["rect"].centery-8))

            # 光标效果
            if inp["active"] and self.cursor_visible:
                cursor_x = inp["rect"].x + 10 + text_surf.get_width() + 2
                pygame.draw.line(self.screen, (100,100,100),
                               (cursor_x, inp["rect"].y+10),
                               (cursor_x, inp["rect"].bottom-10), 2)

        # 绘制按钮
        mouse_pos = pygame.mouse.get_pos()
        for btn_key, btn in self.buttons.items():
            # 悬停效果
            color = list(btn["color"])
            if btn["rect"].collidepoint(mouse_pos):
                color = [min(c+30, 255) for c in color]
            
            # 按钮主体
            pygame.draw.rect(self.screen, color, btn["rect"], border_radius=8)
            
            # 按钮文字
            text = self.ui_font.render(btn["text"], True, (255,255,255))
            text_rect = text.get_rect(center=btn["rect"].center)
            self.screen.blit(text, text_rect)

        # 错误提示
        if self.error_msg:
            error_surf = self.small_font.render(self.error_msg, True, (200,30,30))
            self.screen.blit(error_surf, (sw//2-error_surf.get_width()//2, sh//2+140))

    def validate_inputs(self):
        """验证输入有效性"""
        email = self.inputs[0]["txt"].strip()
        password = self.inputs[1]["txt"].strip()
        
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
            self.error_msg = "❌ Invalid email format"
            return False
        if len(password) < 6:
            self.error_msg = "❌ Password must be at least 6 characters"
            return False
        return True

    def handle_auth(self, is_login=True):
        """处理登录/注册逻辑"""
        if not self.validate_inputs():
            return False

        email = self.inputs[0]["txt"].strip()
        password = self.inputs[1]["txt"].strip()
        
        try:
            if is_login:
                success = self.auth.login(email, password)
                if not success:
                    self.error_msg = "❌ Invalid credentials"
                    return False
            else:
                success = self.auth.register(email, password)
                if success == "EMAIL_EXISTS":
                    self.error_msg = "❌ Email already registered"
                    return False
                if not success:
                    self.error_msg = "❌ Registration failed"
                    return False
            return True
        except Exception as e:
            self.error_msg = f"❌ Error: {str(e)}"
            return False

    def run(self):
        clock = pygame.time.Clock()
        while True:
            dt = clock.tick(60)/1000
            
            # 光标闪烁逻辑
            self.cursor_timer += dt
            if self.cursor_timer > 0.5:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = 0

            # 事件处理
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # 鼠标点击事件
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = event.pos
                    
                    # 处理输入框焦点
                    for inp in self.inputs:
                        inp["active"] = inp["rect"].collidepoint(pos)
                    
                    # 处理按钮点击
                    if self.buttons["login"]["rect"].collidepoint(pos):
                        if self.handle_auth(is_login=True):
                            return True
                    elif self.buttons["register"]["rect"].collidepoint(pos):
                        if self.handle_auth(is_login=False):
                            return True
                
                # 键盘输入事件
                if event.type == pygame.KEYDOWN:
                    active_inp = next((i for i in self.inputs if i["active"]), None)
                    if active_inp:
                        if event.key == pygame.K_BACKSPACE:
                            active_inp["txt"] = active_inp["txt"][:-1]
                        elif event.key == pygame.K_TAB:
                            next_idx = (self.inputs.index(active_inp) + 1) % len(self.inputs)
                            self.inputs[next_idx]["active"] = True
                            active_inp["active"] = False
                        elif event.unicode.isprintable():
                            active_inp["txt"] += event.unicode

            # 绘制界面
            self.draw(dt)
            pygame.display.update()