"""
Nexus Miracle - Appointments Router

CRUD operations for appointment bookings with database integration.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.appointments import (
    cancel_appointment,
    confirm_appointment,
    create_appointment,
    get_appointment_by_id,
    get_appointments_by_patient,
)
from app.crud.doctors import get_doctor_by_id
from app.crud.patients import get_or_create_patient
from app.schemas.appointments import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
    CancelAppointmentRequest,
)
from app.services.db_service import get_db

router = APIRouter()


def _appointment_to_response(appointment) -> AppointmentResponse:
    """Convert appointment model to response schema."""
    return AppointmentResponse(
        id=appointment.id,
        patient_id=appointment.patient_id,
        patient_name=appointment.patient.name_ar or appointment.patient.name,
        patient_phone=appointment.patient.phone,
        doctor_id=appointment.doctor_id,
        doctor_name=appointment.doctor.name,
        doctor_name_ar=appointment.doctor.name_ar,
        specialty=appointment.doctor.specialty,
        specialty_ar=appointment.doctor.specialty_ar,
        scheduled_at=appointment.datetime,
        duration_minutes=appointment.duration_minutes,
        status=appointment.status,
        notes=appointment.notes,
        reminder_sent=appointment.reminder_sent,
        booked_via_call=appointment.booked_via_call,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at,
    )


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Appointment",
    description="Book a new appointment.",
)
async def book_appointment(
    appointment: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
) -> AppointmentResponse:
    """
    Book a new appointment.
    
    If the patient doesn't exist, they will be created automatically.
    Phone number must be in Saudi format (+966 or 05).
    """
    logger.info(f"Booking appointment: {appointment.phone} with doctor {appointment.doctor_id}")
    
    # Verify doctor exists
    doctor = await get_doctor_by_id(db, appointment.doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {appointment.doctor_id} not found",
        )
    
    # Validate appointment time is in the future
    if appointment.scheduled_at <= datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment time must be in the future",
        )
    
    # Get or create patient
    patient, created = await get_or_create_patient(db, appointment.phone)
    if created:
        logger.info(f"Created new patient: {patient.id}")
    
    # Create appointment
    new_appointment = await create_appointment(
        db,
        patient_id=patient.id,
        doctor_id=appointment.doctor_id,
        appointment_datetime=appointment.scheduled_at,
        notes=appointment.notes,
    )
    
    # Reload with relations
    new_appointment = await get_appointment_by_id(db, new_appointment.id)
    
    logger.info(f"Created appointment: {new_appointment.id}")
    return _appointment_to_response(new_appointment)


@router.get(
    "",
    response_model=AppointmentListResponse,
    summary="List Appointments",
    description="Get appointments filtered by phone number.",
)
async def list_appointments(
    phone: str | None = Query(
        default=None,
        description="Filter by patient phone number"
    ),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern=r"^(pending|confirmed|cancelled|completed|no_show)$",
        description="Filter by status"
    ),
    upcoming_only: bool = Query(
        default=False,
        description="Only return future appointments"
    ),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> AppointmentListResponse:
    """
    List appointments with optional filtering.
    
    Filter by phone number to get a specific patient's appointments.
    """
    appointments, total = await get_appointments_by_patient(
        db,
        phone=phone,
        status=status_filter,
        upcoming_only=upcoming_only,
        page=page,
        per_page=per_page,
    )
    
    pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    return AppointmentListResponse(
        items=[_appointment_to_response(a) for a in appointments],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Get Appointment",
    description="Get details for a specific appointment.",
)
async def get_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
) -> AppointmentResponse:
    """Get an appointment by ID."""
    appointment = await get_appointment_by_id(db, appointment_id)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found",
        )
    
    return _appointment_to_response(appointment)


@router.put(
    "/{appointment_id}/cancel",
    response_model=AppointmentResponse,
    summary="Cancel Appointment",
    description="Cancel an existing appointment.",
)
async def cancel_appointment_endpoint(
    appointment_id: int,
    request: CancelAppointmentRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> AppointmentResponse:
    """
    Cancel an appointment.
    
    Only pending or confirmed appointments can be cancelled.
    """
    reason = request.reason if request else None
    
    appointment = await cancel_appointment(db, appointment_id, reason=reason)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found or cannot be cancelled",
        )
    
    logger.info(f"Cancelled appointment: {appointment_id}")
    return _appointment_to_response(appointment)


@router.post(
    "/{appointment_id}/confirm",
    response_model=AppointmentResponse,
    summary="Confirm Appointment",
    description="Confirm a pending appointment.",
)
async def confirm_appointment_endpoint(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
) -> AppointmentResponse:
    """
    Confirm a pending appointment.
    
    Only pending appointments can be confirmed.
    """
    appointment = await confirm_appointment(db, appointment_id)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found or already confirmed",
        )
    
    logger.info(f"Confirmed appointment: {appointment_id}")
    return _appointment_to_response(appointment)
