from sqlalchemy import text
from app.models.database import engine

print("⚠️ Dropping and recreating schema...")
with engine.connect() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    conn.commit()

print("✅ Done.")
