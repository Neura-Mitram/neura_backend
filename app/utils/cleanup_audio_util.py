# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import os
import logging

logger = logging.getLogger("cleanup")

def cleanup_audio_records(records, base_dir="/data/audio"):
    """
    Deletes files for any table storing a 'filename' or 'audio_file'.
    Accepts a list of ORM objects.
    """
    for record in records:
        rel_path = getattr(record, "filename", None) or getattr(record, "audio_file", None)
        if not rel_path:
            logger.warning(f"No filename/audio_file on record {record}")
            continue

        file_path = os.path.join(base_dir, rel_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete file {file_path}: {e}")
        else:
            logger.warning(f"File missing: {file_path}")
