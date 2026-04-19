from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog

def log_action(
    db: Session,
    action: str,
    status: str,
    email: str = None,
    ip_address: str = None,
    details: str = None
):
    log = AuditLog(
        email=email,
        action=action,
        status=status,
        ip_address=ip_address,
        details=details
    )
    db.add(log)
    db.commit()
