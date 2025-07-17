# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


def generate_tone_instruction(persona: dict) -> str:
    """
    Maps the persona (emotion_status + mood_trend + personality_mode + goal_focus + usage_pattern)
    into an assistant tone guideline for AI reply injection.
    """

    emotion = persona.get("emotion_status", "")
    mood = persona.get("mood_trend", "")
    goal = persona.get("goal_focus", "")
    personality = persona.get("personality_mode", "")
    pattern = persona.get("usage_pattern", "")

    tone_parts = []

    # Emotion-based tone
    if emotion in ["sadness", "fear"]:
        tone_parts.append("use a calming and reassuring tone")
    elif emotion in ["joy", "love"]:
        tone_parts.append("keep the tone uplifting and friendly")
    elif emotion == "anger":
        tone_parts.append("respond with understanding and patience")
    elif emotion == "surprise":
        tone_parts.append("acknowledge curiosity and provide clear answers")

    # Mood trend adjustment (adds extra flavor)
    if mood in ["sadness", "fear"]:
        tone_parts.append("remind them they’re not alone")
    elif mood in ["joy", "love"]:
        tone_parts.append("reflect their upbeat energy")
    elif mood == "anger":
        tone_parts.append("stay grounded and non-reactive")
    elif mood == "surprise":
        tone_parts.append("encourage healthy curiosity")

    # Goal focus
    if goal == "mental_health":
        tone_parts.append("include gentle mindfulness cues")
    elif goal == "productivity":
        tone_parts.append("keep responses focused and action-oriented")
    elif goal == "balance":
        tone_parts.append("maintain a balanced and warm approach")

    # Personality mode
    if personality == "motivational":
        tone_parts.append("add motivational encouragement")
    elif personality == "empathetic":
        tone_parts.append("emphasize emotional understanding")

    # Usage pattern insights (new)
    if pattern == "goal_focused":
        tone_parts.append("keep them focused and motivated")
    elif pattern == "reflective":
        tone_parts.append("respond with thoughtfulness and introspection")
    elif pattern == "habit_builder":
        tone_parts.append("acknowledge their discipline and encourage consistency")
    elif pattern == "seeker":
        tone_parts.append("keep answers clear, concise, and factual")

    if not tone_parts:
        return "respond naturally"

    return ", ".join(tone_parts)
