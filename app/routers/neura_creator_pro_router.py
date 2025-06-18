from typing import List

from fastapi import APIRouter, Query, HTTPException, Header
from app.utils.ai_engine import generate_ai_reply
from app.utils.tier_check import ensure_minimum_tier

router = APIRouter()

@router.get("/neura/generate-caption")
def generate_caption(
    user_id: int = Query(..., description="User ID"),
    topic: str = Query(..., description="What is the post about?"),
    tone: str = Query("engaging", description="Tone like 'funny', 'emotional', 'motivational'")
):
    # ✅ Restrict access to Tier 3 and above
    ensure_minimum_tier(user_id, "Tier 3")

    prompt = f"Write 3 {tone} Instagram captions for this topic: {topic}. Make them concise, creative, and attention-grabbing. Include relevant emojis and hashtags where appropriate."

    try:
        captions = generate_ai_reply(prompt)
        return {
            "topic": topic,
            "tone": tone,
            "captions": captions.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate captions: {str(e)}")


@router.get("/neura/youtube-script")
def generate_youtube_script_v2(
    user_id: int = Query(..., description="User ID"),
    script_type: str = Query(..., description="Type: shorts, inspirational, educational, storytelling, listicle, case-study, book-summary, debunking"),
    topic: str = Query(..., description="Main topic of the video"),
    tone: str = Query("inspiring", description="e.g., stoic, emotional, casual, professional"),
    duration: str = Query("medium", description="short (1–2 min), medium (3–5 min), long (8–10 min)"),
    audience: str = Query("general", description="Target audience, e.g., creators, students, entrepreneurs")
):
    ensure_minimum_tier(user_id, "Tier 3")

    prompt = f"""
You are a professional YouTube scriptwriter and content strategist.

Write a full script for a YouTube video.

Details:
- Topic: {topic}
- Script Type: {script_type}
- Tone: {tone}
- Audience: {audience}
- Estimated Duration: {duration}

Requirements:
- Begin with a strong cinematic or reflective hook
- Structure it based on the script type. For example:
    - If "listicle": use numbered points
    - If "storytelling": follow a narrative arc
    - If "educational": explain clearly with logical flow
    - If "book-summary": highlight key insights with relatable language
    - If "debunking": present the myth, then counter with evidence
- Use human, mentor-like language
- Add voice modulation cues or pauses (e.g., “(pause)”, “(softly)”)
- End with a reflection or call-to-action
- Use clear formatting and line breaks

The script must feel authentic, not robotic. Make it emotionally engaging.
"""

    try:
        response = generate_ai_reply(prompt)
        return {
            "script_type": script_type,
            "topic": topic,
            "script": response.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")


@router.get("/neura/generate-draft")
def generate_long_form_draft(
    user_id: int = Query(..., description="User ID"),
    topic: str = Query(..., description="Topic for blog or LinkedIn post"),
    audience: str = Query("general", description="Target reader: creators, leaders, students, etc."),
    tone: str = Query("thoughtful", description="Tone like 'inspiring', 'professional', 'personal'")
):
    ensure_minimum_tier(user_id, "Tier 3")

    prompt = f"""
You are a personal storytelling expert for blog and LinkedIn content.

Write a 500-700 word draft on the topic: "{topic}"
Target audience: {audience}
Tone: {tone}

Structure:
1. Hooked Intro (1–2 lines that grab attention)
2. Personal-style body (insightful, informal, reflective)
3. Actionable or emotional outro (leaves an impression)

Make it sound human, like someone reflecting on life. Include paragraph breaks and natural flow.
"""

    try:
        post = generate_ai_reply(prompt)
        return {
            "topic": topic,
            "audience": audience,
            "tone": tone,
            "draft": post.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate draft: {str(e)}")

@router.post("/neura/seo-suggestions")
def seo_suggestions(
    user_id: int = Query(..., description="User ID"),
    platform: str = Query("blog", description="Platform: blog, youtube, instagram"),
    content: str = Query(..., description="Paste the content you want optimized")
):
    from utils.tier_check import ensure_minimum_tier
    from utils.ai_engine import generate_ai_reply

    ensure_minimum_tier(user_id, "Tier 3")

    prompt = f"""
You're an expert SEO assistant for online content creators.

Analyze the following content meant for {platform}.
Give me:
1. Top 5 SEO keyword suggestions
2. Recommended title ideas (SEO optimized)
3. Suggestions to improve structure, keyword density, or formatting

Content:
{content}

Be concise but actionable in your suggestions.
"""

    try:
        insights = generate_ai_reply(prompt)
        return {
            "platform": platform,
            "keywords_and_suggestions": insights.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate SEO suggestions: {str(e)}")

@router.post("/neura/email-helper")
def generate_email_helper(
    user_id: int = Header(..., description="User ID from mobile app"),
    use_case: str = Query(..., description="Type: reply, summarize, outreach, followup"),
    context: str = Query(...),
    tone: str = Query("professional"),
    goal: str = Query("clarify, close a deal, get a reply")
):

    ensure_minimum_tier(user_id, "Tier 3")

    prompt = f"""
You're an AI email assistant.

Email task: {use_case}
Tone: {tone}
Goal: {goal}

Input/context:
{context}

Write a full draft or response email.
If summarizing, keep it under 100 words. If replying, match the original sender's tone.
"""

    try:
        email_result = generate_ai_reply(prompt)
        return {
            "use_case": use_case,
            "generated_email": email_result.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email generation failed: {str(e)}")

@router.post("/neura/time-planner")
def time_block_planner(
    user_id: int = Header(...),
    tasks: List[str] = Query(..., description="List of tasks or goals"),
    total_hours: float = Query(8.0, description="Hours available today"),
    focus_mode: str = Query("balanced", description="Options: deep, flexible, balanced")
):
    from utils.tier_check import ensure_minimum_tier
    from utils.ai_engine import generate_ai_reply

    ensure_minimum_tier(user_id, "Tier 2")

    prompt = f"""
You're a time management coach.

Plan a smart time-block schedule for today.

- User's focus mode: {focus_mode}
- Total hours available: {total_hours}
- Tasks: {', '.join(tasks)}

Instructions:
- Prioritize tasks
- Suggest start/end times or durations
- Break large tasks if needed
- Include small breaks if focus mode is 'deep'
- Format the schedule clearly
"""

    try:
        plan = generate_ai_reply(prompt)
        return {
            "time_blocks": plan.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Time planning failed: {str(e)}")
