# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.


from pydantic import BaseModel


class GenerateTTSRequest(BaseModel):
    user_id: int
    text: str
    voice: str  # e.g., 'male' or 'female'