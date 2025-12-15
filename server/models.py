from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    files = relationship("File", back_populates="owner")
    permissions = relationship("Permission", back_populates="user")


class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String, index=True)
    extension = Column(String)
    size = Column(Integer)
    storage_name = Column(String, unique=True)  # UUID ім'я на диску

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Метадані
    uploader_name = Column(String)
    editor_name = Column(String)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="files")

    permissions = relationship("Permission", back_populates="file", cascade="all, delete-orphan")


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_id = Column(Integer, ForeignKey("files.id"))
    access_level = Column(String)  # 'read' або 'write'

    user = relationship("User", back_populates="permissions")
    file = relationship("File", back_populates="permissions")