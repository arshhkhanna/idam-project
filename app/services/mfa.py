import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.totp_used import UsedTOTPCode

# TOTP codes are valid for one 30s window + one adjacent window = 90s max lifetime
_TOTP_WINDOW_SECONDS = 90

def generate_mfa_secret() -> str:
    return pyotp.random_base32()

def get_totp_uri(secret: str, email: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name="IDAM System")

def generate_qr_code(uri: str) -> str:
    qr = qrcode.make(uri)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode()

def verify_totp_code(db: Session, user_id: int, secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):  # allow 1 adjacent window (±30s grace)
        return False

    cutoff = datetime.utcnow() - timedelta(seconds=_TOTP_WINDOW_SECONDS)

    # Reject if this exact code was already used within the valid window
    already_used = db.query(UsedTOTPCode).filter(
        UsedTOTPCode.user_id == user_id,
        UsedTOTPCode.code == code,
        UsedTOTPCode.used_at > cutoff
    ).first()
    if already_used:
        return False

    # Record this code so it cannot be reused
    db.add(UsedTOTPCode(user_id=user_id, code=code))
    # Prune expired entries to keep the table small
    db.query(UsedTOTPCode).filter(
        UsedTOTPCode.used_at <= cutoff
    ).delete(synchronize_session=False)
    db.commit()
    return True
