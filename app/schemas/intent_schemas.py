from pydantic import BaseModel

class IntentRequest(BaseModel):
    text: str
