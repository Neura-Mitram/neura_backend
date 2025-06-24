from typing import List

from app.utils.ai_engine import generate_ai_reply
from app.utils.tier_check import ensure_minimum_tier
from pydantic import BaseModel
from app.models.user_model import TierLevel
from app.utils.auth_utils import ensure_token_user_match, require_token
from fastapi import APIRouter, Query, HTTPException, Header, Depends, Request

from app.utils.rate_limit_utils import get_tier_limit, limiter

router = APIRouter()

class CaptionRequest(BaseModel):
    user_id: int
    topic: str
    tone: str = "engaging"
@router.post("/neura/generate-caption")
@limiter.limit(get_tier_limit)
def generate_caption(
    request: Request, payload: CaptionRequest, user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.user_id)

    # ✅ Restrict access to pro
    ensure_minimum_tier(payload.user_id, TierLevel.pro)  # ✅

    prompt = f"Write 3 {payload.tone} Instagram captions for this topic: {payload.topic}. Make them concise, creative, and attention-grabbing. Include emojis and hashtags."

    try:
        captions = generate_ai_reply(prompt)
        return {
            "topic": payload.topic,
            "tone": payload.tone,
            "captions": captions.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate captions: {str(e)}")


class YouTubeScriptRequest(BaseModel):
    user_id: int
    script_type: str
    topic: str
    tone: str = "inspiring"
    duration: str = "medium"
    audience: str = "general"
@router.post("/neura/youtube-script")
@limiter.limit(get_tier_limit)
def generate_youtube_script_v2(
    request: Request, payload: YouTubeScriptRequest, user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.user_id)

    ensure_minimum_tier(payload.user_id, TierLevel.pro)  # ✅

    prompt = f"""
You are a professional YouTube scriptwriter and content strategist.

Write a full script for a YouTube video.

Details:
- Topic: {payload.topic}
- Script Type: {payload.script_type}
- Tone: {payload.tone}
- Audience: {payload.audience}
- Estimated Duration: {payload.duration}

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
            "script_type": payload.script_type,
            "topic": payload.topic,
            "script": response.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")


class DraftRequest(BaseModel):
    user_id: int
    topic: str
    audience: str = "general"
    tone: str = "thoughtful"
@router.post("/neura/generate-blog")
@limiter.limit(get_tier_limit)
def generate_long_form_blog(
    request: Request, payload: DraftRequest, user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.user_id)

    ensure_minimum_tier(payload.user_id, TierLevel.pro)  # ✅

    prompt = f"""
You are a personal storytelling expert for blog and LinkedIn content.

Write a 500-700 word draft on the topic: "{payload.topic}"
Target audience: {payload.audience}
Tone: {payload.tone}

Structure:
1. Hooked Intro (1–2 lines that grab attention)
2. Personal-style body (insightful, informal, reflective)
3. Actionable or emotional outro (leaves an impression)

Make it sound human, like someone reflecting on life. Include paragraph breaks and natural flow.
"""

    try:
        post = generate_ai_reply(prompt)
        return {
            "topic": payload.topic,
            "audience": payload.audience,
            "tone": payload.tone,
            "draft": post.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate draft: {str(e)}")


class SEORequest(BaseModel):
    user_id: int
    platform: str = "blog"
    content: str
@router.post("/neura/seo-suggestions")
@limiter.limit(get_tier_limit)
def seo_suggestions(
    request: Request, payload: SEORequest, user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.user_id)

    ensure_minimum_tier(payload.user_id, TierLevel.pro)  # ✅

    prompt = f"""
You're an expert SEO assistant for online content creators.

Analyze the following content meant for {payload.platform}.
Give me:
1. Top 5 SEO keyword suggestions
2. Recommended title ideas (SEO optimized)
3. Suggestions to improve structure, keyword density, or formatting

Content:
{payload.content}

Be concise but actionable in your suggestions.
"""

    try:
        insights = generate_ai_reply(prompt)
        return {
            "platform": payload.platform,
            "keywords_and_suggestions": insights.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate SEO suggestions: {str(e)}")


class EmailRequest(BaseModel):
    user_id: int
    use_case: str
    context: str
    tone: str = "professional"
    goal: str = "clarify, close a deal, get a reply"
@router.post("/neura/email-helper")
@limiter.limit(get_tier_limit)
def generate_email_helper(
    request: Request, payload: EmailRequest, user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.user_id)

    ensure_minimum_tier(payload.user_id, TierLevel.pro)  # ✅

    prompt = f"""
You're an AI email assistant.

Email task: {payload.use_case}
Tone: {payload.tone}
Goal: {payload.goal}

Input/context:
{payload.context}

Write a full draft or response email.
If summarizing, keep it under 100 words. If replying, match the original sender's tone.
"""

    try:
        email_result = generate_ai_reply(prompt)
        return {
            "use_case": payload.use_case,
            "generated_email": email_result.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email generation failed: {str(e)}")


class TimePlannerRequest(BaseModel):
    user_id: int
    tasks: List[str]
    total_hours: float = 8.0
    focus_mode: str = "balanced"
@router.post("/neura/time-planner")
@limiter.limit(get_tier_limit)
def time_block_planner(
    request: Request, payload: TimePlannerRequest, user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.user_id)

    ensure_minimum_tier(payload.user_id, TierLevel.pro)  # ✅

    prompt = f"""
                    You're a time management coach.
                    
                    Plan a smart time-block schedule for today.
                    
                    - User's focus mode: {payload.focus_mode}
                    - Total hours available: {payload.total_hours}
                    - Tasks: {', '.join(payload.tasks)}
                    
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