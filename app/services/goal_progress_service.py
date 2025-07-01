from datetime import datetime, timedelta
from app.models.goal import Goal
from sqlalchemy.orm import Session

def update_goal_progress(goal: Goal, new_progress: int):
    """
    Updates progress and streak.
    Auto-completes if progress reaches 100%.
    """
    now = datetime.utcnow()

    # Validate range
    if not 0 <= new_progress <= 100:
        raise ValueError("Progress must be between 0 and 100")

    # Check if streak should increment
    if goal.last_progress_update:
        delta = now - goal.last_progress_update
        if delta.days == 1:
            goal.progress_streak_count += 1
        elif delta.days > 1:
            goal.progress_streak_count = 1
    else:
        goal.progress_streak_count = 1

    goal.progress_percent = new_progress
    goal.last_progress_update = now

    # Auto-complete
    if new_progress == 100:
        goal.status = "completed"
        goal.completed_at = now
