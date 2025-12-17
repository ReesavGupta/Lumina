from typing import List
from datetime import datetime
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    full_name: str | None = None
    consent: bool

class UserRead(UserBase):
    id: int
    full_name: str | None = None
    consent: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: str | None = None

class BlinkSampleIn(BaseModel):
    timestamp: datetime
    count: int
    session_id: int | None = None

class SessionBase(BaseModel):
    name: str | None = None

class SessionCreate(SessionBase):
    start_time: datetime

class SessionUpdate(BaseModel):
    name: str | None = None
    end_time: datetime | None = None

class SessionRead(SessionBase):
    id: int
    user_id: int
    start_time: datetime
    end_time: datetime | None = None

    class Config:
        from_attributes = True

class SessionWithBlinks(SessionRead):
    blink_samples: List["BlinkSampleRead"] = []

class BlinkSampleRead(BaseModel):
    id: int
    timestamp: datetime
    count: int
    session_id: int | None = None

    class Config:
        from_attributes = True