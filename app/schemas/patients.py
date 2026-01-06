"""
Nexus Miracle - Patient Schemas

Pydantic schemas for patient-related API endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PatientCreate(BaseModel):
    """Request schema for creating/updating a patient."""
    
    phone: str = Field(
        min_length=10,
        max_length=20,
        description="Phone number (+966XXXXXXXXX or 05XXXXXXXX)"
    )
    name: str | None = Field(default=None, max_length=200, description="Patient name (English)")
    name_ar: str | None = Field(default=None, max_length=200, description="Patient name (Arabic)")
    national_id_last4: str | None = Field(
        default=None,
        min_length=4,
        max_length=4,
        description="Last 4 digits of national ID"
    )
    gender: str | None = Field(default=None, pattern=r"^(male|female)$", description="Gender")
    dob: datetime | None = Field(default=None, description="Date of birth")
    insurance_company: str | None = Field(default=None, max_length=100, description="Insurance company")
    insurance_id: str | None = Field(default=None, max_length=50, description="Insurance ID")
    language: str = Field(default="ar", pattern=r"^(ar|en)$", description="Preferred language")
    
    @field_validator("phone")
    @classmethod
    def validate_saudi_phone(cls, v: str) -> str:
        """Validate and normalize Saudi phone number."""
        v = v.replace(" ", "").replace("-", "")
        
        if v.startswith("+966"):
            if len(v) != 13:
                raise ValueError("Phone must be +966 followed by 9 digits")
        elif v.startswith("05"):
            if len(v) != 10:
                raise ValueError("Phone must be 05 followed by 8 digits")
            v = "+966" + v[1:]
        else:
            raise ValueError("Phone must start with +966 or 05")
        
        return v


class PatientUpdate(BaseModel):
    """Request schema for updating patient information."""
    
    name: str | None = Field(default=None, max_length=200)
    name_ar: str | None = Field(default=None, max_length=200)
    national_id_last4: str | None = Field(default=None, min_length=4, max_length=4)
    gender: str | None = Field(default=None, pattern=r"^(male|female)$")
    dob: datetime | None = None
    insurance_company: str | None = Field(default=None, max_length=100)
    insurance_id: str | None = Field(default=None, max_length=50)
    language: str | None = Field(default=None, pattern=r"^(ar|en)$")


class PatientResponse(BaseModel):
    """Response schema for patient data."""
    
    id: int = Field(description="Patient ID")
    phone: str = Field(description="Phone number")
    name: str | None = Field(description="Patient name (English)")
    name_ar: str | None = Field(description="Patient name (Arabic)")
    national_id_last4: str | None = Field(description="Last 4 digits of national ID")
    gender: str | None = Field(description="Gender")
    dob: datetime | None = Field(description="Date of birth")
    insurance_company: str | None = Field(description="Insurance company")
    insurance_id: str | None = Field(description="Insurance ID")
    language: str = Field(description="Preferred language")
    created_at: datetime = Field(description="Record creation timestamp")
    
    model_config = {"from_attributes": True}
