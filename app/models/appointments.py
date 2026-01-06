"""
Nexus Miracle - Appointment Models

Data models for appointment bookings.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AppointmentStatus(str, Enum):
    """Status of an appointment."""
    
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class AppointmentType(str, Enum):
    """Type of appointment."""
    
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    PROCEDURE = "procedure"
    ROUTINE_CHECKUP = "routine_checkup"
    EMERGENCY = "emergency"


class Patient(BaseModel):
    """Patient information."""
    
    id: UUID = Field(default_factory=uuid4, description="Patient ID")
    name: str = Field(min_length=1, max_length=200, description="Patient name")
    phone: str = Field(
        pattern=r"^\+?[1-9]\d{7,14}$",
        description="Phone number"
    )
    email: str | None = Field(default=None, description="Email address")
    national_id: str | None = Field(default=None, description="National ID")
    date_of_birth: datetime | None = Field(default=None, description="Date of birth")
    gender: str | None = Field(
        default=None,
        pattern=r"^(male|female|other)$",
        description="Gender"
    )
    language_preference: str = Field(
        default="ar",
        description="Preferred language (ar/en)"
    )


class Doctor(BaseModel):
    """Doctor information."""
    
    id: str = Field(description="Doctor ID")
    name: str = Field(description="Doctor name")
    specialty: str = Field(description="Medical specialty")
    department: str = Field(description="Department")


class Appointment(BaseModel):
    """
    Complete appointment model.
    
    Represents a medical appointment booking with all related information.
    """
    
    # Identifiers
    id: UUID = Field(default_factory=uuid4, description="Appointment ID")
    reference_code: str = Field(
        default_factory=lambda: f"NM-{uuid4().hex[:8].upper()}",
        description="Human-readable reference code"
    )
    
    # Patient and doctor
    patient: Patient = Field(description="Patient information")
    doctor: Doctor = Field(description="Doctor information")
    
    # Appointment details
    appointment_type: AppointmentType = Field(
        default=AppointmentType.CONSULTATION,
        description="Type of appointment"
    )
    department: str = Field(description="Department name")
    location: str | None = Field(default=None, description="Clinic/room location")
    
    # Scheduling
    scheduled_at: datetime = Field(description="Scheduled date and time")
    duration_minutes: int = Field(
        default=30,
        ge=5,
        le=480,
        description="Appointment duration"
    )
    
    # Status
    status: AppointmentStatus = Field(
        default=AppointmentStatus.SCHEDULED,
        description="Current status"
    )
    
    # Notes and metadata
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Appointment notes"
    )
    symptoms: list[str] = Field(
        default_factory=list,
        description="Reported symptoms"
    )
    
    # Call tracking
    booked_via_call: bool = Field(
        default=False,
        description="Booked via phone call"
    )
    call_session_id: UUID | None = Field(
        default=None,
        description="Associated call session ID"
    )
    
    # Reminders
    reminder_sent: bool = Field(default=False, description="Reminder sent flag")
    reminder_sent_at: datetime | None = Field(
        default=None,
        description="Reminder sent timestamp"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp"
    )
    cancelled_at: datetime | None = Field(
        default=None,
        description="Cancellation timestamp"
    )
    cancellation_reason: str | None = Field(
        default=None,
        description="Reason for cancellation"
    )
    
    @property
    def is_upcoming(self) -> bool:
        """Check if appointment is upcoming."""
        return (
            self.status in (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED)
            and self.scheduled_at > datetime.now()
        )
    
    @property
    def is_past(self) -> bool:
        """Check if appointment is in the past."""
        return self.scheduled_at < datetime.now()
    
    def confirm(self) -> None:
        """Confirm the appointment."""
        if self.status == AppointmentStatus.SCHEDULED:
            self.status = AppointmentStatus.CONFIRMED
            self.updated_at = datetime.now()
    
    def cancel(self, reason: str | None = None) -> None:
        """
        Cancel the appointment.
        
        Args:
            reason: Optional cancellation reason
        """
        if self.status not in (AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW):
            self.status = AppointmentStatus.CANCELLED
            self.cancelled_at = datetime.now()
            self.cancellation_reason = reason
            self.updated_at = datetime.now()
    
    def complete(self) -> None:
        """Mark appointment as completed."""
        if self.status in (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED):
            self.status = AppointmentStatus.COMPLETED
            self.updated_at = datetime.now()
    
    def to_summary(self) -> dict[str, Any]:
        """
        Get a summary for LLM context.
        
        Returns:
            Summary dictionary
        """
        return {
            "reference": self.reference_code,
            "patient_name": self.patient.name,
            "doctor_name": self.doctor.name,
            "department": self.department,
            "scheduled_at": self.scheduled_at.isoformat(),
            "status": self.status.value,
            "appointment_type": self.appointment_type.value,
        }
