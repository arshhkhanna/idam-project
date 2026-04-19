from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base

file_roles = Table(
    'file_roles',
    Base.metadata,
    Column('file_id', Integer, ForeignKey('files.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

file_users = Table(
    'file_users',
    Base.metadata,
    Column('file_id', Integer, ForeignKey('files.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
)

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    allowed_roles = relationship("Role", secondary=file_roles)
    allowed_users = relationship(
        "User",
        secondary=file_users,
        primaryjoin="File.id == file_users.c.file_id",
        secondaryjoin="file_users.c.user_id == User.id",
        foreign_keys=[file_users.c.file_id, file_users.c.user_id]
    )
    uploader = relationship(
        "User",
        foreign_keys=[uploaded_by]
    )
