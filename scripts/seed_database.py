"""
Nexus Miracle - Database Seed Script

Populates the database with sample data for:
- 5 Doctors with Arabic names
- 5 Insurance companies
- Time slots for next 30 days
- 3 Sample patients with appointments
"""

import asyncio
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from app.models.database import (
    Appointment,
    Base,
    Doctor,
    Insurance,
    Patient,
    TimeSlot,
)
from app.services.db_service import close_db, get_engine, init_db


# ===========================================
# Seed Data
# ===========================================

DOCTORS = [
    {
        "name": "Fahad Al-Ghamdi",
        "name_ar": "فهد الغامدي",
        "specialty": "Orthopedics",
        "specialty_ar": "عظام",
        "branch": "الفرع الرئيسي",
        "bio": "Board-certified orthopedic surgeon with 15 years of experience.",
        "bio_ar": "جراح عظام معتمد بخبرة 15 سنة.",
        "rating": 4.9,
    },
    {
        "name": "Khaled Al-Otaibi",
        "name_ar": "خالد العتيبي",
        "specialty": "Orthopedics",
        "specialty_ar": "عظام",
        "branch": "فرع الملقا",
        "bio": "Specialist in sports medicine and joint surgery.",
        "bio_ar": "متخصص في الطب الرياضي وجراحة المفاصل.",
        "rating": 4.8,
    },
    {
        "name": "Noura Al-Shammari",
        "name_ar": "نورة الشمري",
        "specialty": "Internal Medicine",
        "specialty_ar": "باطنية",
        "branch": "الفرع الرئيسي",
        "bio": "Internal medicine specialist focusing on chronic disease management.",
        "bio_ar": "أخصائية باطنية متخصصة في إدارة الأمراض المزمنة.",
        "rating": 4.9,
    },
    {
        "name": "Mohammed Al-Qahtani",
        "name_ar": "محمد القحطاني",
        "specialty": "Dermatology",
        "specialty_ar": "جلدية",
        "branch": "الفرع الرئيسي",
        "bio": "Expert dermatologist in cosmetic and medical dermatology.",
        "bio_ar": "طبيب جلدية خبير في الأمراض الجلدية والتجميل.",
        "rating": 4.7,
    },
    {
        "name": "Sarah Al-Dosari",
        "name_ar": "سارة الدوسري",
        "specialty": "Pediatrics",
        "specialty_ar": "أطفال",
        "branch": "فرع الملقا",
        "bio": "Caring pediatrician specializing in newborn and child health.",
        "bio_ar": "طبيبة أطفال متخصصة في صحة المواليد والأطفال.",
        "rating": 5.0,
    },
]

INSURANCE_COMPANIES = [
    {
        "company_name": "Tawuniya",
        "company_name_ar": "التعاونية",
        "name_variations": ["التعاونيه", "تعاونية", "تعاونيه", "al tawuniya", "altawuniya"],
        "is_covered": True,
        "coverage_percent": 80,
        "copay_sar": 50.0,
        "network": "gold",
        "notes": "Full coverage for most services",
        "notes_ar": "تغطية كاملة لمعظم الخدمات",
    },
    {
        "company_name": "Bupa",
        "company_name_ar": "بوبا",
        "name_variations": ["بوبه", "buba", "bopa"],
        "is_covered": True,
        "coverage_percent": 90,
        "copay_sar": 30.0,
        "network": "vip",
        "notes": "Premium coverage with minimal copay",
        "notes_ar": "تغطية مميزة مع حد أدنى للمشاركة",
    },
    {
        "company_name": "MedGulf",
        "company_name_ar": "ميدغلف",
        "name_variations": ["ميد غلف", "medgolf", "med gulf", "الخليج للتأمين"],
        "is_covered": True,
        "coverage_percent": 75,
        "copay_sar": 75.0,
        "network": "silver",
        "notes": "Standard coverage",
        "notes_ar": "تغطية عادية",
    },
    {
        "company_name": "AlRajhi Takaful",
        "company_name_ar": "الراجحي",
        "name_variations": ["راجحي", "الراجحي تكافل", "rajhi", "alrajhi"],
        "is_covered": True,
        "coverage_percent": 70,
        "copay_sar": 80.0,
        "network": "silver",
        "notes": "Coverage for essential services",
        "notes_ar": "تغطية للخدمات الأساسية",
    },
    {
        "company_name": "Wafa",
        "company_name_ar": "وفا",
        "name_variations": ["وفاء", "wafaa"],
        "is_covered": False,
        "coverage_percent": 0,
        "copay_sar": 0.0,
        "network": None,
        "notes": "Not contracted - self-pay only",
        "notes_ar": "غير متعاقد - الدفع نقداً فقط",
    },
]

PATIENTS = [
    {
        "phone": "+966501234567",
        "name": "Abdullah Al-Harbi",
        "name_ar": "عبدالله الحربي",
        "national_id_last4": "1234",
        "gender": "male",
        "insurance_company": "التعاونية",
        "insurance_id": "TAW-123456",
        "language": "ar",
    },
    {
        "phone": "+966551234567",
        "name": "Fatima Al-Saeed",
        "name_ar": "فاطمة السعيد",
        "national_id_last4": "5678",
        "gender": "female",
        "insurance_company": "بوبا",
        "insurance_id": "BUPA-789012",
        "language": "ar",
    },
    {
        "phone": "+966541234567",
        "name": "Youssef Al-Malki",
        "name_ar": "يوسف المالكي",
        "national_id_last4": "9012",
        "gender": "male",
        "insurance_company": "ميدغلف",
        "insurance_id": "MED-345678",
        "language": "ar",
    },
]


# ===========================================
# Time Slot Generation
# ===========================================

def generate_time_slots_for_doctor(doctor_id: int) -> list[TimeSlot]:
    """Generate weekly time slots for a doctor."""
    slots = []
    
    # Sunday-Thursday: 8 AM - 10 PM
    for day in range(5):  # 0=Sunday to 4=Thursday
        slots.append(TimeSlot(
            doctor_id=doctor_id,
            day_of_week=day,
            start_time=time(8, 0),
            end_time=time(14, 0),
            is_available=True,
        ))
        slots.append(TimeSlot(
            doctor_id=doctor_id,
            day_of_week=day,
            start_time=time(16, 0),
            end_time=time(22, 0),
            is_available=True,
        ))
    
    # Friday: 4 PM - 10 PM only
    slots.append(TimeSlot(
        doctor_id=doctor_id,
        day_of_week=5,  # Friday
        start_time=time(16, 0),
        end_time=time(22, 0),
        is_available=True,
    ))
    
    # Saturday: Optional rest day (no slots)
    
    return slots


# ===========================================
# Seed Functions
# ===========================================

async def seed_database():
    """Seed the database with sample data."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    
    logger.info("Starting database seeding...")
    
    # Initialize database
    await init_db()
    
    # Create tables
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Tables created")
    
    # Create session
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Seed doctors
        logger.info("Seeding doctors...")
        doctors = []
        for doctor_data in DOCTORS:
            doctor = Doctor(**doctor_data)
            session.add(doctor)
            doctors.append(doctor)
        await session.flush()
        
        for doctor in doctors:
            await session.refresh(doctor)
            logger.info(f"  Created doctor: {doctor.id} - {doctor.name_ar}")
        
        # Seed time slots for each doctor
        logger.info("Seeding time slots...")
        for doctor in doctors:
            slots = generate_time_slots_for_doctor(doctor.id)
            for slot in slots:
                session.add(slot)
        await session.flush()
        logger.info(f"  Created {len(doctors) * 11} time slots")
        
        # Seed insurance companies
        logger.info("Seeding insurance companies...")
        for insurance_data in INSURANCE_COMPANIES:
            insurance = Insurance(**insurance_data)
            session.add(insurance)
            logger.info(f"  Created insurance: {insurance.company_name_ar}")
        await session.flush()
        
        # Seed patients
        logger.info("Seeding patients...")
        patients = []
        for patient_data in PATIENTS:
            patient = Patient(**patient_data)
            session.add(patient)
            patients.append(patient)
        await session.flush()
        
        for patient in patients:
            await session.refresh(patient)
            logger.info(f"  Created patient: {patient.id} - {patient.name_ar}")
        
        # Seed sample appointments
        logger.info("Seeding sample appointments...")
        tomorrow = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        # Appointment 1: Abdullah with Dr. Fahad (Orthopedics)
        appt1 = Appointment(
            patient_id=patients[0].id,
            doctor_id=doctors[0].id,
            datetime=tomorrow,
            status="confirmed",
            notes="Follow-up for knee pain",
            duration_minutes=30,
        )
        session.add(appt1)
        
        # Appointment 2: Fatima with Dr. Noura (Internal Medicine)
        appt2 = Appointment(
            patient_id=patients[1].id,
            doctor_id=doctors[2].id,
            datetime=tomorrow + timedelta(hours=2),
            status="pending",
            notes="Annual checkup",
            duration_minutes=30,
        )
        session.add(appt2)
        
        # Appointment 3: Youssef with Dr. Sarah (Pediatrics) - for his child
        appt3 = Appointment(
            patient_id=patients[2].id,
            doctor_id=doctors[4].id,
            datetime=tomorrow + timedelta(days=1),
            status="pending",
            notes="Child vaccination",
            duration_minutes=30,
        )
        session.add(appt3)
        
        await session.commit()
        logger.info("  Created 3 sample appointments")
    
    await close_db()
    
    logger.info("=" * 50)
    logger.info("Database seeding completed successfully!")
    logger.info("=" * 50)
    logger.info("")
    logger.info("Summary:")
    logger.info(f"  - {len(DOCTORS)} doctors")
    logger.info(f"  - {len(INSURANCE_COMPANIES)} insurance companies")
    logger.info(f"  - {len(PATIENTS)} patients")
    logger.info(f"  - 3 sample appointments")
    logger.info(f"  - {len(DOCTORS) * 11} time slots")


if __name__ == "__main__":
    # Setup logging
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        colorize=True,
    )
    
    asyncio.run(seed_database())
