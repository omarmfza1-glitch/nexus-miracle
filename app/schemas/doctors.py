"""
Nexus Miracle - Doctor Schemas

Pydantic schemas for doctor-related API endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class DoctorBase(BaseModel):
    """Base schema for doctor data."""
    
    name: str = Field(description="Doctor name (English)")
    name_ar: str = Field(description="Doctor name (Arabic)")
    specialty: str = Field(description="Medical specialty (English)")
    specialty_ar: str = Field(description="Medical specialty (Arabic)")
    branch: str = Field(description="Clinic branch")


class DoctorResponse(DoctorBase):
    """Response schema for a single doctor."""
    
    id: int = Field(description="Doctor ID")
    status: str = Field(description="Doctor status (active/inactive/on_leave)")
    bio: str | None = Field(default=None, description="Doctor bio (English)")
    bio_ar: str | None = Field(default=None, description="Doctor bio (Arabic)")
    rating: float = Field(description="Doctor rating (0-5)")
    created_at: datetime = Field(description="Record creation timestamp")
    
    model_config = {"from_attributes": True}


class DoctorListResponse(BaseModel):
    """Response schema for paginated doctor list."""
    
    items: list[DoctorResponse] = Field(description="List of doctors")
    total: int = Field(description="Total number of doctors matching criteria")
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")
