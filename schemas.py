"""
Database Schemas for PsychSphere

Each Pydantic model below maps to a MongoDB collection with the lowercase
name of the class (e.g., Inquiry -> "inquiry").
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class Inquiry(BaseModel):
    """
    Inquiries submitted from the website contact form
    Collection name: "inquiry"
    """
    name: str = Field(..., description="Full name of the person inquiring", min_length=2)
    email: EmailStr = Field(..., description="Contact email")
    phone: Optional[str] = Field(None, description="Phone number")
    message: str = Field(..., description="Inquiry message", min_length=5)
    source: Optional[str] = Field("website", description="Lead source identifier")
    newsletter_opt_in: bool = Field(False, description="Whether user opted in for updates")


# You can add more collections as your product grows, e.g.,
# class Session(BaseModel): ...
