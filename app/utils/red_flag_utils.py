# app/utils/red_flag_utils.py

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


def detect_red_flag(message: str) -> str | None:
    msg = message.lower()
    for keyword in RED_FLAG_KEYWORDS:
        if keyword in msg:
            return "code"
    for keyword in CREATOR_QUESTIONS:
        if keyword in msg:
            return "creator"
    return None
