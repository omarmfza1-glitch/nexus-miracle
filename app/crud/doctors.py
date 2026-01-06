"""
Nexus Miracle - Doctor CRUD Operations

Database operations for doctors and their availability.
"""

from datetime import date, datetime, time, timedelta

from loguru import logger
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Appointment, Doctor, TimeSlot
from app.schemas.time_slots import AvailableSlot


async def get_all_doctors(
    session: AsyncSession,
    *,
    specialty: str | None = None,
    specialty_ar: str | None = None,
    branch: str | None = None,
    status: str = "active",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Doctor], int]:
    """
    Get all doctors with optional filtering and pagination.
    
    Args:
        session: Database session
        specialty: Filter by specialty (English)
        specialty_ar: Filter by specialty (Arabic)
        branch: Filter by branch
        status: Filter by status (default: active)
        page: Page number (1-indexed)
        per_page: Items per page
    
    Returns:
        Tuple of (list of doctors, total count)
    """
    # Build query
    query = select(Doctor).where(
        Doctor.is_deleted == False,
        Doctor.status == status,
    )
    
    # Use OR for specialty search (match English OR Arabic)
    if specialty or specialty_ar:
        search_term = specialty or specialty_ar
        query = query.where(
            or_(
                Doctor.specialty.ilike(f"%{search_term}%"),
                Doctor.specialty_ar.ilike(f"%{search_term}%"),
            )
        )
    
    if branch:
        query = query.where(Doctor.branch.ilike(f"%{branch}%"))
    
    # Get total count
    count_query = select(Doctor.id).where(
        Doctor.is_deleted == False,
        Doctor.status == status,
    )
    if specialty or specialty_ar:
        search_term = specialty or specialty_ar
        count_query = count_query.where(
            or_(
                Doctor.specialty.ilike(f"%{search_term}%"),
                Doctor.specialty_ar.ilike(f"%{search_term}%"),
            )
        )
    if branch:
        count_query = count_query.where(Doctor.branch.ilike(f"%{branch}%"))
    
    result = await session.execute(count_query)
    total = len(result.all())
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Doctor.name_ar)
    
    result = await session.execute(query)
    doctors = list(result.scalars().all())
    
    logger.debug(f"Found {len(doctors)} doctors (total: {total})")
    return doctors, total


async def get_doctor_by_id(
    session: AsyncSession,
    doctor_id: int,
) -> Doctor | None:
    """
    Get a doctor by ID.
    
    Args:
        session: Database session
        doctor_id: Doctor ID
    
    Returns:
        Doctor if found, None otherwise
    """
    query = select(Doctor).where(
        Doctor.id == doctor_id,
        Doctor.is_deleted == False,
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_doctors_by_specialty(
    session: AsyncSession,
    specialty: str,
) -> list[Doctor]:
    """
    Get doctors by specialty (searches both English and Arabic).
    
    Args:
        session: Database session
        specialty: Specialty to search for
    
    Returns:
        List of matching doctors
    """
    query = select(Doctor).where(
        Doctor.is_deleted == False,
        Doctor.status == "active",
        (Doctor.specialty.ilike(f"%{specialty}%")) | 
        (Doctor.specialty_ar.ilike(f"%{specialty}%")),
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_available_slots_for_date(
    session: AsyncSession,
    doctor_id: int,
    target_date: date,
    slot_duration_minutes: int = 30,
) -> list[AvailableSlot]:
    """
    Get available time slots for a doctor on a specific date.
    
    Args:
        session: Database session
        doctor_id: Doctor ID
        target_date: Date to check availability
        slot_duration_minutes: Duration of each slot in minutes
    
    Returns:
        List of available slots
    """
    # Get day of week (0=Sunday in Saudi convention)
    # Python weekday: 0=Monday, 6=Sunday
    python_weekday = target_date.weekday()
    # Convert to Saudi convention: Sunday=0, Monday=1, ..., Saturday=6
    saudi_day = (python_weekday + 1) % 7
    
    # Get doctor's time slots for this day
    slot_query = select(TimeSlot).where(
        TimeSlot.doctor_id == doctor_id,
        TimeSlot.day_of_week == saudi_day,
        TimeSlot.is_available == True,
    )
    result = await session.execute(slot_query)
    time_slots = result.scalars().all()
    
    if not time_slots:
        logger.debug(f"No time slots for doctor {doctor_id} on day {saudi_day}")
        return []
    
    # Get existing appointments for this doctor on this date
    day_start = datetime.combine(target_date, time(0, 0))
    day_end = datetime.combine(target_date, time(23, 59, 59))
    
    appt_query = select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.datetime >= day_start,
        Appointment.datetime <= day_end,
        Appointment.status.in_(["pending", "confirmed"]),
        Appointment.is_deleted == False,
    )
    result = await session.execute(appt_query)
    existing_appointments = result.scalars().all()
    
    # Create set of booked times
    booked_times = {appt.datetime for appt in existing_appointments}
    
    # Generate available slots
    available_slots: list[AvailableSlot] = []
    
    for ts in time_slots:
        current_time = datetime.combine(target_date, ts.start_time)
        end_time = datetime.combine(target_date, ts.end_time)
        
        while current_time + timedelta(minutes=slot_duration_minutes) <= end_time:
            # Check if slot is not booked and is in the future
            if current_time not in booked_times and current_time > datetime.now():
                available_slots.append(AvailableSlot(
                    slot_datetime=current_time,
                    duration_minutes=slot_duration_minutes,
                    is_available=True,
                ))
            current_time += timedelta(minutes=slot_duration_minutes)
    
    logger.debug(f"Found {len(available_slots)} available slots for doctor {doctor_id} on {target_date}")
    return available_slots
