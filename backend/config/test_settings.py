import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-for-production")
os.environ.setdefault("DJANGO_DEBUG", "True")
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
os.environ.setdefault("DB_NAME", "nefijj_test")
os.environ.setdefault("DB_USER", "test_only")
os.environ.setdefault("DB_PASSWORD", "test_only")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "3306")

from .settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
SECURE_SSL_REDIRECT = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
