from app.models.goal import Goal
from app.database import SessionLocal
from datetime import datetime
from app.services.goal_progress_service import update_goal_progress

def handle_goal_modify(user, goal_id, updates):
    db = SessionLocal()
    goal = db.query(Goal).filter_by(user_id=user.id, id=goal_id).first()
    if not goal:
        return {"error": "Goal not found."}

    if "status" in updates:
        goal.status = updates["status"]
        if updates["status"] == "completed":
            goal.completed_at = datetime.utcnow()

    if "goal_text" in updates:
        goal.goal_text = updates["goal_text"]
    if "progress_percent" in updates:
        update_goal_progress(goal, int(updates["progress_percent"]))

    db.commit()
    return {"message": "Goal updated successfully."}
