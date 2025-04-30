import pygame, sys
from settings import SCREEN_WIDTH, SCREEN_HEIGHT
from firebase_auth import FirebaseAuth
from login_screen import LoginScreen
from level import Level

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Sow & Gain")
        self.clock = pygame.time.Clock()

        # 登录/注册
        self.auth = FirebaseAuth()
        login = LoginScreen(self.screen, self.auth)
        ok    = login.run()
        if not ok:
            pygame.quit()
            sys.exit()
        print("✅ login success, UID =", self.auth.user["localId"])

        # 启动游戏，云存档模式
        self.level = Level(auth=self.auth, save_mode="cloud")

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                self.level.pause_menu.handle_event(e)

                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        self.level.pause_menu.toggle_menu()

                    # ✅ 1/2/3 → local save
                    if e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                        slot = e.key - pygame.K_1
                        self.level.save_local(slot)

                    # ✅ 4/5/6 → local save reading
                    elif e.key in (pygame.K_4, pygame.K_5, pygame.K_6):
                        slot = e.key - pygame.K_4
                        self.level.load(slot)

            dt = self.clock.tick(60) / 1000
            self.level.run(dt)
            pygame.display.update()

if __name__ == "__main__":
    Game().run()
