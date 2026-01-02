"""
Nexus Miracle - Appointments Router

CRUD operations for appointment bookings.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter()


# ===========================================
# Request/Response Models
# ===========================================

class AppointmentCreate(BaseModel):
    """Request model for creating an appointment."""
    
    patient_name: str = Field(min_length=1, max_length=200)
    patient_phone: str = Field(pattern=r"^\+?[1-9]\d{7,14}$")
    doctor_id: str = Field(min_length=1)
    department: str = Field(min_length=1, max_length=100)
    scheduled_at: datetime
    notes: str | None = Field(default=None, max_length=1000)


class AppointmentUpdate(BaseModel):
    """Request model for updating an appointment."""
    
    patient_name: str | None = Field(default=None, min_length=1, max_length=200)
    patient_phone: str | None = Field(default=None, pattern=r"^\+?[1-9]\d{7,14}$")
    doctor_id: str | None = Field(default=None, min_length=1)
    department: str | None = Field(default=None, min_length=1, max_length=100)
    scheduled_at: datetime | None = None
    status: str | None = Field(default=None, pattern=r"^(scheduled|confirmed|cancelled|completed)$")
    notes: str | None = Field(default=None, max_length=1000)


class AppointmentResponse(BaseModel):
    """Response model for an appointment."""
    
    id: UUID
    patient_name: str
    patient_phone: str
    doctor_id: str
    department: str
    scheduled_at: datetime
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class AppointmentsListResponse(BaseModel):
    """Response model for listing appointments."""
    
    items: list[AppointmentResponse]
    total: int
    page: int
    per_page: int
    pages: int


# ===========================================
# In-Memory Storage (Placeholder)
# ===========================================

# TODO: Replace with database storage
_appointments: dict[UUID, dict[str, Any]] = {}


# ===========================================
# Endpoints
# ===========================================

@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Appointment",
    description="Creates a new appointment booking.",
)
async def create_appointment(
    appointment: AppointmentCreate,
) -> dict[str, Any]:
    """
    Create a new appointment.
    
    Args:
        appointment: Appointment creation data
    
    Returns:
        Created appointment
    """
    logger.info(f"Creating appointment for {appointment.patient_name}")
    
    now = datetime.now()
    appointment_id = uuid4()
    
    appointment_data = {
        "id": appointment_id,
        "patient_name": appointment.patient_name,
        "patient_phone": appointment.patient_phone,
        "doctor_id": appointment.doctor_id,
        "department": appointment.department,
        "scheduled_at": appointment.scheduled_at,
        "status": "scheduled",
        "notes": appointment.notes,
        "created_at": now,
        "updated_at": now,
    }
    
    _appointments[appointment_id] = appointment_data
    
    logger.info(f"Created appointment: {appointment_id}")
    return appointment_data


@router.get(
    "",
    response_model=AppointmentsListResponse,
    summary="List Appointments",
    description="Retrieves a paginated list of appointments.",
)
async def list_appointments(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None, pattern=r"^(scheduled|confirmed|cancelled|completed)$"),
    department: str | None = None,
) -> dict[str, Any]:
    """
    List appointments with pagination and filtering.
    
    Args:
        page: Page number (1-indexed)
        per_page: Items per page
        status: Filter by appointment status
        department: Filter by department
    
    Returns:
        Paginated list of appointments
    """
    # Filter appointments
    filtered = list(_appointments.values())
    
    if status:
        filtered = [a for a in filtered if a["status"] == status]
    
    if department:
        filtered = [a for a in filtered if a["department"] == department]
    
    # Sort by scheduled_at descending
    filtered.sort(key=lambda x: x["scheduled_at"], reverse=True)
    
    # Paginate
    total = len(filtered)
    pages = (total + per_page - 1) // per_page if total > 0 else 1
    start = (page - 1) * per_page
    end = start + per_page
    items = filtered[start:end]
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Get Appointment",
    description="Retrieves a specific appointment by ID.",
)
async def get_appointment(appointment_id: UUID) -> dict[str, Any]:
    """
    Get a specific appointment.
    
    Args:
        appointment_id: Appointment UUID
    
    Returns:
        Appointment details
    
    Raises:
        HTTPException: If appointment not found
    """
    if appointment_id not in _appointments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found",
        )
    
    return _appointments[appointment_id]


@router.put(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Update Appointment",
    description="Updates an existing appointment.",
)
async def update_appointment(
    appointment_id: UUID,
    update: AppointmentUpdate,
) -> dict[str, Any]:
    """
    Update an existing appointment.
    
    Args:
        appointment_id: Appointment UUID
        update: Fields to update
    
    Returns:
        Updated appointment
    
    Raises:
        HTTPException: If appointment not found
    """
    if appointment_id not in _appointments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found",
        )
    
    appointment = _appointments[appointment_id]
    update_data = update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if value is not None:
            appointment[field] = value
    
    appointment["updated_at"] = datetime.now()
    
    logger.info(f"Updated appointment: {appointment_id}")
    return appointment


@router.delete(
    "/{appointment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Appointment",
    description="Deletes an appointment.",
)
async def delete_appointment(appointment_id: UUID) -> None:
    """
    Delete an appointment.
    
    Args:
        appointment_id: Appointment UUID
    
    Raises:
        HTTPException: If appointment not found
    """
    if appointment_id not in _appointments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found",
        )
    
    del _appointments[appointment_id]
    logger.info(f"Deleted appointment: {appointment_id}")


@router.post(
    "/{appointment_id}/confirm",
    response_model=AppointmentResponse,
    summary="Confirm Appointment",
    description="Confirms a scheduled appointment.",
)
async def confirm_appointment(appointment_id: UUID) -> dict[str, Any]:
    """
    Confirm a scheduled appointment.
    
    Args:
        appointment_id: Appointment UUID
    
    Returns:
        Updated appointment
    
    Raises:
        HTTPException: If appointment not found or already confirmed
    """
    if appointment_id not in _appointments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found",
        )
    
    appointment = _appointments[appointment_id]
    
    if appointment["status"] != "scheduled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot confirm appointment with status: {appointment['status']}",
        )
    
    appointment["status"] = "confirmed"
    appointment["updated_at"] = datetime.now()
    
    logger.info(f"Confirmed appointment: {appointment_id}")
    return appointment


@router.post(
    "/{appointment_id}/cancel",
    response_model=AppointmentResponse,
    summary="Cancel Appointment",
    description="Cancels an appointment.",
)
async def cancel_appointment(appointment_id: UUID) -> dict[str, Any]:
    """
    Cancel an appointment.
    
    Args:
        appointment_id: Appointment UUID
    
    Returns:
        Updated appointment
    
    Raises:
        HTTPException: If appointment not found or already completed
    """
    if appointment_id not in _appointments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found",
        )
    
    appointment = _appointments[appointment_id]
    
    if appointment["status"] == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a completed appointment",
        )
    
    appointment["status"] = "cancelled"
    appointment["updated_at"] = datetime.now()
    
    logger.info(f"Cancelled appointment: {appointment_id}")
    return appointment
