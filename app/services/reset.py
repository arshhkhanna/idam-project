import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.reset_token import PasswordResetToken
from app.models.user import User
from app.services.auth import hash_password

def create_reset_token(db: Session, email: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=30)
    db.add(PasswordResetToken(email=email, token=token, expires_at=expires_at))
    db.commit()
    return token

def verify_reset_token(db: Session, token: str):
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.is_used == False
    ).first()
    if not reset_token:
        return None
    if reset_token.expires_at < datetime.utcnow():
        return None
    return reset_token

def reset_user_password(db: Session, token: str, new_password: str) -> bool:
    reset_token = verify_reset_token(db, token)
    if not reset_token:
        return False
    user = db.query(User).filter(User.email == reset_token.email).first()
    if not user:
        return False
    user.hashed_password = hash_password(new_password)
    reset_token.is_used = True
    db.commit()
    return True
