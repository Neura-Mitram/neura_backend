# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


def cleanup_audio_records(records, base_dir="/data/audio"):
    """
    Deletes files and records for any table storing a 'filename' or 'audio_file'.
    Accepts a list of ORM objects.
    """
    for record in records:
        # Determine which attribute to use
        rel_path = getattr(record, "filename", None) or getattr(record, "audio_file", None)
        if not rel_path:
            print(f"⚠️ No filename/audio_file on record {record}")
            continue

        file_path = os.path.join(base_dir, rel_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            os.remove(file_path)
            print(f"🗑️ Deleted file: {file_path}")
        else:
            print(f"⚠️ File missing: {file_path}")
