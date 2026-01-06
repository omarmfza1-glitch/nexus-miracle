"""
Nexus Miracle - Insurance Router

API endpoints for insurance coverage lookups.
"""

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.insurance import check_coverage, get_all_insurance
from app.schemas.insurance import InsuranceCheckResponse, InsuranceCoverage
from app.services.db_service import get_db

router = APIRouter()


@router.get(
    "",
    response_model=list[InsuranceCoverage],
    summary="List Insurance Companies",
    description="Get all insurance companies and their coverage details.",
)
async def list_insurance(
    covered_only: bool = False,
    db: AsyncSession = Depends(get_db),
) -> list[InsuranceCoverage]:
    """
    List all insurance companies.
    
    Args:
        covered_only: Only return insurance companies that are covered
    """
    insurance_list = await get_all_insurance(db, covered_only=covered_only)
    return [InsuranceCoverage.model_validate(ins) for ins in insurance_list]


@router.get(
    "/{company}",
    response_model=InsuranceCheckResponse,
    summary="Check Insurance Coverage",
    description="Check if an insurance company is covered and get coverage details.",
)
async def check_insurance_coverage(
    company: str,
    db: AsyncSession = Depends(get_db),
) -> InsuranceCheckResponse:
    """
    Check insurance coverage by company name.
    
    Supports fuzzy matching for Arabic and English names.
    Examples: تعاونية, التعاونية, Tawuniya, bupa, بوبا
    """
    logger.info(f"Checking coverage for: {company}")
    return await check_coverage(db, company)
