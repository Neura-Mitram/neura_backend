# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.



import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("cleanup")

def cleanup_orphan_temp_audio():
    folder = "/data/audio/temp_audio"
    cutoff = datetime.utcnow() - timedelta(hours=1)

    deleted_count = 0
    for fname in os.listdir(folder):
        path = os.path.join(folder, fname)
        if os.path.isfile(path):
            mtime = datetime.utcfromtimestamp(os.path.getmtime(path))
            if mtime < cutoff:
                try:
                    os.remove(path)
                    logger.info(f"🗑️ Deleted orphan temp audio: {path}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete {path}: {e}")

    logger.info(f"✅ Orphan temp audio cleanup complete: {deleted_count} files deleted.")
