"""
Nexus Miracle - Appointment Schemas

Pydantic schemas for appointment-related API endpoints.
"""

from datetime import datetime as dt
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class AppointmentStatus(str, Enum):
    """Appointment status enumeration."""
    
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class AppointmentCreate(BaseModel):
    """Request schema for creating an appointment."""
    
    phone: str = Field(
        min_length=10,
        max_length=20,
        description="Patient phone number (+966XXXXXXXXX or 05XXXXXXXX)"
    )
    doctor_id: int = Field(ge=1, description="Doctor ID")
    scheduled_at: dt = Field(description="Appointment date and time")
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Appointment notes"
    )
    
    @field_validator("phone")
    @classmethod
    def validate_saudi_phone(cls, v: str) -> str:
        """Validate and normalize Saudi phone number."""
        # Remove spaces and dashes
        v = v.replace(" ", "").replace("-", "")
        
        # Accept +966 or 05 format
        if v.startswith("+966"):
            if len(v) != 13:
                raise ValueError("Phone must be +966 followed by 9 digits")
        elif v.startswith("05"):
            if len(v) != 10:
                raise ValueError("Phone must be 05 followed by 8 digits")
            # Convert to international format
            v = "+966" + v[1:]
        else:
            raise ValueError("Phone must start with +966 or 05")
        
        return v


class AppointmentUpdate(BaseModel):
    """Request schema for updating an appointment."""
    
    scheduled_at: dt | None = Field(default=None, description="New appointment time")
    status: AppointmentStatus | None = Field(default=None, description="New status")
    notes: str | None = Field(default=None, max_length=1000, description="Updated notes")


class AppointmentResponse(BaseModel):
    """Response schema for a single appointment."""
    
    id: int = Field(description="Appointment ID")
    patient_id: int = Field(description="Patient ID")
    patient_name: str | None = Field(description="Patient name")
    patient_phone: str = Field(description="Patient phone")
    doctor_id: int = Field(description="Doctor ID")
    doctor_name: str = Field(description="Doctor name")
    doctor_name_ar: str = Field(description="Doctor name (Arabic)")
    specialty: str = Field(description="Doctor specialty")
    specialty_ar: str = Field(description="Doctor specialty (Arabic)")
    scheduled_at: dt = Field(description="Appointment date and time")
    duration_minutes: int = Field(description="Appointment duration")
    status: str = Field(description="Appointment status")
    notes: str | None = Field(description="Appointment notes")
    reminder_sent: bool = Field(description="Whether reminder was sent")
    booked_via_call: bool = Field(description="Whether booked via phone call")
    created_at: dt = Field(description="Record creation timestamp")
    updated_at: dt = Field(description="Last update timestamp")
    
    model_config = {"from_attributes": True}


class AppointmentListResponse(BaseModel):
    """Response schema for paginated appointment list."""
    
    items: list[AppointmentResponse] = Field(description="List of appointments")
    total: int = Field(description="Total number of appointments matching criteria")
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")


class CancelAppointmentRequest(BaseModel):
    """Request schema for cancelling an appointment."""
    
    reason: str | None = Field(
        default=None,
        max_length=500,
        description="Cancellation reason"
    )
