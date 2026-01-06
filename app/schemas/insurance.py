"""
Nexus Miracle - Insurance Schemas

Pydantic schemas for insurance-related API endpoints.
"""

from pydantic import BaseModel, Field


class InsuranceCoverage(BaseModel):
    """Insurance coverage details."""
    
    id: int = Field(description="Insurance record ID")
    company_name: str = Field(description="Company name (English)")
    company_name_ar: str = Field(description="Company name (Arabic)")
    is_covered: bool = Field(description="Whether this insurance is accepted")
    coverage_percent: int = Field(description="Coverage percentage (0-100)")
    copay_sar: float = Field(description="Copay amount in Saudi Riyals")
    network: str | None = Field(description="Network tier (vip/gold/silver/basic)")
    notes: str | None = Field(description="Additional notes (English)")
    notes_ar: str | None = Field(description="Additional notes (Arabic)")
    
    model_config = {"from_attributes": True}


class InsuranceCheckResponse(BaseModel):
    """Response for insurance coverage check."""
    
    found: bool = Field(description="Whether insurance was found")
    query: str = Field(description="Original search query")
    coverage: InsuranceCoverage | None = Field(
        default=None,
        description="Coverage details if found"
    )
    message: str = Field(description="Human-readable message")
    message_ar: str = Field(description="Message in Arabic")
