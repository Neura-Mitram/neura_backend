# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from fastapi import Request
from app.models.user import User


def handle_private_mode_status(request: Request, user: User) -> dict:
    if user.is_private:
        return {"reply": "🔒 Neura is currently in Private Mode. I’m paused until you turn it off."}
    else:
        return {"reply": "✅ Neura is active and listening. Private Mode is OFF."}
