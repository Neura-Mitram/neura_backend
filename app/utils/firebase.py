# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import os
import json
import firebase_admin
from firebase_admin import credentials, messaging

# ✅ Detect and initialize Firebase only once
if not firebase_admin._apps:
    raw_json = os.getenv("FIREBASE_ADMIN_JSON")

    if not raw_json:
        raise ValueError("FIREBASE_ADMIN_JSON is not set in environment variables")

    try:
        if raw_json.strip().startswith("{"):
            # 🧠 Stringified JSON (e.g., Hugging Face Space)
            cred_dict = json.loads(raw_json)
            cred = credentials.Certificate(cred_dict)
        else:
            # 🧪 Local path to JSON (for dev)
            cred = credentials.Certificate(raw_json)

        firebase_admin.initialize_app(cred)

    except Exception as e:
        raise RuntimeError("❌ Failed to initialize Firebase Admin SDK") from e


def send_fcm_push(token: str, title: str, body: str, data: dict = {}):
    """
    Send a push notification via FCM.
    """
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=token,
        data=data
    )
    return messaging.send(message)
