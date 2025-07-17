# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import logging
import time

from app.utils.schedulers.cleanup.interaction_logs_cleanup import clean_old_interaction_logs
from app.utils.schedulers.cleanup.notification_cleaner import delete_old_notification_logs
from app.utils.schedulers.cleanup.daily_checkin_cleaner import clean_old_checkins
from app.utils.schedulers.cleanup.message_memory_cleaner import delete_old_unimportant_messages
from app.utils.schedulers.cleanup.journal_cleaner import clean_old_journal_entries
from app.utils.schedulers.cleanup.goal_cleaner import clean_old_completed_goals
from app.utils.schedulers.cleanup.habit_cleaner import clean_old_completed_habits
from app.utils.schedulers.cleanup.persona_trait_decay_cleaner import clean_old_persona_traits, decay_user_traits
from app.utils.schedulers.cleanup.mood_cleaner import clean_old_mood_logs
from app.utils.schedulers.cleanup.sos_cleaner import clean_old_sos_logs


logger = logging.getLogger("cleanup")

def run_all_cleanups():
    logger.info("🧹 Starting all cleanup tasks...")

    cleanup_tasks = [
        ("InteractionLogs", clean_old_interaction_logs),
        ("DailyCheckins", clean_old_checkins),
        ("Notifications", delete_old_notification_logs),
        ("Messages", delete_old_unimportant_messages),
        ("JournalEntries", clean_old_journal_entries),
        ("CompletedGoals", clean_old_completed_goals),
        ("CompletedHabits", clean_old_completed_habits),
        ("PersonaTraitDecay", clean_old_persona_traits),
        ("TraitScoreDecay", decay_user_traits),
        ("MoodLogs", clean_old_mood_logs),
        ("SOSLogs", clean_old_sos_logs)
    ]

    for name, func in cleanup_tasks:
        start = time.time()
        try:
            logger.info(f"🔹 Running cleanup: {name}")
            func()
            duration = round(time.time() - start, 2)
            logger.info(f"✅ Completed {name} cleanup in {duration} sec.")
        except Exception as e:
            logger.error(f"🛑 {name} cleanup failed: {e}", exc_info=True)

    logger.info("🎉 All cleanup jobs completed.")
