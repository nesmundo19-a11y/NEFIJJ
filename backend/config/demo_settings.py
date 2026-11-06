import os
from pathlib import Path

from .test_settings import *


demo_database_path = Path(
    os.getenv("NEFIJJ_DEMO_DB_PATH", BASE_DIR / "nefijj-demo.sqlite3"),
).expanduser()

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": demo_database_path,
    }
}

DEBUG = True
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "[::1]",
    *[
        host.strip()
        for host in os.getenv("NEFIJJ_DEMO_ALLOWED_HOSTS", "").split(",")
        if host.strip()
    ],
]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
NEFIJJ_DEMO_MODE = True
