# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


RED_FLAG_KEYWORDS = [
    "show me your code",
    "source code",
    "backend code",
    "how you work",
    "how do you work",
    "internal logic",
    "share your code",
    "share backend",
    "reveal code",
    "tell me your code",
]

CREATOR_QUESTIONS = [
    "who created you",
    "who built you",
    "who programmed you",
    "who made you",
    "who is your creator",
    "who developed you",
    "who is your developer",
]

SELF_QUERY_KEYWORDS = [
    "who are you",
    "what can you do",
    "what do you do",
    "what are your features",
    "how can you help",
    "what is your purpose",
    "what's your job",
    "explain yourself",
    "tell me about yourself",
    "what is this app",
    "what are you"
]

# Keywords that suggest danger and trigger general SOS
EMERGENCY_KEYWORDS = [
    "help me", "i am scared", "emergency", "i need help", "call police",
    "i feel unsafe", "he is hitting me", "i am in danger", "someone is following me"
]

# Keywords that indicate *severe* threats (used for force launch)
SEVERE_KEYWORDS = [
    "rape", "murder", "acid", "kidnap", "molest",
    "hostage", "gun", "bleeding", "attacked", "danger"
]


def detect_red_flag(message: str) -> str | None:
    msg = message.lower()
    for keyword in RED_FLAG_KEYWORDS:
        if keyword in msg:
            return "code"
    for keyword in CREATOR_QUESTIONS:
        if keyword in msg:
            return "creator"
    for keyword in EMERGENCY_KEYWORDS:
        if keyword in msg:
            return "sos"
    for keyword in SELF_QUERY_KEYWORDS:
        if keyword in msg:
            return "self_query"
    return None
