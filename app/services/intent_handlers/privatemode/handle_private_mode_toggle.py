# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import Request
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.user import User

def handle_private_mode_toggle(request: Request, user: User, message: str, db: Session) -> dict:
    turning_on = "on" in message.lower() or "enable" in message.lower() or "activate" in message.lower()

    if turning_on:
        user.is_private = True
        user.last_private_on = datetime.utcnow()
        db.commit()
        return {"reply": "🔒 Private mode is now ON. Neura will stay silent until you turn it off."}
    else:
        user.is_private = False
        user.last_private_on = None
        db.commit()
        return {"reply": "🔓 Private mode is now OFF. Neura is fully active again."}
