# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from app.models.notification import NotificationLog
from app.models.user import User
from app.utils.auth_utils import ensure_token_user_match

async def handle_notification_add(request: Request, db: Session, user: User, intent_payload: dict):
    try:
        # Ensure token-user match
        await ensure_token_user_match(request, user.id)

        notification_type = intent_payload.get("notification_type", "generic")

        # ✅ Validate notification type with a log
        valid_types = ["generic", "reminder", "tip", "system"]
        if notification_type not in valid_types:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Invalid notification type '{notification_type}' received. Falling back to 'generic'.")
            notification_type = "generic"

        content = intent_payload.get("content", "You have a new notification.")

        new_notification = NotificationLog(
            user_id=user.id,
            notification_type=notification_type,
            content=content,
            delivered=False
        )

        db.add(new_notification)
        db.commit()
        db.refresh(new_notification)

        return {
            "status": "success",
            "message": "Notification logged",
            "notification_id": new_notification.id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging notification: {str(e)}")
