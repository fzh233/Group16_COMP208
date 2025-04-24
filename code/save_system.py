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
        仅上传到云端槽 slot，不影响本地存档。
        """
        user = getattr(self.auth, 'user', {}) or {}
        uid   = user.get('localId')
        token = user.get('idToken')
        if not uid or not token:
            print("⚠️ 未登录，跳过云端存档")
            return

        try:
            db.child("users") \
              .child(uid) \
              .child("saves") \
              .child(f"slot_{slot}") \
              .set(game_state, token)
            print(f"✅ 云端 slot_{slot} 上传成功")
        except Exception as e:
            print("❌ 云端存档失败：", e)

    def load_game(self, slot):
        """
        仅尝试从云端槽 slot 读取存档，返回 dict 或 None。
        本地回退请用 SaveLoadSystem.load_game，由 Level.load 来做。
        """
        user = getattr(self.auth, 'user', {}) or {}
        uid   = user.get('localId')
        token = user.get('idToken')
        if not uid or not token:
            print("⚠️ 未登录，无法读取云端存档")
            return None

        try:
            snapshot = db.child("users") \
                         .child(uid) \
                         .child("saves") \
                         .child(f"slot_{slot}") \
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
