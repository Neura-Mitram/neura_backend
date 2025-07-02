from app.models.habit import Habit
from app.models.database import SessionLocal
from datetime import datetime

def handle_habit_modify(user, habit_id, updates):
    db = SessionLocal()
    habit = db.query(Habit).filter_by(user_id=user.id, id=habit_id).first()
    if not habit:
        return {"error": "Habit not found."}

    if "status" in updates:
        habit.status = updates["status"]
        if updates["status"] == "completed":
            now = datetime.utcnow()
            if habit.last_completed:
                days_since = (now.date() - habit.last_completed.date()).days
                if days_since == 1:
                    habit.streak_count = (habit.streak_count or 0) + 1
                else:
                    habit.streak_count = 1
            else:
                habit.streak_count = 1

            habit.last_completed = now

    if "habit_name" in updates:
        habit.habit_name = updates["habit_name"]

    db.commit()
    return {"message": "✅ Habit updated successfully."}
