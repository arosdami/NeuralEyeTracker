# core/user_manager.py
# Felhasználók kezelése – mentés users.json fájlba

import os
import json
import hashlib
import secrets
from datetime import datetime

from config.paths import USERS_FILE


class UserManager:
    def __init__(self, path: str = str(USERS_FILE)):
        self.path = str(path)
        self.users = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            self.users = {}
            self._save()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.users = json.load(f)
        except Exception:
            self.users = {}

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[USER_MANAGER] Mentési hiba: {e}")

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        data = (salt + password).encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def user_exists(self, username: str) -> bool:
        return username.lower() in [u.lower() for u in self.users.keys()]

    def register(self, username, password, full_name="", role="user"):
        username = username.strip()
        if not username:
            return False, "A felhasználónév nem lehet üres."
        if len(username) < 3:
            return False, "A felhasználónév legalább 3 karakter legyen."
        if not password or len(password) < 4:
            return False, "A jelszó legalább 4 karakter legyen."
        if self.user_exists(username):
            return False, "Ez a felhasználónév már létezik."

        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)

        self.users[username] = {
            "password_hash": password_hash,
            "salt": salt,
            "created": datetime.now().isoformat(),
            "last_login": "",
            "full_name": full_name,
            "role": role,
        }
        self._save()
        return True, "Sikeres regisztráció."

    def login(self, username, password):
        username = username.strip()
        if not username or not password:
            return False, None, "Add meg a felhasználónevet és jelszót."

        real_key = None
        for u in self.users.keys():
            if u.lower() == username.lower():
                real_key = u
                break

        if real_key is None:
            return False, None, "Nincs ilyen felhasználó."

        user = self.users[real_key]
        salt = user.get("salt", "")
        expected = user.get("password_hash", "")
        got = self._hash_password(password, salt)

        if got != expected:
            return False, None, "Hibás jelszó."

        user["last_login"] = datetime.now().isoformat()
        self._save()

        return True, {
            "username": real_key,
            "full_name": user.get("full_name", ""),
            "role": user.get("role", "user"),
            "last_login": user.get("last_login", ""),
        }, "Sikeres bejelentkezés."

    def get_user(self, username):
        for u in self.users.keys():
            if u.lower() == username.lower():
                return u, self.users[u]
        return None, None

    def list_users(self):
        return list(self.users.keys())