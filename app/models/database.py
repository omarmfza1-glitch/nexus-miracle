"""
Nexus Miracle - SQLAlchemy Database Models

ORM models for the medical clinic database with support for Arabic names,
Saudi phone numbers, and timezone-aware timestamps.
"""

from datetime import datetime, time
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ===========================================
# Base Model
# ===========================================

class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )


# ===========================================
# Doctor Model
# ===========================================

class Doctor(Base, TimestampMixin, SoftDeleteMixin):
    """Medical doctor/physician model."""
    
    __tablename__ = "doctors"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Names (English and Arabic)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # Specialty (English and Arabic)
    specialty: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    specialty_ar: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Branch/Location
    branch: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
    )  # active, inactive, on_leave
    
    # Profile
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    
    # Relationships
    time_slots: Mapped[list["TimeSlot"]] = relationship(
        "TimeSlot",
        back_populates="doctor",
        lazy="selectin",
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment",
        back_populates="doctor",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Doctor(id={self.id}, name='{self.name}', specialty='{self.specialty}')>"


# ===========================================
# Patient Model
# ===========================================

class Patient(Base, TimestampMixin, SoftDeleteMixin):
    """Patient model with Saudi-specific fields."""
    
    __tablename__ = "patients"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Phone (primary identifier for lookups)
    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
    )  # Format: +966XXXXXXXXX or 05XXXXXXXX
    
    # National ID (last 4 digits for verification)
    national_id_last4: Mapped[str | None] = mapped_column(
        String(4),
        nullable=True,
    )
    
    # Names
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    name_ar: Mapped[str | None] = mapped_column(String(200), nullable=True)
    
    # Demographics
    gender: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )  # male, female
    dob: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Insurance
    insurance_company: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    insurance_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Language preference
    language: Mapped[str] = mapped_column(
        String(5),
        default="ar",
        nullable=False,
    )  # ar, en
    
    # Relationships
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment",
        back_populates="patient",
        lazy="selectin",
    )
    call_logs: Mapped[list["CallLog"]] = relationship(
        "CallLog",
        back_populates="patient",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, phone='{self.phone}', name='{self.name}')>"


# ===========================================
# Appointment Model
# ===========================================

class Appointment(Base, TimestampMixin, SoftDeleteMixin):
    """Medical appointment booking model."""
    
    __tablename__ = "appointments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=False,
        index=True,
    )
    
    # Scheduling
    datetime: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False,
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )  # pending, confirmed, cancelled, completed, no_show
    
    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Reminders
    reminder_sent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    
    # Call tracking
    booked_via_call: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    call_log_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("call_logs.id"),
        nullable=True,
    )
    
    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="appointments",
    )
    doctor: Mapped["Doctor"] = relationship(
        "Doctor",
        back_populates="appointments",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_appointments_datetime_status", "datetime", "status"),
        Index("ix_appointments_doctor_datetime", "doctor_id", "datetime"),
    )
    
    def __repr__(self) -> str:
        return f"<Appointment(id={self.id}, patient_id={self.patient_id}, doctor_id={self.doctor_id}, datetime='{self.datetime}')>"


# ===========================================
# TimeSlot Model
# ===========================================

class TimeSlot(Base, TimestampMixin):
    """Doctor availability time slot model."""
    
    __tablename__ = "time_slots"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key
    doctor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=False,
        index=True,
    )
    
    # Day of week (0=Sunday, 1=Monday, ..., 6=Saturday)
    # Note: Sunday is first day in Saudi Arabia
    day_of_week: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        index=True,
    )
    
    # Time window
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    
    # Availability
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # Relationships
    doctor: Mapped["Doctor"] = relationship(
        "Doctor",
        back_populates="time_slots",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_time_slots_doctor_day", "doctor_id", "day_of_week"),
    )
    
    def __repr__(self) -> str:
        return f"<TimeSlot(id={self.id}, doctor_id={self.doctor_id}, day={self.day_of_week}, {self.start_time}-{self.end_time})>"


# ===========================================
# Insurance Model
# ===========================================

class Insurance(Base, TimestampMixin):
    """Insurance company and coverage model."""
    
    __tablename__ = "insurance"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Company name (primary, English)
    company_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Arabic name and variations for fuzzy matching
    company_name_ar: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    name_variations: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )  # List of alternative names/spellings
    
    # Coverage details
    is_covered: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    coverage_percent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )  # 0-100
    copay_sar: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )  # Copay in Saudi Riyals
    
    # Network
    network: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # vip, gold, silver, basic
    
    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Insurance(id={self.id}, company='{self.company_name}', covered={self.is_covered})>"


# ===========================================
# CallLog Model
# ===========================================

class CallLog(Base, TimestampMixin):
    """Phone call log for tracking AI assistant interactions."""
    
    __tablename__ = "call_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Phone number
    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    
    # Call timing
    start_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Call details
    call_direction: Mapped[str] = mapped_column(
        String(10),
        default="inbound",
        nullable=False,
    )  # inbound, outbound
    call_status: Mapped[str] = mapped_column(
        String(20),
        default="completed",
        nullable=False,
    )  # completed, missed, failed
    
    # Telnyx tracking
    telnyx_call_control_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # Transcript and summary
    transcript: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )  # List of {role, content, timestamp}
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Patient link (nullable - patient may not be identified)
    patient_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("patients.id"),
        nullable=True,
        index=True,
    )
    
    # Relationships
    patient: Mapped["Patient | None"] = relationship(
        "Patient",
        back_populates="call_logs",
    )
    
    def __repr__(self) -> str:
        return f"<CallLog(id={self.id}, phone='{self.phone}', start='{self.start_time}')>"


# ===========================================
# FillerPhrase Model
# ===========================================

class FillerPhrase(Base, TimestampMixin):
    """Filler phrases used by the AI during call processing delays."""
    
    __tablename__ = "filler_phrases"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Phrase text (Arabic primary)
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Category for grouping
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # search, empathy, delay, dialog, silence, goodbye
    
    # Speaker (which AI persona uses this)
    speaker: Mapped[str] = mapped_column(
        String(20),
        default="سارة",
        nullable=False,
    )  # سارة (Sara), نِكسوس (Nexus)
    
    # Optional pre-generated audio URL
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Is active
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    def __repr__(self) -> str:
        return f"<FillerPhrase(id={self.id}, category='{self.category}', speaker='{self.speaker}')>"

