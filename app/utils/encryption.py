# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.types import TypeDecorator
from cryptography.fernet import Fernet
import os

# 🔐 Load secret key from env (safe!)
FERNET_SECRET = os.getenv("FERNET_SECRET")  # Must be 32-byte base64
fernet = Fernet(FERNET_SECRET)

if not FERNET_SECRET:
    raise ValueError("FERNET_SECRET not set in environment variables.")

def encrypt(text: str) -> str:
    return fernet.encrypt(text.encode()).decode()

def decrypt(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()

class EncryptedTypeHybrid(TypeDecorator):
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            return encrypt(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return decrypt(value)
        return value