import os
import uuid
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from app.models.file import File, file_roles, file_users
from app.models.role import Role
from app.models.user import User

UPLOAD_DIR = "app/uploads"

def save_file(db: Session, file: UploadFile, uploader_id: int) -> File:
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as f:
        content = file.file.read()
        f.write(content)

    db_file = File(
        filename=unique_name,
        original_name=file.filename,
        file_type=file.content_type,
        file_size=len(content),
        uploaded_by=uploader_id
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def assign_file_access(db: Session, file_id: int, role_names: list, user_ids: list):
    db_file = db.query(File).filter(File.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    for role_name in role_names:
        role = db.query(Role).filter(Role.name == role_name).first()
        if role and role not in db_file.allowed_roles:
            db_file.allowed_roles.append(role)

    for user_id in user_ids:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user not in db_file.allowed_users:
            db_file.allowed_users.append(user)

    db.commit()
    return db_file

def get_files_for_user(db: Session, user: User) -> list:
    if any(r.name == "super_admin" for r in user.roles):
        return db.query(File).all()

    user_role_ids = [role.id for role in user.roles]

    role_files = db.query(File).join(
        file_roles, File.id == file_roles.c.file_id
    ).filter(
        file_roles.c.role_id.in_(user_role_ids)
    ).all()

    user_files = db.query(File).join(
        file_users, File.id == file_users.c.file_id
    ).filter(
        file_users.c.user_id == user.id
    ).all()

    return list({f.id: f for f in role_files + user_files}.values())

def can_access_file(db: Session, file_id: int, user: User) -> bool:
    db_file = db.query(File).filter(File.id == file_id).first()
    if not db_file:
        return False

    if any(r.name == "super_admin" for r in user.roles):
        return True

    user_role_ids = [role.id for role in user.roles]
    if any(r.id in user_role_ids for r in db_file.allowed_roles):
        return True

    if any(u.id == user.id for u in db_file.allowed_users):
        return True

    return False

def delete_file(db: Session, file_id: int, user: User):
    db_file = db.query(File).filter(File.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    is_super_admin = any(r.name == "super_admin" for r in user.roles)
    if not is_super_admin and db_file.uploaded_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this file"
        )

    file_path = os.path.join(UPLOAD_DIR, db_file.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(db_file)
    db.commit()
