"""
Nexus Miracle - CRUD Operations Package

Database operations for all models.
"""

from app.crud.appointments import (
    cancel_appointment,
    confirm_appointment,
    create_appointment,
    get_appointment_by_id,
    get_appointments_by_doctor,
    get_appointments_by_patient,
)
from app.crud.doctors import (
    get_all_doctors,
    get_available_slots_for_date,
    get_doctor_by_id,
    get_doctors_by_specialty,
)
from app.crud.insurance import (
    check_coverage,
    get_all_insurance,
    get_insurance_by_name,
)
from app.crud.patients import (
    create_patient,
    get_or_create_patient,
    get_patient_by_phone,
    update_patient,
)

__all__ = [
    # Doctors
    "get_all_doctors",
    "get_doctor_by_id",
    "get_doctors_by_specialty",
    "get_available_slots_for_date",
    # Patients
    "get_patient_by_phone",
    "create_patient",
    "update_patient",
    "get_or_create_patient",
    # Appointments
    "create_appointment",
    "get_appointment_by_id",
    "get_appointments_by_patient",
    "get_appointments_by_doctor",
    "cancel_appointment",
    "confirm_appointment",
    # Insurance
    "get_all_insurance",
    "get_insurance_by_name",
    "check_coverage",
]
