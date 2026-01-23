from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.common import MongoBaseModel, PyObjectId

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    firm_affiliation: Optional[str] = None
    role: str = "paralegal"

class UserCreate(UserBase):
    password: str

class UserInDB(MongoBaseModel, UserBase):
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserResponse(MongoBaseModel, UserBase):
    pass