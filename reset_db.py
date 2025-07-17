from sqlalchemy import text
from app.models.database import engine

print("⚠️ Dropping and recreating schema...")

with engine.begin() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))

print("✅ Database schema reset successfully.")
