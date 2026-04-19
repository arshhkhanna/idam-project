import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.models.file import File
from app.schemas.user import FileResponse as FileResponseSchema, FileAccessRequest
from app.services.dependencies import get_current_user
from app.services.files import save_file, assign_file_access, get_files_for_user, can_access_file, delete_file
from app.services.roles import require_permission
from app.services.audit import log_action
from fastapi import Request
from typing import List

UPLOAD_DIR = "app/uploads"
ALLOWED_EXTENSIONS = {'.doc', '.xml', '.pdf'}

def _valid_magic(header: bytes, ext: str) -> bool:
    if ext == '.pdf':
        return header[:4] == b'%PDF'
    if ext == '.doc':
        # OLE2 Compound Document magic bytes (Word 97-2003 .doc)
        return header[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
    if ext == '.xml':
        # Strip UTF-8 BOM and leading whitespace, then expect an opening tag
        stripped = header.lstrip(b'\xef\xbb\xbf \t\n\r')
        return stripped[:1] == b'<'
    return False

router = APIRouter(prefix="/files", tags=["Files"])

@router.post("/upload", response_model=FileResponseSchema)
def upload_file(
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .doc, .xml, and .pdf files are allowed"
        )

    # Read header for magic-byte check, then seek to end for size
    header = file.file.read(16)
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Max size is 10MB"
        )

    if not _valid_magic(header, ext):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match the declared extension"
        )

    return save_file(db, file, current_user.id)

@router.get("/", response_model=List[FileResponseSchema])
def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Returns only files the current user has access to
    return get_files_for_user(db, current_user)

@router.get("/download/{file_id}")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check permission
    if not can_access_file(db, file_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this file"
        )

    db_file = db.query(File).filter(File.id == file_id).first()
    safe_base = os.path.realpath(UPLOAD_DIR)
    file_path = os.path.realpath(os.path.join(UPLOAD_DIR, db_file.filename))
    if not file_path.startswith(safe_base + os.sep):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        filename=db_file.original_name,
        media_type=db_file.file_type
    )

@router.post("/assign/{file_id}")
def assign_access(
    file_id: int,
    data: FileAccessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("files", "write"))
):
    assign_file_access(db, file_id, data.role_names, data.user_ids)
    return {"message": f"Access assigned to file {file_id}"}

@router.delete("/{file_id}")
def remove_file(
    request: Request,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    delete_file(db, file_id, current_user)
    log_action(db, action="file_delete", status="success",
        email=current_user.email, ip_address=request.client.host,
        details=f"file_id={file_id}")
    return {"message": "File deleted successfully"}
