# local_save.py
import json

class LocalSaveSystem:
    def __init__(self):
        self.save_files = {
            i: f"save_{i+1}.json"
            for i in range(3)
        }

    def save_game(self, slot, game_state):
        """保存到本地槽 slot"""
        fname = self.save_files.get(slot)
        if not fname:
            return
        with open(fname, "w") as f:
            json.dump(game_state, f, indent=2)
        print(f"💾 本地已保存 {fname}")

    def load_game(self, slot):
        """从本地槽 slot 读取"""
        fname = self.save_files.get(slot)
        if not fname:
            return None
        try:
            with open(fname, "r") as f:
                data = json.load(f)
            print(f"💾 本地存档 {fname} 读取成功")
            return data
        except FileNotFoundError:
            print(f"⚠️ 本地 {fname} 不存在")
            return None
