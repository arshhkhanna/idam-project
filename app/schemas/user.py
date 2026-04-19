from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import re


def _validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError('must be at least 8 characters')
    if not re.search(r'\d', v):
        raise ValueError('must contain at least one number')
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]', v):
        raise ValueError('must contain at least one special character')
    return v


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        return _validate_password(v)


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        return _validate_password(v)


class MFAVerify(BaseModel):
    code: str


class MFAEnableRequest(BaseModel):
    current_password: str


class MFADisableRequest(BaseModel):
    code: str
    current_password: str


class MFALoginRequest(BaseModel):
    email: EmailStr
    password: str
    mfa_code: str


class AuditLogResponse(BaseModel):
    id: int
    email: Optional[str] = None
    action: str
    status: str
    ip_address: Optional[str] = None
    details: Optional[str] = None

    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    resource: str
    action: str

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    permissions: list[PermissionResponse] = []

    class Config:
        from_attributes = True


class AssignRoleRequest(BaseModel):
    role_name: str


class FileResponse(BaseModel):
    id: int
    filename: str
    original_name: str
    file_type: str
    file_size: int
    uploaded_by: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FileAccessRequest(BaseModel):
    role_names: Optional[list[str]] = []
    user_ids: Optional[list[int]] = []
