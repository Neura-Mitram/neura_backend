# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SafetyTriggerRequest(BaseModel):
    device_id: str
    message: str
    emotion: Optional[str] = None
    location: Optional[str] = None

class SOSContactAddRequest(BaseModel):
    device_id: str
    name: str
    phone: str

class SOSContactDeleteRequest(BaseModel):
    device_id: str
    contact_id: int

class SOSContactListRequest(BaseModel):
    device_id: str

class UnsafeAreaReportRequest(BaseModel):
    device_id: str
    location: Optional[str]
    reason: str
    description: Optional[str]
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class SosAlertLogRequest(BaseModel):
    device_id: int
    message: str
    emotion: Optional[str] = None
    timestamp: Optional[datetime] = None

class ImSafeLogRequest(BaseModel):
    device_id: int
    status: str
    location: Optional[str] = None
    timestamp: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class UnsafeAreaClusterPingRequest(BaseModel):
    device_id: int
    latitude: float
    longitude: float
    timestamp: datetime

class MyReportsRequest(BaseModel):
    device_id: int
