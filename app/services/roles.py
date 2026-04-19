from sqlalchemy.orm import Session
from app.models.role import Role, Permission
from app.models.user import User
from fastapi import HTTPException, status

# All roles and their permissions from your diagram
DEFAULT_ROLES = {
    "super_admin": {
        "description": "Full Control - System Owner",
        "permissions": [
            ("users", "read"), ("users", "write"), ("users", "delete"),
            ("audit_logs", "read"), ("audit_logs", "write"),
            ("roles", "read"), ("roles", "write"), ("roles", "delete"),
            ("reports", "read"), ("reports", "write"),
            ("password_reset", "write"),
            ("api", "read"), ("api", "write"),
            ("employee_records", "read"), ("employee_records", "write"),
        ]
    },
    "admin": {
        "description": "Admin / IT Manager - Manage Users",
        "permissions": [
            ("users", "read"), ("users", "write"), ("users", "delete"),
            ("roles", "read"), ("roles", "write"),
        ]
    },
    "security_analyst": {
        "description": "Security Analyst - Monitor & Audit",
        "permissions": [
            ("audit_logs", "read"),
            ("users", "read"),
        ]
    },
    "monitor_audit": {
        "description": "Monitor & Audit - View Logs Only",
        "permissions": [
            ("audit_logs", "read"),
        ]
    },
    "developer_a": {
        "description": "Developer A - API Access Read & Write",
        "permissions": [
            ("api", "read"), ("api", "write"),
        ]
    },
    "developer_b": {
        "description": "Developer B - API Access Read Only",
        "permissions": [
            ("api", "read"),
        ]
    },
    "business_analyst": {
        "description": "Business Analyst - Reports & Analytics",
        "permissions": [
            ("reports", "read"), ("reports", "write"),
        ]
    },
    "hr_manager": {
        "description": "HR Manager - Employee Records",
        "permissions": [
            ("employee_records", "read"), ("employee_records", "write"),
        ]
    },
    "support_a": {
        "description": "Support A - Password Resets Only",
        "permissions": [
            ("password_reset", "write"),
        ]
    },
    "general_user": {
        "description": "General User - Basic Access",
        "permissions": [
            ("api", "read"),
        ]
    },
}

def seed_roles(db: Session):
    if db.query(Role).first():
        return

    for role_name, role_data in DEFAULT_ROLES.items():
        role = Role(name=role_name, description=role_data["description"])
        db.add(role)
        db.flush()  # need the id before adding permissions

        for resource, action in role_data["permissions"]:
            db.add(Permission(role_id=role.id, resource=resource, action=action))

    db.commit()

def get_all_roles(db: Session):
    return db.query(Role).all()

def assign_role(db: Session, user_id: int, role_name: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found")

    if role in user.roles:
        raise HTTPException(status_code=400, detail="User already has this role")

    user.roles.append(role)
    db.commit()
    return user

def remove_role(db: Session, user_id: int, role_name: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found")

    if role not in user.roles:
        raise HTTPException(status_code=400, detail="User does not have this role")

    user.roles.remove(role)
    db.commit()
    return user

def check_permission(user: User, resource: str, action: str) -> bool:
    for role in user.roles:
        if role.name == "super_admin":
            return True
        for permission in role.permissions:
            if permission.resource == resource and permission.action == action:
                return True
    return False

def require_permission(resource: str, action: str):
    from fastapi import Depends
    from app.services.dependencies import get_current_user

    def permission_checker(current_user: User = Depends(get_current_user)):
        if not check_permission(current_user, resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to {action} {resource}"
            )
        return current_user

    return permission_checker
