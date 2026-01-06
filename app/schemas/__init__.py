"""
Nexus Miracle - Pydantic Schemas Package

Request/response schemas for API endpoints.
"""

from app.schemas.appointments import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentUpdate,
)
from app.schemas.doctors import (
    DoctorBase,
    DoctorListResponse,
    DoctorResponse,
)
from app.schemas.insurance import (
    InsuranceCheckResponse,
    InsuranceCoverage,
)
from app.schemas.patients import (
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)
from app.schemas.time_slots import (
    AvailableSlotsResponse,
    TimeSlotResponse,
)

__all__ = [
    # Doctors
    "DoctorBase",
    "DoctorResponse",
    "DoctorListResponse",
    # Appointments
    "AppointmentCreate",
    "AppointmentUpdate",
    "AppointmentResponse",
    "AppointmentListResponse",
    # Insurance
    "InsuranceCoverage",
    "InsuranceCheckResponse",
    # Patients
    "PatientCreate",
    "PatientUpdate",
    "PatientResponse",
    # Time Slots
    "TimeSlotResponse",
    "AvailableSlotsResponse",
]
