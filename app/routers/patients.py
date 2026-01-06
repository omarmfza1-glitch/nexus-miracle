"""
Nexus Miracle - Patients Router

Patient management endpoints for the admin dashboard.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Patient
from app.services.db_service import get_db

router = APIRouter()


# ===========================================
# Request/Response Models
# ===========================================

class PatientResponse(BaseModel):
    """Patient response model."""
    id: int
    phone: str
    name: str | None = None
    name_ar: str | None = None
    national_id_last4: str | None = None
    gender: str | None = None
    insurance_company: str | None = None
    insurance_id: str | None = None
    language: str = "ar"
    
    model_config = {"from_attributes": True}


class PatientListResponse(BaseModel):
    """Paginated patient list response."""
    items: list[PatientResponse]
    total: int
    page: int
    per_page: int
    pages: int


class PatientUpdateRequest(BaseModel):
    """Update patient request."""
    name: str | None = None
    name_ar: str | None = None
    national_id_last4: str | None = Field(default=None, min_length=4, max_length=4)
    gender: str | None = None
    insurance_company: str | None = None
    insurance_id: str | None = None
    language: str | None = None


# ===========================================
# Endpoints
# ===========================================

@router.get(
    "",
    response_model=PatientListResponse,
    summary="List Patients",
    description="Returns paginated list of patients with optional search.",
)
async def list_patients(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, description="Search by phone, name, or name_ar"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List patients with pagination and search."""
    # Build query
    query = select(Patient).where(Patient.is_deleted == False)
    count_query = select(func.count(Patient.id)).where(Patient.is_deleted == False)
    
    if search:
        search_filter = or_(
            Patient.phone.contains(search),
            Patient.name.ilike(f"%{search}%"),
            Patient.name_ar.contains(search),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(Patient.created_at.desc()).offset(offset).limit(per_page)
    
    result = await session.execute(query)
    items = list(result.scalars().all())
    
    pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get Patient",
    description="Returns a single patient by ID.",
)
async def get_patient(
    patient_id: int,
    session: AsyncSession = Depends(get_db),
) -> Patient:
    """Get a specific patient."""
    result = await session.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.is_deleted == False,
        )
    )
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    return patient


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Update Patient",
    description="Updates patient information.",
)
async def update_patient(
    patient_id: int,
    request: PatientUpdateRequest,
    session: AsyncSession = Depends(get_db),
) -> Patient:
    """Update patient information."""
    result = await session.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.is_deleted == False,
        )
    )
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    # Update fields
    update_data = request.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in update_data.items():
        setattr(patient, field, value)
    
    await session.commit()
    await session.refresh(patient)
    
    logger.info(f"Updated patient {patient_id}")
    return patient


@router.get(
    "/by-phone/{phone}",
    response_model=PatientResponse,
    summary="Get Patient by Phone",
    description="Returns patient by phone number.",
)
async def get_patient_by_phone(
    phone: str,
    session: AsyncSession = Depends(get_db),
) -> Patient:
    """Get patient by phone number."""
    # Normalize phone
    normalized = phone.replace(" ", "").replace("-", "")
    if normalized.startswith("05"):
        normalized = "+966" + normalized[1:]
    
    result = await session.execute(
        select(Patient).where(
            Patient.phone == normalized,
            Patient.is_deleted == False,
        )
    )
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    return patient
