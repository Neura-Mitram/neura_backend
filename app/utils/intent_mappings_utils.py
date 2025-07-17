# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


ALL_VALID_INTENTS = [
    "journal", "journal_list", "journal_delete", "journal_modify", "journal_weekly_summary",
    "checkin", "checkin_list", "checkin_delete", "checkin_modify", "checkin_weekly_summary",
    "habit", "habit_list", "habit_modify", "habit_delete", "habit_weekly_summary",
    "goal", "goal_list", "goal_modify", "goal_delete", "goal_weekly_summary",
    "mark_goal_completed", "mark_habit_completed",
    "mood", "mood_history", "summary", "nudge",
    "important_summary", "weekly_emotion_summary",
    "search", "qna_summary", "notification", "smart_reply", "update_device",
    "creator_mode", "creator_caption", "creator_content_ideas",
    "creator_weekly_plan", "creator_audience_helper", "creator_viral_reels",
    "creator_seo", "creator_email", "creator_time_planner",
    "creator_youtube_script", "creator_blog",
    "private_mode_toggle", "private_mode_status",
    "interpreter_mode",
    "fallback"
]

INTENT_ALIAS_MAP = {
    "be my interpreter": "interpreter_mode",
    "translate this": "interpreter_mode",
    "listen and translate": "interpreter_mode",
    "i need translation": "interpreter_mode",
    "interpret this conversation": "interpreter_mode",
    "act as interpreter": "interpreter_mode",
    "help me translate": "interpreter_mode",

    "start journaling": "journal",
    "show journals": "journal_list",
    "delete my journal": "journal_delete",
    "edit journal": "journal_modify",
    "weekly journal summary": "journal_weekly_summary",

    "check in with myself": "checkin",
    "list my check-ins": "checkin_list",
    "remove last check-in": "checkin_delete",
    "change my check-in": "checkin_modify",
    "check-in summary": "checkin_weekly_summary",

    "create a habit": "habit",
    "show habits": "habit_list",
    "change habit": "habit_modify",
    "delete a habit": "habit_delete",
    "how are my habits going": "habit_weekly_summary",

    "set a new goal": "goal",
    "list my goals": "goal_list",
    "update goal": "goal_modify",
    "remove a goal": "goal_delete",
    "weekly goal report": "goal_weekly_summary",

    "complete my habit": "mark_habit_completed",
    "mark goal done": "mark_goal_completed",

    "log my mood": "mood",
    "show mood history": "mood_history",

    "daily summary": "summary",
    "send a nudge": "nudge",
    "important things": "important_summary",
    "emotion this week": "weekly_emotion_summary",

    "search something": "search",
    "question summary": "qna_summary",
    "notify me": "notification",
    "smart suggestion": "smart_reply",
    "update my device": "update_device",

    "creator tools": "creator_mode",
    "write caption": "creator_caption",
    "content ideas": "creator_content_ideas",
    "weekly plan": "creator_weekly_plan",
    "grow my audience": "creator_audience_helper",
    "trending reels": "creator_viral_reels",
    "seo help": "creator_seo",
    "email draft": "creator_email",
    "time schedule": "creator_time_planner",
    "youtube script": "creator_youtube_script",
    "blog post": "creator_blog",

    "go private": "private_mode_toggle",
    "check private mode": "private_mode_status"
}

INTENT_EXAMPLES = [
    ("Neura, translate what they are saying in English", "interpreter_mode"),
    ("Can you help me build a habit of gratitude journaling?", "habit"),
    ("I want to see how my mood has been lately", "mood_history"),
    ("Turn on silent mode for now", "private_mode_toggle"),
    ("Am I currently in private mode?", "private_mode_status"),
    ("Please summarize my week", "summary"),
    ("Give me a friendly reminder to drink water", "notification"),
    ("What goals did I complete last week?", "goal_weekly_summary"),
    ("Delete my morning check-in", "checkin_delete"),
    ("Update my bedtime goal", "goal_modify"),
    ("Help me with content ideas for my skincare page", "creator_content_ideas"),
    ("Write a blog post about mindful eating", "creator_blog")
]
