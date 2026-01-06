"""
Nexus Miracle - Insurance CRUD Operations

Database operations for insurance coverage lookups.
"""

from loguru import logger
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Insurance
from app.schemas.insurance import InsuranceCheckResponse


async def get_all_insurance(
    session: AsyncSession,
    *,
    covered_only: bool = False,
) -> list[Insurance]:
    """
    Get all insurance companies.
    
    Args:
        session: Database session
        covered_only: Only return covered insurance
    
    Returns:
        List of insurance records
    """
    query = select(Insurance)
    
    if covered_only:
        query = query.where(Insurance.is_covered == True)
    
    query = query.order_by(Insurance.company_name_ar)
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_insurance_by_name(
    session: AsyncSession,
    name: str,
) -> Insurance | None:
    """
    Get insurance by name with fuzzy matching.
    
    Searches company_name, company_name_ar, and name_variations.
    
    Args:
        session: Database session
        name: Insurance name to search for
    
    Returns:
        Insurance if found, None otherwise
    """
    # Normalize search term
    name = name.strip().lower()
    
    # First try exact match on primary names
    query = select(Insurance).where(
        or_(
            Insurance.company_name.ilike(name),
            Insurance.company_name_ar.ilike(name),
        )
    )
    result = await session.execute(query)
    insurance = result.scalar_one_or_none()
    
    if insurance:
        return insurance
    
    # Try partial match
    query = select(Insurance).where(
        or_(
            Insurance.company_name.ilike(f"%{name}%"),
            Insurance.company_name_ar.ilike(f"%{name}%"),
        )
    )
    result = await session.execute(query)
    insurance = result.scalar_one_or_none()
    
    if insurance:
        return insurance
    
    # Search in name_variations (JSON array)
    # Note: SQLite JSON support is limited, so we fetch all and search in Python
    all_insurance = await get_all_insurance(session)
    
    for ins in all_insurance:
        if ins.name_variations:
            for variation in ins.name_variations:
                if name in variation.lower() or variation.lower() in name:
                    logger.debug(f"Found insurance via variation: {variation}")
                    return ins
    
    logger.debug(f"No insurance found for: {name}")
    return None


async def check_coverage(
    session: AsyncSession,
    company_name: str,
) -> InsuranceCheckResponse:
    """
    Check insurance coverage for a company.
    
    Args:
        session: Database session
        company_name: Insurance company name to check
    
    Returns:
        InsuranceCheckResponse with coverage details
    """
    insurance = await get_insurance_by_name(session, company_name)
    
    if not insurance:
        return InsuranceCheckResponse(
            found=False,
            query=company_name,
            coverage=None,
            message=f"Insurance company '{company_name}' not found in our system.",
            message_ar=f"لم نجد شركة التأمين '{company_name}' في نظامنا.",
        )
    
    if not insurance.is_covered:
        return InsuranceCheckResponse(
            found=True,
            query=company_name,
            coverage=insurance,
            message=f"{insurance.company_name} is not covered. You can pay as self-pay.",
            message_ar=f"شركة {insurance.company_name_ar} غير متعاقدة معنا. يمكنك الدفع نقداً.",
        )
    
    return InsuranceCheckResponse(
        found=True,
        query=company_name,
        coverage=insurance,
        message=(
            f"{insurance.company_name} is covered! "
            f"Coverage: {insurance.coverage_percent}%, "
            f"Copay: {insurance.copay_sar} SAR."
        ),
        message_ar=(
            f"شركة {insurance.company_name_ar} متعاقدة معنا! "
            f"نسبة التغطية: {insurance.coverage_percent}%، "
            f"المبلغ المتبقي عليك: {insurance.copay_sar} ريال."
        ),
    )
