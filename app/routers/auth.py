from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas.user import UserCreate, UserResponse, UserLogin, TokenResponse, PasswordResetRequest, PasswordResetConfirm, MFALoginRequest, RefreshRequest
from app.services.auth import create_user, get_user_by_email, verify_password
from app.services.token import create_access_token, create_refresh_token, verify_refresh_token, revoke_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.services.reset import create_reset_token, reset_user_password
from app.services.mfa import verify_totp_code
from app.services.audit import log_action
from app.services.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("5/minute")
def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        log_action(db, action="register", status="failed",
            email=user_data.email, ip_address=request.client.host,
            details="Email already registered")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    user = create_user(db, user_data.email, user_data.password)
    log_action(db, action="register", status="success",
        email=user_data.email, ip_address=request.client.host)
    return user

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, user_data: UserLogin, db: Session = Depends(get_db)):
    user = get_user_by_email(db, user_data.email)
    if not user:
        log_action(db, action="login", status="failed",
            email=user_data.email, ip_address=request.client.host,
            details="invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    if not verify_password(user_data.password, user.hashed_password):
        log_action(db, action="login", status="failed",
            email=user_data.email, ip_address=request.client.host,
            details="invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    if not user.is_active:
        log_action(db, action="login", status="failed",
            email=user_data.email, ip_address=request.client.host,
            details="Account inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive — pending admin approval"
        )
    if user.mfa_enabled:
        return {"access_token": "", "refresh_token": None, "token_type": "mfa_required"}
    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token(db, user.email)
    log_action(db, action="login", status="success",
        email=user_data.email, ip_address=request.client.host)
    response = JSONResponse({"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"})
    response.set_cookie("access_token", access_token, httponly=True, samesite="strict", max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return response

@router.post("/login-mfa", response_model=TokenResponse)
@limiter.limit("5/minute")
def login_mfa(request: Request, user_data: MFALoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, user_data.email)
    if not user:
        log_action(db, action="login_mfa", status="failed",
            email=user_data.email, ip_address=request.client.host,
            details="invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    if not verify_password(user_data.password, user.hashed_password):
        log_action(db, action="login_mfa", status="failed",
            email=user_data.email, ip_address=request.client.host,
            details="invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    if not user.is_active:
        log_action(db, action="login_mfa", status="failed",
            email=user_data.email, ip_address=request.client.host,
            details="Account inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive — pending admin approval"
        )
    if not user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled for this account"
        )
    if not verify_totp_code(db, user.id, user.mfa_secret, user_data.mfa_code):
        log_action(db, action="login_mfa", status="failed",
            email=user_data.email, ip_address=request.client.host,
            details="Invalid MFA code")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code"
        )
    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token(db, user.email)
    log_action(db, action="login_mfa", status="success",
        email=user_data.email, ip_address=request.client.host)
    response = JSONResponse({"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"})
    response.set_cookie("access_token", access_token, httponly=True, samesite="strict", max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return response

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("5/minute")
def refresh_token(request: Request, data: RefreshRequest, db: Session = Depends(get_db)):
    token_record = verify_refresh_token(db, data.refresh_token)
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    revoke_refresh_token(db, data.refresh_token)
    access_token = create_access_token({"sub": token_record.email})
    new_refresh_token = create_refresh_token(db, token_record.email)
    response = JSONResponse({"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"})
    response.set_cookie("access_token", access_token, httponly=True, samesite="strict", max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return response

@router.post("/logout")
@limiter.limit("5/minute")
def logout(request: Request, data: RefreshRequest, db: Session = Depends(get_db)):
    revoke_refresh_token(db, data.refresh_token)
    response = JSONResponse({"message": "Logged out successfully"})
    response.delete_cookie("access_token")
    return response

@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(request: Request, data: PasswordResetRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, data.email)
    if not user:
        return {"message": "If that email exists, a reset token has been generated"}
    token = create_reset_token(db, data.email)
    log_action(db, action="forgot_password", status="success",
        email=data.email, ip_address=request.client.host)
    return {"message": "Password reset token generated", "reset_token": token}

@router.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, data: PasswordResetConfirm, db: Session = Depends(get_db)):
    success = reset_user_password(db, data.token, data.new_password)
    if not success:
        log_action(db, action="reset_password", status="failed",
            ip_address=request.client.host, details="Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    log_action(db, action="reset_password", status="success",
        ip_address=request.client.host)
    return {"message": "Password reset successfully"}
