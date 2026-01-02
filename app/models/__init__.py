"""
Nexus Miracle - Models Package

Data models for the application.
"""

from app.models.appointments import (
    Appointment,
    AppointmentStatus,
)
from app.models.conversation import (
    CallState,
    ConversationMessage,
    ConversationRole,
    ConversationSession,
)
from app.models.settings import (
    AdminSettings,
    SystemSettings,
    VoiceSettings,
)

__all__ = [
    # Conversation
    "CallState",
    "ConversationMessage",
    "ConversationRole",
    "ConversationSession",
    # Settings
    "AdminSettings",
    "SystemSettings",
    "VoiceSettings",
    # Appointments
    "Appointment",
    "AppointmentStatus",
]
