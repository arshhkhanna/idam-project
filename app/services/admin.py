from fastapi import Depends, HTTPException, status
from app.models.user import User
from app.services.dependencies import get_current_user
from app.services.roles import check_permission

# Gate for the admin panel — user must have at least one admin-relevant permission
_ADMIN_PANEL_PERMISSIONS = [("users", "read"), ("audit_logs", "read"), ("roles", "read")]

def get_admin_user(current_user: User = Depends(get_current_user)):
    if not any(check_permission(current_user, r, a) for r, a in _ADMIN_PANEL_PERMISSIONS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

def require_super_admin(current_user: User = Depends(get_current_user)):
    if not any(r.name == "super_admin" for r in current_user.roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")
    return current_user
