# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import logging
import time

from app.utils.schedulers.interaction_logs_cleanup import clean_old_interaction_logs
from app.utils.schedulers.generated_audio_cleanup import delete_old_audio_files
from app.utils.schedulers.notification_cleaner import delete_old_notification_logs
from app.utils.schedulers.daily_checkin_cleaner import clean_old_checkins
from app.utils.schedulers.message_memory_cleaner import delete_old_unimportant_messages
from app.utils.schedulers.journal_cleaner import clean_old_journal_entries
from app.utils.schedulers.goal_cleaner import clean_old_completed_goals
from app.utils.schedulers.habit_cleaner import clean_old_completed_habits
from app.utils.schedulers.cleanup_orphan_temp_audio import cleanup_orphan_temp_audio


logger = logging.getLogger("cleanup")

def run_all_cleanups():
    logger.info("🧹 Starting all cleanup tasks...")

    cleanup_tasks = [
        ("InteractionLogs", clean_old_interaction_logs),
        ("GeneratedAudio", delete_old_audio_files),
        ("DailyCheckins", clean_old_checkins),
        ("Notifications", delete_old_notification_logs),
        ("Messages", delete_old_unimportant_messages),
        ("JournalEntries", clean_old_journal_entries),
        ("CompletedGoals", clean_old_completed_goals),
        ("CompletedHabits", clean_old_completed_habits),
        ("OrphanTempAudio", cleanup_orphan_temp_audio)
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
