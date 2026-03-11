"""
User model — multi-tenant, role-based access.
Roles: admin, creator, viewer
"""
from sqlalchemy import Column, String, Boolean, Enum as SAEnum
import enum

from models.base import TimestampMixin, UUIDMixin
from core.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    creator = "creator"
    viewer = "viewer"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.creator, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<User {self.email} [{self.role}]>"
