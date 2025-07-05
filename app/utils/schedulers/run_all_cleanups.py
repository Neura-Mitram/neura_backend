# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from app.utils.schedulers.interaction_logs_cleanup import clean_old_interaction_logs
from app.utils.schedulers.generated_audio_cleanup import delete_old_audio_files
from app.utils.schedulers.notification_cleaner import delete_old_notification_logs
from app.utils.schedulers.daily_checkin_cleaner import clean_old_checkins
from app.utils.schedulers.message_memory_cleaner import delete_old_unimportant_messages
from app.utils.schedulers.notifications_voice_cleaner import delete_old_voice_notifications


def run_all_cleanups():
    print("🧹 Starting all cleanup tasks...\n")
    clean_old_interaction_logs()
    delete_old_audio_files()
    clean_old_checkins()
    delete_old_notification_logs()
    delete_old_unimportant_messages()
    delete_old_voice_notifications()
    print("\n✅ All cleanup jobs completed.")
