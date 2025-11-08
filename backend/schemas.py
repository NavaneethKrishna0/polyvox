# backend/schemas.py
from pydantic import BaseModel, EmailStr, Field # <--- Import Field

# Schema for receiving user creation data from the request
class UserCreate(BaseModel):
    email: EmailStr
    # Add validation: password must have a max length of 72
    password: str = Field(..., min_length=8, max_length=72)

# Schema for returning user data in the response (without the password)
class User(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True
        

class Job(BaseModel):
    id: int
    status: str
    pdf_filename: str
    audio_filename: str | None = None
    result_text: str | None = None
    timestamps_json: str | None = None

    class Config:
        from_attributes = True