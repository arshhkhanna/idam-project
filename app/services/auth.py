import bcrypt
from sqlalchemy.orm import Session
from app.models.user import User

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, email: str, password: str):
    hashed = hash_password(password)
    user = User(email=email, hashed_password=hashed, is_active=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
