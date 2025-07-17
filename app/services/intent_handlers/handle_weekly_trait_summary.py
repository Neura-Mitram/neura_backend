# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import Request
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.trait_summary_service import generate_weekly_trait_summary

async def handle_weekly_trait_summary(request: Request, user: User, message: str, db: Session):
    try:
        summary_text = generate_weekly_trait_summary(user, db)
        return {
            "status": "success",
            "intent": "trait_summary",
            "reply": summary_text
        }
    except Exception as e:
        return {
            "status": "error",
            "intent": "trait_summary",
            "message": "Failed to generate summary.",
            "detail": str(e)
        }
