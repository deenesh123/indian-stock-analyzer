"""Auth, trial, settings for StockVista Pro"""
import streamlit as st
import json, os, hashlib, secrets
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data")
os.makedirs(DATA_DIR, exist_ok=True)
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "trial_days": 7,
    "app_name": "StockVista Pro",
    "payment_link": "https://your-payment-link.com",
    "payment_price": "Rs 499",
    "support_email": "support@example.com",
}

def _hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return h.hex(), salt

def _verify_password(password, password_hash, salt):
    h, _ = _hash_password(password, salt)
    return h == password_hash

def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_settings():
    s = load_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())
    for k, v in DEFAULT_SETTINGS.items():
        if k not in s:
            s[k] = v
    return s

def save_settings(s):
    save_json(SETTINGS_FILE, s)

def get_users():
    users = load_json(USERS_FILE, {})
    if "admin" not in users:
        ph, salt = _hash_password("admin123")
        users["admin"] = {
            "username": "admin", "password_hash": ph, "salt": salt, "role": "admin",
            "created": datetime.now().strftime("%Y-%m-%d"), "trial_start": None,
            "paid": True, "email": "",
        }
        save_json(USERS_FILE, users)
    return users

def save_users(users):
    save_json(USERS_FILE, users)

def register_user(username, password, email=""):
    users = get_users()
    username = username.strip().lower()
    if not username or not password:
        return False, "Username and password required."
    if username in users:
        return False, "Username already exists."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."
    ph, salt = _hash_password(password)
    users[username] = {
        "username": username, "password_hash": ph, "salt": salt, "role": "user",
        "created": datetime.now().strftime("%Y-%m-%d"),
        "trial_start": datetime.now().strftime("%Y-%m-%d"),
        "paid": False, "email": email,
    }
    save_users(users)
    return True, "Account created! Free trial started."

def login_user(username, password):
    users = get_users()
    username = username.strip().lower()
    if username not in users:
        return False, None, "Invalid username or password."
    u = users[username]
    if not _verify_password(password, u["password_hash"], u["salt"]):
        return False, None, "Invalid username or password."
    return True, u, "Login successful."

def trial_days_left(user, settings):
    if user.get("role") == "admin" or user.get("paid"):
        return 9999
    start = user.get("trial_start")
    if not start:
        return 0
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end = start_dt + timedelta(days=int(settings.get("trial_days", 7)))
        return max(0, (end - datetime.now()).days + 1)
    except Exception:
        return 0

def has_access(user, settings):
    if not user:
        return False
    if user.get("role") == "admin" or user.get("paid"):
        return True
    return trial_days_left(user, settings) > 0
