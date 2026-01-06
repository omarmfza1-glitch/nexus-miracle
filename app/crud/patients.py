"""
Nexus Miracle - Patient CRUD Operations

Database operations for patient records.
"""

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Patient


async def get_patient_by_phone(
    session: AsyncSession,
    phone: str,
) -> Patient | None:
    """
    Get a patient by phone number.
    
    Args:
        session: Database session
        phone: Phone number (normalized to +966 format)
    
    Returns:
        Patient if found, None otherwise
    """
    # Normalize phone to +966 format
    if phone.startswith("05"):
        phone = "+966" + phone[1:]
    
    query = select(Patient).where(
        Patient.phone == phone,
        Patient.is_deleted == False,
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def create_patient(
    session: AsyncSession,
    phone: str,
    *,
    name: str | None = None,
    name_ar: str | None = None,
    national_id_last4: str | None = None,
    gender: str | None = None,
    insurance_company: str | None = None,
    insurance_id: str | None = None,
    language: str = "ar",
) -> Patient:
    """
    Create a new patient.
    
    Args:
        session: Database session
        phone: Phone number
        name: Patient name (English)
        name_ar: Patient name (Arabic)
        national_id_last4: Last 4 digits of national ID
        gender: Gender (male/female)
        insurance_company: Insurance company name
        insurance_id: Insurance ID
        language: Preferred language
    
    Returns:
        Created patient
    """
    # Normalize phone
    if phone.startswith("05"):
        phone = "+966" + phone[1:]
    
    patient = Patient(
        phone=phone,
        name=name,
        name_ar=name_ar,
        national_id_last4=national_id_last4,
        gender=gender,
        insurance_company=insurance_company,
        insurance_id=insurance_id,
        language=language,
    )
    
    session.add(patient)
    await session.flush()
    await session.refresh(patient)
    
    logger.info(f"Created patient: {patient.id} ({phone})")
    return patient


async def update_patient(
    session: AsyncSession,
    patient_id: int,
    **updates,
) -> Patient | None:
    """
    Update a patient's information.
    
    Args:
        session: Database session
        patient_id: Patient ID
        **updates: Fields to update
    
    Returns:
        Updated patient if found, None otherwise
    """
    # Filter out None values
    updates = {k: v for k, v in updates.items() if v is not None}
    
    if not updates:
        # No updates, just return the patient
        query = select(Patient).where(Patient.id == patient_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    stmt = (
        update(Patient)
        .where(Patient.id == patient_id, Patient.is_deleted == False)
        .values(**updates)
    )
    await session.execute(stmt)
    
    # Fetch updated patient
    query = select(Patient).where(Patient.id == patient_id)
    result = await session.execute(query)
    patient = result.scalar_one_or_none()
    
    if patient:
        logger.info(f"Updated patient: {patient_id}")
    
    return patient


async def get_or_create_patient(
    session: AsyncSession,
    phone: str,
    **patient_data,
) -> tuple[Patient, bool]:
    """
    Get an existing patient or create a new one.
    
    Args:
        session: Database session
        phone: Phone number
        **patient_data: Additional patient data for creation
    
    Returns:
        Tuple of (patient, created) where created is True if new patient was created
    """
    existing = await get_patient_by_phone(session, phone)
    
    if existing:
        logger.debug(f"Found existing patient: {existing.id}")
        return existing, False
    
    patient = await create_patient(session, phone, **patient_data)
    return patient, True
