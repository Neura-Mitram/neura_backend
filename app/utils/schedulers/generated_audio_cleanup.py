# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.database import SessionLocal
from app.models.generated_audio import GeneratedAudio
from app.models.user import User
from app.utils.cleanup_audio_util import cleanup_audio_records
from app.utils.tier_logic import (
    get_user_audio_file_retention_days,
    get_user_metadata_retention_days
)
import logging

logger = logging.getLogger("cleanup")

def delete_old_audio_files():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            tier = user.tier.value if user.tier else "free"
            file_days = get_user_audio_file_retention_days(user)
            data_days = get_user_metadata_retention_days(user)

            file_cutoff = datetime.utcnow() - timedelta(days=file_days)

            # 1️⃣ Always delete old files
            old_files = db.query(GeneratedAudio).filter(
                GeneratedAudio.user_id == user.id,
                GeneratedAudio.created_at < file_cutoff
            ).all()
            cleanup_audio_records(old_files)

            # 2️⃣ Delete metadata if policy allows
            if data_days:
                data_cutoff = datetime.utcnow() - timedelta(days=data_days)
                count = (
                    db.query(GeneratedAudio)
                    .filter(
                        GeneratedAudio.user_id == user.id,
                        GeneratedAudio.created_at < data_cutoff
                    )
                    .delete(synchronize_session=False)
                )
                logger.info(f"🗑️ User {user.id} ({tier}) - Deleted {count} metadata records older than {data_days} days.")
            else:
                logger.info(f"✅ User {user.id} ({tier}) - Metadata retained indefinitely.")

        db.commit()
        logger.info("✅ GeneratedAudio cleanup completed.")

    except Exception as e:
        logger.error(f"🛑 GeneratedAudio cleanup failed: {e}", exc_info=True)
    finally:
        db.close()
