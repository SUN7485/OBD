"""API routes for fleet and car analytics."""
import logging
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.middleware.auth import get_current_user
from backend.domain.models import User, UserRole
from backend.services.analytics import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/fleet/summary",
    summary="Get fleet summary",
    description="Get organization-wide fleet analytics summary."
)
async def get_fleet_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get fleet-wide analytics summary.
    
    Requires admin or fleet_manager role.
    Returns aggregated metrics for the entire organization.
    """
    if current_user.role not in [UserRole.admin, UserRole.fleet_manager]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin or fleet_manager role"
        )

    service = AnalyticsService(db)

    try:
        result = await service.get_fleet_summary(current_user.organization_id)
    except Exception as e:
        logger.error(f"Error getting fleet summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve fleet summary"
        )

    return result


@router.get(
    "/car/{car_id}/summary",
    summary="Get car analytics summary",
    description="Get individual car analytics including recent metrics and averages."
)
async def get_car_summary(
    car_id: uuid.UUID,
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get individual car analytics.
    
    - Verify user has access to car
    - Return car-specific metrics including:
      - Recent telemetry (last reading)
      - Averages over the period
      - Maximum values
      - DTC history
    """
    service = AnalyticsService(db)

    try:
        result = await service.get_car_summary(
            car_id=car_id,
            organization_id=current_user.organization_id,
            hours=hours
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting car summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve car summary"
        )

    return result


@router.get(
    "/car/{car_id}/statistics",
    summary="Get car driving statistics",
    description="Get driving statistics over multiple days."
)
async def get_car_statistics(
    car_id: uuid.UUID,
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get driving statistics for a car.
    
    Returns daily aggregated statistics including:
    - Distance traveled
    - Fuel consumed
    - Average and max speed
    - Fuel efficiency
    """
    service = AnalyticsService(db)

    try:
        result = await service.get_driving_statistics(
            car_id=car_id,
            organization_id=current_user.organization_id,
            days=days
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting car statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve car statistics"
        )

    return result
