# save_system.py

import time
import pyrebase
from firebase_config import firebase_config

# 初始化 Pyrebase
firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()

class SaveSystem:
    """
    云端存档系统，用于按 30s 自动上传与按 1/2/3 手动覆盖
    """

    def __init__(self, auth):
        """
        auth: FirebaseAuth 实例，需先 login 或 register 成功
        """
        self.auth = auth
        self.last_saved = time.time()

    def save_game(self, slot, game_state):
        """
        立即上传到云端槽 slot，同时覆盖同名本地文件 save_{slot+1}.json
        """
        # 先写本地
        filename = f'save_{slot+1}.json'
        with open(filename, 'w') as f:
            import json
            json.dump(game_state, f, indent=2)
        print(f"💾 本地已保存 {filename}")

        # 再写云端
        user = getattr(self.auth, 'user', {}) or {}
        uid   = user.get('localId')
        token = user.get('idToken')
        if not uid or not token:
            print("⚠️ 未登录，跳过云端存档")
            return

        try:
            db.child("users")\
              .child(uid)\
              .child("saves")\
              .child(f"slot_{slot}")\
              .set(game_state, token)
            print(f"✅ 云端 slot_{slot} 上传成功")
        except Exception as e:
            print("❌ 云端存档失败：", e)

    def load_game(self, slot):
        """
        先尝试本地读取 save_{slot+1}.json，
        如果不存在，再尝试云端读取 slot_{slot}
        返回 dict 或 None
        """
        import json

        # 本地
        filename = f'save_{slot+1}.json'
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            print(f"💾 本地存档 {filename} 读取成功")
            return data
        except FileNotFoundError:
            print(f"⚠️ 本地 {filename} 不存在")

        # 云端
        user = getattr(self.auth, 'user', {}) or {}
        uid   = user.get('localId')
        token = user.get('idToken')
        if not uid or not token:
            print("⚠️ 未登录，无法读取云端存档")
            return None

        try:
            snapshot = db.child("users")\
                         .child(uid)\
                         .child("saves")\
                         .child(f"slot_{slot}")\
                         .get(token)
            data = snapshot.val()
            if data is None:
                print(f"⚠️ 云端无存档 slot_{slot}")
            else:
                print(f"✅ 云端存档 slot_{slot} 读取成功")
            return data
        except Exception as e:
            print("❌ 云端读取失败：", e)
            return None

    def auto_save_if_due(self, game_state, slot=0, interval=30):
        """
        每 interval 秒自动云端存档到槽 slot
        """
        now = time.time()
        if now - self.last_saved >= interval:
            print("⏳ 自动云端存档…")
            self.save_game(slot, game_state)
            self.last_saved = now
