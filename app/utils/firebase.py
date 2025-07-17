# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


import firebase_admin
from firebase_admin import credentials, messaging
import os, json

# ✅ Initialize Firebase from JSON string in environment
if not firebase_admin._apps:
    raw_json = os.getenv("FIREBASE_ADMIN_JSON")
    if not raw_json:
        raise ValueError("FIREBASE_ADMIN_JSON is not set")

    cred_dict = json.loads(raw_json)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

def send_fcm_push(token: str, title: str, body: str, data: dict = {}):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        token=token,
        data=data  # optional key-value map for deep linking
    )
    return messaging.send(message)