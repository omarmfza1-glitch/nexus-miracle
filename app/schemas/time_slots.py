"""
Nexus Miracle - Time Slot Schemas

Pydantic schemas for time slot and availability endpoints.
"""

from datetime import date as dt_date
from datetime import datetime as dt
from datetime import time as dt_time

from pydantic import BaseModel, Field


class TimeSlotResponse(BaseModel):
    """Response schema for a single time slot."""
    
    id: int = Field(description="Time slot ID")
    doctor_id: int = Field(description="Doctor ID")
    day_of_week: int = Field(description="Day of week (0=Sunday, 6=Saturday)")
    start_time: dt_time = Field(description="Slot start time")
    end_time: dt_time = Field(description="Slot end time")
    is_available: bool = Field(description="Whether slot is available")
    
    model_config = {"from_attributes": True}


class AvailableSlot(BaseModel):
    """A single available appointment slot."""
    
    slot_datetime: dt = Field(description="Slot date and time")
    duration_minutes: int = Field(default=30, description="Slot duration")
    is_available: bool = Field(default=True, description="Slot availability")


class AvailableSlotsResponse(BaseModel):
    """Response schema for available time slots on a specific date."""
    
    doctor_id: int = Field(description="Doctor ID")
    doctor_name: str = Field(description="Doctor name (English)")
    doctor_name_ar: str = Field(description="Doctor name (Arabic)")
    slot_date: dt_date = Field(description="Date for availability")
    slots: list[AvailableSlot] = Field(description="List of available slots")
    total_available: int = Field(description="Total number of available slots")


class DoctorSchedule(BaseModel):
    """Doctor's weekly schedule."""
    
    doctor_id: int = Field(description="Doctor ID")
    schedule: list[TimeSlotResponse] = Field(description="Weekly time slots")
