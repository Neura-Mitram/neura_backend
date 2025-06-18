import os
import time

def delete_old_audio_files(folder="/data/temp_audio", age_limit_minutes=15):
    now = time.time()
    cutoff = now - (age_limit_minutes * 60)

    if not os.path.exists(folder):
        return

    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        if os.path.isfile(filepath):
            file_modified_time = os.path.getmtime(filepath)
            if file_modified_time < cutoff:
                os.remove(filepath)
                print(f"🧹 Deleted old audio file: {filepath}")
