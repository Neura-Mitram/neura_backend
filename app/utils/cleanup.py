# utils/cleanup.py

import os
import time
from datetime import datetime, timedelta

def delete_old_audio_files(folder_path: str, max_age_minutes: int = 10):
    now = time.time()
    deleted_files = []

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and filename.endswith(".wav"):
            file_age = now - os.path.getmtime(file_path)
            if file_age > max_age_minutes * 60:
                os.remove(file_path)
                deleted_files.append(filename)

    if deleted_files:
        print(f"Deleted audio files: {deleted_files}")
