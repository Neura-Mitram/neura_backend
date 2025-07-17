# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from datetime import datetime
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.journal import JournalEntry
from app.models.notification import NotificationLog
from app.utils.audio_processor import synthesize_voice
from app.services.translation_service import translate
from app.utils.fcm_utils import send_fcm_push

from math import radians, cos, sin, sqrt, atan2
from geopy.geocoders import Nominatim
from app.services.search_service import search_wikipedia, search_duckduckgo, format_results_for_summary
from app.utils.ai_engine import generate_ai_reply

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points
    on the Earth surface in kilometers.
    """
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def haversine_km(lat1, lon1, lat2, lon2):
    return haversine_distance(lat1, lon1, lat2, lon2)


# For Location
async def get_location_details(lat, lon):
    try:
        geolocator = Nominatim(user_agent="neura-assistant")
        location = geolocator.reverse((lat, lon), timeout=5)
        if not location or not location.raw:
            return {}
        addr = location.raw.get("address", {})
        return {
            "state": addr.get("state"),
            "city": addr.get("city") or addr.get("town"),
            "area": addr.get("suburb") or addr.get("neighbourhood"),
            "street": addr.get("road")
        }
    except:
        return {}


# For Smart City Tips From AI + SEARCH + WIKI
async def generate_smart_city_tip(city: str, time_of_day: str = "morning", emotion: str = "joy") -> str:
    """
    Pulls wiki + web info for a city, and creates friendly travel tips using Mistral.
    """
    if not city:
        return "I don't have enough location info to offer city-specific tips right now."

    try:
        wiki_results = search_wikipedia(city, count=3)
        ddg_results = search_duckduckgo(city, count=3)
        merged = wiki_results + ddg_results
    except Exception:
        merged = []

    if not merged:
        return f"Welcome to {city.title()}! Stay safe and enjoy your time."

    # Build AI summarization prompt
    summary_prompt = format_results_for_summary(merged, city)
    enriched_prompt = (
        f"{summary_prompt}\n\n"
        f"Now write 3 warm, clear travel tips for someone who just arrived in {city.title()}.\n"
        f"Tone: helpful, local assistant.\n"
        f"Time: {time_of_day}\n"
        f"Emotion: {emotion}\n"
        f"Make it friendly, voice-first, and non-generic."
    )

    try:
        summary_text = generate_ai_reply(enriched_prompt)
        return summary_text.strip()
    except Exception:
        return f"Welcome to {city.title()}! Let me know if I can help while you're here."


# For Deliver Travel Tips + Voice + journal + voice notification
async def deliver_travel_tip(user: User, db: Session, lat: float, lon: float) -> dict:
    location = await get_location_details(lat, lon)
    city = location.get("city") or location.get("state") or "your area"
    user_lang = user.preferred_lang or "en"
    time_of_day = "morning" if 5 <= datetime.now().hour < 12 else "evening"
    user_emotion = user.emotion_status if user.emotion_status in ["joy", "anger", "fear", "sadness", "love",
                                                                  "surprise"] else "joy"

    tips_text_en = await generate_smart_city_tip(city=city, time_of_day=time_of_day, emotion=user_emotion)
    tips_text_final = translate(tips_text_en, source_lang="en",
                                target_lang=user_lang) if user_lang != "en" else tips_text_en

    voice_gender = user.voice if user.voice in ["male", "female"] else "male"
    tips_audio_url = synthesize_voice(tips_text_final, gender=voice_gender, lang=user_lang)

    # ✅ Send FCM push if available
    if user.fcm_token:
        try:
            send_fcm_push(
                token=user.fcm_token,
                title=f"Neura Travel Tip for {city}",
                body=tips_text_final[:120] + "..." if len(tips_text_final) > 120 else tips_text_final,
                data={
                    "type": "travel_tip",
                    "city": city,
                    "voice_stream": tips_audio_url
                }
            )
        except Exception as e:
            print(f"⚠️ FCM push failed for {user.id}: {e}")

    # 📓 Log travel moment in journal
    try:
        db.add(JournalEntry(
            user_id=user.id,
            entry_text=f"Reached {city or 'a new place'} 🧳",
            timestamp=datetime.utcnow()
        ))
    except:
        pass  # Safe skip

    # 🔔 Log as voice notification
    db.add(NotificationLog(
        user_id=user.id,
        notification_type="travel_voice_tip",
        content=f"{tips_text_final} [stream: {tips_audio_url}]",
        delivered=False,
        timestamp=datetime.utcnow()
    ))

    user.last_travel_tip_sent = datetime.utcnow()
    db.commit()

    return {
        "city": city,
        "tips": tips_text_final,
        "audio_url": tips_audio_url
    }