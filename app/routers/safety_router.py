# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.



from fastapi import APIRouter, Request, Form, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from collections import defaultdict

from app.models.database import SessionLocal
from app.models.user import User
from app.models.sos import SOSLog, UnsafeAreaReport
from app.models.sos_contact import SOSContact
from app.models.safety import UnsafeClusterPing

from app.utils.auth_utils import require_token, ensure_token_user_match
from app.schemas.safety_schemas import (
    SOSContactAddRequest,
    SOSContactDeleteRequest,
    SOSContactListRequest,
    UnsafeAreaReportRequest,
    SosAlertLogRequest,
    ImSafeLogRequest,
    UnsafeAreaClusterPingRequest,
    MyReportsRequest
)
from app.services.safety_notifier import notify_nearby_users
from app.utils.tier_logic import is_pro_user, is_event_trigger_allowed, get_user_metadata_retention_days
from app.utils.location_utils import haversine_km, get_location_details
from app.utils.ai_engine import generate_ai_reply
from app.utils.persona_prompt_wrapper import inject_persona_into_prompt
from app.services.translation_service import translate
from app.utils.voice_sender import synthesize_voice
from app.utils.firebase import send_fcm_push
from app.utils.voice_sender import send_voice_to_neura
from app.utils.location_utils import haversine_distance


router = APIRouter()

# ---------------------- DB SESSION ----------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------- 🚨 SOS ALERT ----------------------
@router.post("/sos-alert")
async def sos_alert(
    request: Request,
    device_id: str = Form(...),
    message: str = Form(...),
    location: str = Form(None),
    latitude: float = Form(None),
    longitude: float = Form(None),
    trigger_sos_force: bool = Form(False),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    """
    Triggered when Neura detects an SOS keyword like "rape", "murder", etc.
    Stores the alert in DB and optionally triggers frontend actions.
    """
    ensure_token_user_match(user_data["sub"], device_id)

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if latitude is not None and longitude is not None:
        user.last_lat = latitude
        user.last_lon = longitude
        db.commit()

    await notify_nearby_users(user, db, request)

    log = SOSLog(
        user_id=user.id,
        message=message,
        location=location,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()

    # 📞 Fetch SOS contacts for SMS forwarding
    contacts = db.query(SOSContact).filter(SOSContact.device_id == user.temp_uid).all()
    sms_contacts = [{"name": c.name, "phone": c.phone} for c in contacts]


    # 🚨 Base confirmation text
    base_text = "Your SOS alert was received. Help is on the way. Please stay safe."

    # 🌐 Translate if needed
    user_lang = user.preferred_lang or "en"
    final_text = translate(base_text, source_lang="en", target_lang=user_lang) if user_lang != "en" else base_text

    # 🔊 Generate voice file
    try:
        audio_url = synthesize_voice(
            text=final_text,
            gender=user.voice or "female",
            emotion=user.emotion_status or "unknown",
            lang=user.preferred_lang or "en"
        )
    except Exception as e:
        audio_url = None


    # 📲 Send FCM confirmation to the triggering user
    if user.fcm_token:
        send_fcm_push(
            token=user.fcm_token,
            title="🚨 SOS Alert Sent",
            body=final_text,
            data={"screen": "sos", "origin": "self_trigger"}
        )

    # Build tier-based response
    response = {
        "success": True,
        "msg": "🚨 SOS alert saved.",
        "timestamp": log.timestamp.isoformat(),
        "trigger_sos_force": trigger_sos_force,
        "show_sos_screen": True,
        "auto_sms": trigger_sos_force,
        "background_mic": trigger_sos_force and is_event_trigger_allowed(user),
        "proof_log": trigger_sos_force and is_pro_user(user),
        "audio_url": audio_url,
        "sos_contacts": sms_contacts
    }

    return response

# ---------------------- 📋 SOS ALERT LOG ----------------------
@router.post("/safety/log-sos-alert")
async def log_sos_alert(
    request: Request,
    payload: SosAlertLogRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

        # 1️⃣ Save to SOSLog
    log = SOSLog(
        user_id=user.id,
        message=payload.message,
        emotion=payload.emotion,
        timestamp=payload.timestamp or datetime.utcnow()
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # 2️⃣ Voice confirmation for triggering user
    base_text = "SOS alert triggered. I'm with you. Stay calm and help is coming."
    user_lang = user.preferred_lang or "en"
    final_text = translate(base_text, source_lang="en", target_lang=user_lang) if user_lang != "en" else base_text

    try:
        await send_voice_to_neura(
            request=request,
            device_id=payload.device_id,
            text=final_text,
            gender=user.voice or "female",
            emotion=user.emotion_status or "unknown",
            lang=user.preferred_lang or "en"
        )
    except Exception as e:
        print(f"⚠️ Failed to send voice confirmation: {e}")

    # 3️⃣ Notify nearby users
    try:
        await notify_nearby_users(user, db, request)
    except Exception as e:
        print(f"⚠️ Failed to notify nearby users: {e}")

    # 📞 Fetch SOS contacts for SMS forwarding
    contacts = db.query(SOSContact).filter(SOSContact.device_id == user.temp_uid).all()
    sms_contacts = [{"name": c.name, "phone": c.phone} for c in contacts]

    return {
        "success": True,
        "log_id": log.id,
        "voice_sent": True,
        "sos_contacts": sms_contacts  # ✅ for frontend
    }


# ---------------------- 📋 IAM-SAFE ALERT LOG ----------------------
@router.post("/safety/im-safe")
async def mark_user_safe(
    request: Request,
    payload: ImSafeLogRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    # ✅ Auth check
    ensure_token_user_match(user_data["sub"], payload.device_id)

    # ✅ Fetch user
    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # 1️⃣ Save "I'm Safe" log
    log = SOSLog(
        user_id=user.id,
        source="manual_safe",
        message=payload.status,
        location=payload.location,
        emotion="safe",
        timestamp=payload.timestamp
    )
    db.add(log)
    db.commit()

    # 2️⃣ Voice Confirmation for self
    try:
        await send_voice_to_neura(
            request=request,
            device_id=payload.device_id,
            text="✅ Marked safe. Thank you for confirming. Stay protected.",
            gender=user.voice or "female",
            emotion="surprise",
            lang=user.preferred_lang or "en"
        )
    except Exception:
        pass

    # 3️⃣ Notify Nearby Users: Reverse Alert
    try:
        lat1, lon1 = user.last_lat, user.last_lon
        if lat1 and lon1:
            nearby_users = db.query(User).filter(
                User.id != user.id,
                User.safety_alert_optin == True,
                User.last_lat.isnot(None),
                User.last_lon.isnot(None)
            ).all()

            for other_user in nearby_users:
                dist = haversine_distance(lat1, lon1, other_user.last_lat, other_user.last_lon)
                if dist <= 2.0:
                    # 🔔 Push Notification
                    if other_user.fcm_token:
                        send_fcm_push(
                            token=other_user.fcm_token,
                            title="🟢 Nearby Safety Update",
                            body="A previously triggered SOS has now been marked safe.",
                            data={"screen": "sos_alert", "trigger_type": "resolved"}
                        )
                    # 🔊 Voice Reassurance
                    try:
                        await send_voice_to_neura(
                            request=request,
                            device_id=other_user.temp_uid,
                            text="🟢 Nearby alert cleared. The person is now safe.",
                            gender=other_user.voice or "male",
                            emotion="surprise",
                            lang=other_user.preferred_lang or "en"
                        )

                    except Exception:
                        pass
    except Exception as e:
        print(f"[WARN] Failed nearby safe alert: {e}")

    # ✅ Done
    return {"success": True, "message": "Marked safe and nearby users updated."}



# ---------------------- 📋 REPORT UNSAFE AREAS ----------------------
@router.post("/safety/report-unsafe-area")
async def report_unsafe_area(
    request: Request,
    payload: UnsafeAreaReportRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    report = UnsafeAreaReport(
        user_id=user.id,
        location=payload.location,
        reason=payload.reason,
        description=payload.description
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "success": True,
        "report_id": report.id,
        "timestamp": report.timestamp.isoformat(),
        "message": "Report logged successfully."
    }


# ---------------------- 🔴 CLUSTER PING: REPORT UNSAFE AREA ----------------------
@router.post("/safety/cluster-ping")
async def log_cluster_ping(
    request: Request,
    payload: UnsafeAreaClusterPingRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    ping = UnsafeClusterPing(
        user_id=user.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        timestamp=payload.timestamp,
    )
    db.add(ping)
    db.commit()
    db.refresh(ping)

    return {
        "success": True,
        "ping_id": ping.id,
        "message": "Cluster ping logged successfully."
    }


# ---------------------- 📡 GET NEARBY UNSAFE CLUSTER PINGS ----------------------
@router.get("/safety/nearby-pings")
async def get_nearby_cluster_pings(
    request: Request,
    latitude: float = Query(...),
    longitude: float = Query(...),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    cutoff = datetime.utcnow() - timedelta(minutes=15)

    recent_pings = db.query(UnsafeClusterPing).filter(
        UnsafeClusterPing.timestamp >= cutoff
    ).all()

    nearby = []
    for ping in recent_pings:
        distance_km = haversine_km(latitude, longitude, ping.latitude, ping.longitude)
        if distance_km <= 1.0:
            nearby.append({
                "id": ping.id,
                "latitude": ping.latitude,
                "longitude": ping.longitude,
                "timestamp": ping.timestamp.isoformat(),
                "user_id": ping.user_id,
                "distance_km": round(distance_km, 2)
            })

    return {
        "count": len(nearby),
        "nearby_pings": nearby
    }


# ---------------------- 📋 FETCH MY UNSAFE REPORTS ----------------------
@router.post("/safety/my-reports")
async def get_user_unsafe_reports(
    payload: MyReportsRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    user = db.query(User).filter(User.temp_uid == payload.device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    reports = db.query(UnsafeAreaReport).filter(UnsafeAreaReport.user_id == user.id).order_by(UnsafeAreaReport.timestamp.desc()).all()

    return {
        "success": True,
        "count": len(reports),
        "reports": [
            {
                "id": r.id,
                "reason": r.reason,
                "description": r.description,
                "location": r.location,
                "timestamp": r.timestamp.isoformat()
            } for r in reports
        ]
    }


# ---------------------- ❌ DELETE UNSAFE REPORT ----------------------
@router.post("/safety/delete-report")
async def delete_unsafe_report(
    device_id: int = Form(...),
    report_id: int = Form(...),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], device_id)

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    report = db.query(UnsafeAreaReport).filter(
        UnsafeAreaReport.id == report_id,
        UnsafeAreaReport.user_id == user.id
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found or unauthorized.")

    db.delete(report)
    db.commit()

    return {"success": True, "message": "Report deleted successfully."}


# ---------------------- 📍 NEARBY GEO JUMP FOR MY REPORTS ----------------------
@router.get("/safety/nearest-location")
async def get_user_nearest_location(
    latitude: float = Query(...),
    longitude: float = Query(...),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    # For now, return coordinates as dummy area (frontend handles reverse geocoding)
    return {
        "latitude": latitude,
        "longitude": longitude,
        "message": "Location received. Use reverse geocoding on frontend to match section."
    }

# --------- 🗺️ UNSAFE SUMMARY (MY ONLY) ---------
@router.post("/safety/unsafe-summary")
async def generate_unsafe_summary(
    request: Request,
    device_id: int = Form(...),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], device_id)

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    reports = db.query(UnsafeAreaReport).filter(UnsafeAreaReport.user_id == user.id).order_by(UnsafeAreaReport.timestamp.desc()).limit(30).all()

    if not reports:
        return {"success": True, "summary": "No reports to summarize."}

    prompt_lines = [f"{i+1}. Location: {r.location or 'Unknown'} | Reason: {r.reason} | Time: {r.timestamp.strftime('%I:%M %p')}" for i, r in enumerate(reports)]

    prompt = (
        "Given the following unsafe area reports submitted by a user, summarize the key patterns in 2 lines. "
        "Mention location, time pattern (if visible), and types of issues.\n\nReports:\n" +
        "\n".join(prompt_lines) + "\n\nSummary:"
    )

    # 🔁 Call Mistral
    summary_en = generate_ai_reply(inject_persona_into_prompt(prompt, user, db))
    user_lang = user.preferred_lang or "en"
    summary_final = translate(summary_en, "en", user_lang) if user_lang != "en" else summary_en

    try:
        audio_url = synthesize_voice(
            text=summary_final,
            gender=user.voice or "female",
            emotion=user.emotion_status or "unknown",
            lang=user_lang
        )
    except Exception:
        audio_url = None

    return {"success": True, "summary": summary_final, "audio_url": audio_url}


# --------- 🗺️ COMMUNITY REPORTS (ALL USERS) ---------
@router.get("/safety/community-reports")
async def get_community_reports(
    request: Request,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    user = db.query(User).filter(User.temp_uid == user_data["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    retention_days = get_user_metadata_retention_days(user)
    cutoff = datetime.utcnow() - timedelta(days=retention_days)

    recent_reports = db.query(UnsafeAreaReport).filter(
        UnsafeAreaReport.timestamp >= cutoff
    ).order_by(UnsafeAreaReport.timestamp.desc()).limit(300).all()

    # Grouped: state → city → area → street → [reports]
    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    for r in recent_reports:
        lat, lon = r.latitude, r.longitude
        loc = await get_location_details(lat, lon) if (lat and lon) else {}

        state = loc.get("state", "Unknown State")
        city = loc.get("city", "Unknown City")
        area = loc.get("area", "Unknown Area")
        street = loc.get("street", "Unknown Street")

        grouped[state][city][area][street].append({
            "id": r.id,
            "user_id": r.user_id,
            "reason": r.reason,
            "location": r.location,
            "timestamp": r.timestamp.isoformat(),
        })

    return {
        "success": True,
        "retention_days": retention_days,
        "grouped_reports": grouped
    }

# ---------------------- 🧠 COMMUNITY UNSAFE SUMMARY ----------------------
@router.post("/safety/community-summary")
async def generate_community_summary(
    request: Request,
    device_id: int = Form(...),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    # Validate user
    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Get last 100 reports across all users
    reports = db.query(UnsafeAreaReport).order_by(UnsafeAreaReport.timestamp.desc()).limit(100).all()

    if not reports:
        return {"success": True, "summary": "No community reports available yet."}

    prompt_lines = [
        f"{i+1}. Location: {r.location or 'Unknown'} | Reason: {r.reason} | Time: {r.timestamp.strftime('%I:%M %p')}"
        for i, r in enumerate(reports)
    ]

    prompt = (
        "You're analyzing unsafe reports from the community. Find patterns by region, common reasons, and time clusters."
        " Output in 3 lines."
        "\n\nReports:\n" + "\n".join(prompt_lines) + "\n\nSummary:"
    )

    summary_en = generate_ai_reply(inject_persona_into_prompt(prompt, user, db))
    user_lang = user.preferred_lang or "en"
    summary_final = translate(summary_en, "en", user_lang) if user_lang != "en" else summary_en

    try:
        audio_url = synthesize_voice(
            text=summary_final,
            gender=user.voice or "female",
            emotion=user.emotion_status or "unknown",
            lang=user_lang
        )
    except Exception:
        audio_url = None

    return {"success": True, "summary": summary_final, "audio_url": audio_url}

# ---------------------- 🧠 COMMUNITY AREA CHECK ----------------------
@router.post("/safety/cluster-check")
async def get_unsafe_clusters_near_user(
    request: Request,
    payload: dict,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    device_id = payload.get("device_id")
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")

    ensure_token_user_match(user_data["sub"], device_id)

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    retention_days = get_user_metadata_retention_days(user)
    cutoff = datetime.utcnow() - timedelta(days=retention_days)

    all_reports = db.query(UnsafeAreaReport).filter(UnsafeAreaReport.timestamp >= cutoff).all()

    nearby_clusters = defaultdict(list)

    for r in all_reports:
        if r.latitude is None or r.longitude is None:
            continue
        distance = haversine_km(latitude, longitude, r.latitude, r.longitude)
        if distance <= 2.0:
            key = f"{r.location or 'Unknown'}"
            nearby_clusters[key].append({
                "reason": r.reason,
                "location": r.location,
                "timestamp": r.timestamp.isoformat(),
                "distance_km": round(distance, 2)
            })

    sorted_clusters = sorted(
        nearby_clusters.items(),
        key=lambda kv: len(kv[1]),
        reverse=True
    )

    top_clusters = [
        {
            "location": k,
            "report_count": len(v),
            "latest": max(x["timestamp"] for x in v),
            "reports": v
        }
        for k, v in sorted_clusters[:3] if len(v) >= 2
    ]

    return {
        "success": True,
        "clusters_found": len(top_clusters),
        "clusters": top_clusters
    }

# ---------------------- 🧠 SAFE ROUTE SUGGESTION ----------------------
@router.post("/safety/safe-route")
async def get_safe_route_suggestion_with_ai(
    request: Request,
    device_id: int = Form(...),
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], device_id)

    user = db.query(User).filter(User.temp_uid == device_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    cutoff = datetime.utcnow() - timedelta(days=5)
    recent_reports = db.query(UnsafeAreaReport).filter(
        UnsafeAreaReport.timestamp >= cutoff,
        UnsafeAreaReport.location != None
    ).all()

    location_counts = {}
    for report in recent_reports:
        loc = report.location.strip()
        if loc:
            location_counts[loc] = location_counts.get(loc, 0) + 1

    def risk_level(count):
        if count <= 2:
            return 'low'
        elif count <= 5:
            return 'medium'
        else:
            return 'high'

    route_suggestions = [
        {
            "location": loc,
            "risk": risk_level(count),
            "warning": f"{count} incidents"
        }
        for loc, count in location_counts.items()
    ]

    # Sort safest first
    ordered = sorted(route_suggestions, key=lambda r: {'low': 0, 'medium': 1, 'high': 2}[r["risk"]])
    final_route = ordered[:10]

    # ---------------------- 🧠 AI TIPS ----------------------
    if not final_route:
        return {"success": True, "route": [], "ai_tip": "No route suggestions available."}

    lines = [
        f"{i+1}. {r['location']} — {r['risk'].capitalize()} Risk ({r['warning']})"
        for i, r in enumerate(final_route)
    ]

    prompt = (
        "Given the following route with risk levels, generate 2-line tips for travelers."
        " Mention safest zones, any hotspots to avoid, and how to plan wisely.\n\n"
        "Route:\n" + "\n".join(lines) + "\n\nTips:"
    )

    summary_en = generate_ai_reply(inject_persona_into_prompt(prompt, user, db))
    user_lang = user.preferred_lang or "en"
    summary_translated = translate(summary_en, "en", user_lang) if user_lang != "en" else summary_en

    try:
        audio_url = synthesize_voice(
            text=summary_translated,
            gender=user.voice or "female",
            emotion=user.emotion_status or "unknown",
            lang=user_lang
        )

    except Exception:
        audio_url = None

    return {
        "success": True,
        "generated": len(final_route),
        "route": final_route,
        "ai_tip": summary_translated,
        "audio_url": audio_url
    }


# ---------------------- ➕ ADD SOS CONTACT ----------------------
@router.post("/safety/add-sos-contact")
async def add_sos_contact(
    request: Request,
    payload: SOSContactAddRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.device_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found.")

    contact = SOSContact(
        device_id=payload.device_id,
        name=payload.name,
        phone=payload.phone
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)

    return {"success": True, "contact_id": contact.id, "message": "SOS contact added."}

# ---------------------- ❌ DELETE SOS CONTACT ----------------------
@router.post("/safety/delete-sos-contact")
async def delete_sos_contact(
    request: Request,
    payload: SOSContactDeleteRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    contact = db.query(SOSContact).filter(
        SOSContact.id == payload.contact_id,
        SOSContact.device_id == payload.device_id
    ).first()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found.")

    db.delete(contact)
    db.commit()
    return {"success": True, "message": "SOS contact deleted."}

# ---------------------- 📋 LIST SOS CONTACTS ----------------------
@router.post("/safety/list-sos-contacts")
async def list_sos_contacts(
    request: Request,
    payload: SOSContactListRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(require_token)
):
    ensure_token_user_match(user_data["sub"], payload.device_id)

    contacts = db.query(SOSContact).filter(SOSContact.device_id == payload.device_id).all()

    contact_list = [{"id": c.id, "name": c.name, "phone": c.phone} for c in contacts]

    return {"success": True, "contacts": contact_list}
