import os
import time
import logging

# Setup basic logging instead of print()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def delete_old_audio_files(folder: str = "/data/temp_audio", age_limit_minutes: int = 15) -> None:
    """
    Deletes audio files older than the specified age limit (in minutes) from the folder.
    Intended for temporary audio cleanup (e.g., from check-ins).
    """
    now = time.time()
    cutoff = now - (age_limit_minutes * 60)

    if not os.path.exists(folder):
        logging.warning(f"Folder not found: {folder}")
        return

    deleted_count = 0

    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        if os.path.isfile(filepath):
            try:
                file_modified_time = os.path.getmtime(filepath)
                if file_modified_time < cutoff:
                    os.remove(filepath)
                    logging.info(f"🧹 Deleted old audio file: {filepath}")
                    deleted_count += 1
            except Exception as e:
                logging.error(f"Failed to delete {filepath}: {e}")

    if deleted_count == 0:
        logging.info("No old audio files to delete.")
