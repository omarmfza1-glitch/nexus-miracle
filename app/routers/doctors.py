"""
Nexus Miracle - Doctors Router

API endpoints for doctor management and availability.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.doctors import (
    get_all_doctors,
    get_available_slots_for_date,
    get_doctor_by_id,
)
from app.schemas.doctors import DoctorListResponse, DoctorResponse
from app.schemas.time_slots import AvailableSlotsResponse
from app.services.db_service import get_db

router = APIRouter()


@router.get(
    "",
    response_model=DoctorListResponse,
    summary="List Doctors",
    description="Get a paginated list of doctors with optional filtering.",
)
async def list_doctors(
    specialty: str | None = Query(
        default=None,
        description="Filter by specialty (supports Arabic: عظام, باطنية, etc.)"
    ),
    branch: str | None = Query(
        default=None,
        description="Filter by branch"
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> DoctorListResponse:
    """
    List doctors with optional filtering by specialty and branch.
    
    Supports Arabic specialty names like عظام (orthopedics), باطنية (internal medicine).
    """
    # Try both specialty and specialty_ar
    doctors, total = await get_all_doctors(
        db,
        specialty=specialty,
        specialty_ar=specialty,
        branch=branch,
        page=page,
        per_page=per_page,
    )
    
    pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    return DoctorListResponse(
        items=[DoctorResponse.model_validate(d) for d in doctors],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/{doctor_id}",
    response_model=DoctorResponse,
    summary="Get Doctor",
    description="Get details for a specific doctor.",
)
async def get_doctor(
    doctor_id: int,
    db: AsyncSession = Depends(get_db),
) -> DoctorResponse:
    """Get a doctor by ID."""
    doctor = await get_doctor_by_id(db, doctor_id)
    
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {doctor_id} not found",
        )
    
    return DoctorResponse.model_validate(doctor)


@router.get(
    "/{doctor_id}/slots",
    response_model=AvailableSlotsResponse,
    summary="Get Available Slots",
    description="Get available appointment slots for a doctor on a specific date.",
)
async def get_doctor_slots(
    doctor_id: int,
    target_date: date = Query(
        alias="date",
        description="Date to check availability (YYYY-MM-DD)"
    ),
    db: AsyncSession = Depends(get_db),
) -> AvailableSlotsResponse:
    """
    Get available time slots for a doctor on a specific date.
    
    Returns 30-minute slots that are not already booked.
    """
    # Verify doctor exists
    doctor = await get_doctor_by_id(db, doctor_id)
    
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {doctor_id} not found",
        )
    
    slots = await get_available_slots_for_date(db, doctor_id, target_date)
    
    logger.info(f"Found {len(slots)} available slots for doctor {doctor_id} on {target_date}")
    
    return AvailableSlotsResponse(
        doctor_id=doctor_id,
        doctor_name=doctor.name,
        doctor_name_ar=doctor.name_ar,
        slot_date=target_date,
        slots=slots,
        total_available=len(slots),
    )
