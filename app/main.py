from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse as FastAPIFileResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from sqlalchemy.orm import Session, joinedload
from app.db import engine, Base, SessionLocal, get_db
from app.models import user, reset_token, audit_log, refresh_token, role, file, totp_used
from app.models.user import User as UserModel
from app.routers import auth, users, admin, mfa, roles, files
from app.services.limiter import limiter
from app.services.roles import seed_roles
from app.services.token import verify_access_token
import os

Base.metadata.create_all(bind=engine)

os.makedirs("app/uploads", exist_ok=True)

db = SessionLocal()
try:
    seed_roles(db)
finally:
    db.close()

app = FastAPI(title="IDAM System", version="1.0.0")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:;"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(mfa.router)
app.include_router(roles.router)
app.include_router(files.router)

@app.get("/")
def serve_frontend():
    return FastAPIFileResponse("app/static/index.html")

@app.get("/admin-panel")
def serve_admin(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/", status_code=302)
    payload = verify_access_token(token)
    if not payload:
        return RedirectResponse(url="/", status_code=302)
    user_obj = (
        db.query(UserModel)
        .options(joinedload(UserModel.roles))
        .filter(UserModel.email == payload.get("sub"))
        .first()
    )
    if not user_obj:
        return RedirectResponse(url="/", status_code=302)
    _ADMIN_PANEL_ROLES = {'super_admin', 'admin', 'security_analyst', 'monitor_audit'}
    if not any(r.name in _ADMIN_PANEL_ROLES for r in user_obj.roles):
        return RedirectResponse(url="/", status_code=302)
    return FastAPIFileResponse("app/templates/admin.html")

@app.get("/health")
def health_check():
    return {"status": "IDAM is running!"}
