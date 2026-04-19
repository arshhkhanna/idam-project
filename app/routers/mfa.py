from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.schemas.user import MFAVerify, MFAEnableRequest, MFADisableRequest
from app.services.dependencies import get_current_user
from app.services.auth import verify_password
from app.services.mfa import generate_mfa_secret, get_totp_uri, generate_qr_code, verify_totp_code
from app.services.limiter import limiter

router = APIRouter(prefix="/mfa", tags=["MFA"])

@router.post("/enable")
@limiter.limit("5/minute")
def enable_mfa(
    request: Request,
    data: MFAEnableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    secret = generate_mfa_secret()
    current_user.mfa_secret = secret
    db.commit()
    uri = get_totp_uri(secret, current_user.email)
    qr_code = generate_qr_code(uri)
    return {
        "message": "Scan the QR code with Google Authenticator",
        "qr_code_base64": qr_code,
    }

@router.post("/verify")
@limiter.limit("5/minute")
def verify_mfa(
    request: Request,
    data: MFAVerify,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not set up yet. Call /mfa/enable first"
        )
    if not verify_totp_code(db, current_user.id, current_user.mfa_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code"
        )
    current_user.mfa_enabled = True
    db.commit()
    return {"message": "MFA enabled successfully!"}

@router.post("/disable")
@limiter.limit("5/minute")
def disable_mfa(
    request: Request,
    data: MFADisableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled"
        )
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    if not verify_totp_code(db, current_user.id, current_user.mfa_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code"
        )
    current_user.mfa_secret = None
    current_user.mfa_enabled = False
    db.commit()
    return {"message": "MFA disabled successfully"}
