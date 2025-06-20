from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from app.utils.jwt_utils import verify_access_token
from app.models.database import SessionLocal
from app.models.user_model import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # we won't use /token directly

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: SessionLocal = Depends(get_db)) -> User:
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="❌ Invalid or expired token")

    user = db.query(User).filter(User.temp_uid == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=404, detail="❌ User not found")

    return user
