from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.schemas.user import RoleResponse, AssignRoleRequest
from app.services.roles import get_all_roles, assign_role, remove_role, require_permission
from typing import List

router = APIRouter(prefix="/roles", tags=["Roles"])

@router.get("/", response_model=List[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles", "read"))
):
    # Returns all available roles and their permissions
    return get_all_roles(db)

@router.post("/assign/{user_id}")
def assign_role_to_user(
    user_id: int,
    data: AssignRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles", "write"))
):
    assign_role(db, user_id, data.role_name)
    return {"message": f"Role '{data.role_name}' assigned to user {user_id}"}

@router.delete("/remove/{user_id}")
def remove_role_from_user(
    user_id: int,
    data: AssignRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles", "write"))
):
    remove_role(db, user_id, data.role_name)
    return {"message": f"Role '{data.role_name}' removed from user {user_id}"}
