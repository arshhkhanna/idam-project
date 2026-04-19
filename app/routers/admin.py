from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.user import UserResponse, AuditLogResponse
from app.services.admin import require_super_admin
from app.services.roles import require_permission
from typing import List

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users", "read"))
):
    return db.query(User).all()

@router.get("/users/detailed")
def get_all_users_detailed(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users", "read"))
):
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "is_active": u.is_active,
            "is_admin": u.is_admin,
            "mfa_enabled": u.mfa_enabled,
            "roles": [r.name for r in u.roles]
        }
        for u in users
    ]

@router.patch("/users/{user_id}/enable")
def enable_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users", "write"))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = True
    db.commit()
    return {"message": f"User {user_id} has been enabled"}

@router.patch("/users/{user_id}/disable")
def disable_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users", "write"))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = False
    db.commit()
    return {"message": f"User {user_id} has been disabled"}

@router.patch("/users/{user_id}/make-admin")
def make_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_admin = True
    db.commit()
    return {"message": f"User {user_id} is now an admin"}

@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit_logs", "read"))
):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()

@router.get("/files")
def get_all_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    from app.models.file import File
    files = db.query(File).all()
    return [
        {
            "id": f.id,
            "original_name": f.original_name,
            "file_type": f.file_type,
            "file_size": f.file_size,
            "uploaded_by": f.uploaded_by,
            "allowed_roles": [r.name for r in f.allowed_roles],
            "allowed_users": [u.id for u in f.allowed_users]
        }
        for f in files
    ]
