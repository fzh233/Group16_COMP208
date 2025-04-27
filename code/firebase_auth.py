# firebase_auth.py

import pyrebase
from firebase_config import firebase_config

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

class FirebaseAuth:
    def __init__(self):
        self.user = None

    def login(self, email: str, password: str) -> bool:
        """登录，成功返回 True 并设置 self.user"""
        try:
            self.user = auth.sign_in_with_email_and_password(email, password)
            return True
        except Exception as e:
            print("🔒 Login failed:", e)
            return False

    def register(self, email: str, password: str):
        """
        注册，成功返回 True；
        如果 EMAIL_EXISTS -> 返回 'EMAIL_EXISTS'；
        其他错误返回 False
        """
        try:
            self.user = auth.create_user_with_email_and_password(email, password)
            return True
        except Exception as e:
            msg = str(e)
            if "EMAIL_EXISTS" in msg:
                return "EMAIL_EXISTS"
            print("🔑 Register failed:", e)
            return False
