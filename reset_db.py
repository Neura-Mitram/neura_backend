# reset_db.py
from app.models import database  # Make sure this imports your Base
from app.models.database import engine

if __name__ == "__main__":
    print("⚠️ Dropping all existing tables...")
    database.Base.metadata.drop_all(bind=engine)

    print("✅ Recreating tables from models...")
    database.Base.metadata.create_all(bind=engine)

    print("✅ Database reset complete.")
