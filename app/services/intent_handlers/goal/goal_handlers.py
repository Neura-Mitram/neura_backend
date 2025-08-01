# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from app.models.goal import Goal
from app.models.database import SessionLocal
from datetime import datetime
from app.services.goal_progress_service import update_goal_progress
from app.utils.usage_tracker import track_usage_event

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
    track_usage_event(db, user, category="goal_mark_completed")

    return {"message": "Goal updated successfully."}
