"""
Nexus Miracle - Appointment CRUD Operations

Database operations for appointment bookings.
"""

from datetime import datetime

from loguru import logger
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.database import Appointment, Doctor, Patient


async def create_appointment(
    session: AsyncSession,
    patient_id: int,
    doctor_id: int,
    appointment_datetime: datetime,
    *,
    notes: str | None = None,
    booked_via_call: bool = False,
    call_log_id: int | None = None,
    duration_minutes: int = 30,
) -> Appointment:
    """
    Create a new appointment.
    
    Args:
        session: Database session
        patient_id: Patient ID
        doctor_id: Doctor ID
        appointment_datetime: Appointment date and time
        notes: Optional notes
        booked_via_call: Whether booked via phone call
        call_log_id: Associated call log ID
        duration_minutes: Appointment duration
    
    Returns:
        Created appointment
    """
    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        datetime=appointment_datetime,
        notes=notes,
        booked_via_call=booked_via_call,
        call_log_id=call_log_id,
        duration_minutes=duration_minutes,
        status="pending",
    )
    
    session.add(appointment)
    await session.flush()
    await session.refresh(appointment)
    
    logger.info(f"Created appointment: {appointment.id} for patient {patient_id} with doctor {doctor_id}")
    return appointment


async def get_appointment_by_id(
    session: AsyncSession,
    appointment_id: int,
    *,
    include_relations: bool = True,
) -> Appointment | None:
    """
    Get an appointment by ID.
    
    Args:
        session: Database session
        appointment_id: Appointment ID
        include_relations: Whether to eagerly load patient and doctor
    
    Returns:
        Appointment if found, None otherwise
    """
    query = select(Appointment).where(
        Appointment.id == appointment_id,
        Appointment.is_deleted == False,
    )
    
    if include_relations:
        query = query.options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor),
        )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_appointments_by_patient(
    session: AsyncSession,
    patient_id: int | None = None,
    phone: str | None = None,
    *,
    status: str | None = None,
    upcoming_only: bool = False,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Appointment], int]:
    """
    Get appointments for a patient.
    
    Args:
        session: Database session
        patient_id: Patient ID (optional if phone provided)
        phone: Patient phone (used if patient_id not provided)
        status: Filter by status
        upcoming_only: Only return future appointments
        page: Page number
        per_page: Items per page
    
    Returns:
        Tuple of (appointments, total count)
    """
    # Build base query
    query = select(Appointment).where(Appointment.is_deleted == False)
    
    if patient_id:
        query = query.where(Appointment.patient_id == patient_id)
    elif phone:
        # Normalize phone
        if phone.startswith("05"):
            phone = "+966" + phone[1:]
        # Join with patient to filter by phone
        query = query.join(Patient).where(Patient.phone == phone)
    
    if status:
        query = query.where(Appointment.status == status)
    
    if upcoming_only:
        query = query.where(Appointment.datetime > datetime.now())
    
    # Add relations
    query = query.options(
        joinedload(Appointment.patient),
        joinedload(Appointment.doctor),
    )
    
    # Get total count (separate query without joins for count)
    count_query = select(Appointment.id).where(Appointment.is_deleted == False)
    if patient_id:
        count_query = count_query.where(Appointment.patient_id == patient_id)
    elif phone:
        count_query = count_query.join(Patient).where(Patient.phone == phone)
    if status:
        count_query = count_query.where(Appointment.status == status)
    if upcoming_only:
        count_query = count_query.where(Appointment.datetime > datetime.now())
    
    result = await session.execute(count_query)
    total = len(result.all())
    
    # Apply pagination and ordering
    offset = (page - 1) * per_page
    query = query.order_by(Appointment.datetime.desc()).offset(offset).limit(per_page)
    
    result = await session.execute(query)
    appointments = list(result.scalars().unique().all())
    
    return appointments, total


async def get_appointments_by_doctor(
    session: AsyncSession,
    doctor_id: int,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    status: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[Appointment], int]:
    """
    Get appointments for a doctor.
    
    Args:
        session: Database session
        doctor_id: Doctor ID
        date_from: Start date filter
        date_to: End date filter
        status: Status filter
        page: Page number
        per_page: Items per page
    
    Returns:
        Tuple of (appointments, total count)
    """
    query = select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.is_deleted == False,
    )
    
    if date_from:
        query = query.where(Appointment.datetime >= date_from)
    if date_to:
        query = query.where(Appointment.datetime <= date_to)
    if status:
        query = query.where(Appointment.status == status)
    
    query = query.options(joinedload(Appointment.patient))
    
    # Count query
    count_query = select(Appointment.id).where(
        Appointment.doctor_id == doctor_id,
        Appointment.is_deleted == False,
    )
    if date_from:
        count_query = count_query.where(Appointment.datetime >= date_from)
    if date_to:
        count_query = count_query.where(Appointment.datetime <= date_to)
    if status:
        count_query = count_query.where(Appointment.status == status)
    
    result = await session.execute(count_query)
    total = len(result.all())
    
    # Paginate
    offset = (page - 1) * per_page
    query = query.order_by(Appointment.datetime).offset(offset).limit(per_page)
    
    result = await session.execute(query)
    appointments = list(result.scalars().unique().all())
    
    return appointments, total


async def cancel_appointment(
    session: AsyncSession,
    appointment_id: int,
    *,
    reason: str | None = None,
) -> Appointment | None:
    """
    Cancel an appointment.
    
    Args:
        session: Database session
        appointment_id: Appointment ID
        reason: Cancellation reason
    
    Returns:
        Updated appointment if found, None otherwise
    """
    stmt = (
        update(Appointment)
        .where(
            Appointment.id == appointment_id,
            Appointment.is_deleted == False,
            Appointment.status.in_(["pending", "confirmed"]),
        )
        .values(
            status="cancelled",
            cancellation_reason=reason,
            updated_at=datetime.now(),
        )
    )
    result = await session.execute(stmt)
    
    if result.rowcount == 0:
        logger.warning(f"Failed to cancel appointment {appointment_id}")
        return None
    
    # Fetch updated appointment
    return await get_appointment_by_id(session, appointment_id)


async def confirm_appointment(
    session: AsyncSession,
    appointment_id: int,
) -> Appointment | None:
    """
    Confirm a pending appointment.
    
    Args:
        session: Database session
        appointment_id: Appointment ID
    
    Returns:
        Updated appointment if found, None otherwise
    """
    stmt = (
        update(Appointment)
        .where(
            Appointment.id == appointment_id,
            Appointment.is_deleted == False,
            Appointment.status == "pending",
        )
        .values(
            status="confirmed",
            updated_at=datetime.now(),
        )
    )
    result = await session.execute(stmt)
    
    if result.rowcount == 0:
        logger.warning(f"Failed to confirm appointment {appointment_id}")
        return None
    
    return await get_appointment_by_id(session, appointment_id)
