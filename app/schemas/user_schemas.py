# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from pydantic import BaseModel
from typing import Optional, List, Dict


class LoginRequest(BaseModel):
    device_id: Optional[str]

class OnboardingUpdateRequest(BaseModel):
    ai_name: Optional[str]
    voice: Optional[str]
    preferred_lang: Optional[str]
    device_id: str


class ProfileRequest(BaseModel):
    device_id: Optional[str]


class TierUpgradeRequest(BaseModel):
    device_id: Optional[str]
    new_tier: Optional[str]
    payment_key: Optional[str]


class TierDowngradeRequest(BaseModel):
    device_id: Optional[str]
    new_tier: Optional[str]


class TranslationRequest(BaseModel):
    device_id: str
    strings: List[str]
    target_lang: str  # e.g., "hi"


class UserLangRequest(BaseModel):
    device_id: Optional[str]
    preferred_lang: Optional[str]