# save_load.py

import json
from pathlib import Path

class SaveLoadSystem:
    def __init__(self, level):
        self.level = level
        self.save_folder = Path("saves")
        self.save_folder.mkdir(exist_ok=True)
        self.slots = 3

    def save_game(self, slot, game_state):
        """手动本地存档"""
        if 0 <= slot < self.slots:
            filename = self.save_folder / f"save_{slot+1}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(game_state, f, ensure_ascii=False, indent=2)
            print(f"💾 Local saved {filename}")

    def load_game(self, slot):
        """手动本地读档"""
        filename = self.save_folder / f"save_{slot+1}.json"
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"💾 Local load succeeded: {filename}")
            return data
        except FileNotFoundError:
            print(f"⚠️ Local file not found: {filename}")
            return None
