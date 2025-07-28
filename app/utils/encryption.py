# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import os
from sqlalchemy.types import TypeDecorator, Text
from cryptography.fernet import Fernet

# ✅ Optional: load from .env in dev
if os.getenv("ENV") != "production":
    from dotenv import load_dotenv
    load_dotenv()

# 🔐 Get Fernet secret
FERNET_SECRET = os.getenv("FERNET_SECRET")

if not FERNET_SECRET:
    raise EnvironmentError("FERNET_SECRET is missing. Please set it in your environment or .env file.")

try:
    fernet = Fernet(FERNET_SECRET)
except Exception as e:
    raise ValueError("FERNET_SECRET is invalid. Make sure it is a valid 32-byte base64 string.") from e

# 🔐 Encrypt/Decrypt helpers
def encrypt(text: str) -> str:
    return fernet.encrypt(text.encode()).decode()

def decrypt(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()

# 🧩 Custom Encrypted DB Field
class EncryptedTypeHybrid(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return encrypt(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return decrypt(value)
        return value
