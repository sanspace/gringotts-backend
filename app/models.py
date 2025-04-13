from typing import Any

from pydantic import BaseModel, EmailStr, Field


class GoogleToken(BaseModel):
    token: str = Field(..., description="Google ID Token received from frontend")

class BackendToken(BaseModel):
    access_token: str
    token_type: str
    user: dict[str, Any] # Send back some user info

class UserInDB(BaseModel): # Example DB User Model
    id: int # Your internal DB User ID
    google_sub: str = Field(index=True, unique=True)
    email: EmailStr = Field(index=True, unique=True)
    full_name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    picture: str | None = None
    is_active: bool = True
    # Add other fields like roles, etc.

