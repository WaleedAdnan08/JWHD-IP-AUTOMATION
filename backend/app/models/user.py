from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
import re
from datetime import datetime
from app.models.common import MongoBaseModel, PyObjectId

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    firm_affiliation: Optional[str] = None
    role: str = "paralegal"

class UserCreate(UserBase):
    password: str

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r"[A-Z]", v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r"\d", v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserInDB(MongoBaseModel, UserBase):
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserResponse(MongoBaseModel, UserBase):
    pass