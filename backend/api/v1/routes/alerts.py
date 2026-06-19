"""API routes for alert management."""
import logging
from typing import Optional, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.session import get_db
from middleware.auth import get_current_user
from domain.models import User, AlertType, AlertSeverity
from services.alerts import AlertService
from services.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertResponse(BaseModel):
    """Alert response schema."""
    id: str
    car_id: str
    alert_type: str
    severity: str
    title: str
    message: Optional[str]
    is_read: bool
    is_resolved: bool
    resolved_at: Optional[str]
    resolved_by: Optional[str]
    created_at: str
    metadata: dict

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Alert list response."""
    alerts: List[AlertResponse]
    total: int
    limit: int
    offset: int


class UnreadCountResponse(BaseModel):
    """Unread alert count response."""
    info: int
    warning: int
    critical: int


@router.get(
    "",
    response_model=AlertListResponse,
    summary="List alerts",
    description="Get alerts with filtering and pagination."
)
async def list_alerts(
    car_id: Optional[uuid.UUID] = Query(None, description="Filter by car ID"),
    severity: Optional[str] = Query(None, description="Filter by severity (info, warning, critical)"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    is_resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List alerts with filters.
    
    - Supports query params: car_id, severity, alert_type, is_read, is_resolved, limit, offset
    - Filters by organization_id for multi-tenant isolation
    - Returns paginated results
    """
    # Parse severity
    severity_enum = None
    if severity:
        try:
            severity_enum = AlertSeverity(severity)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity: {severity}"
            )

    # Parse alert type
    alert_type_enum = None
    if alert_type:
        try:
            alert_type_enum = AlertType(alert_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid alert type: {alert_type}"
            )

    service = AlertService(db)

    try:
        alerts, total = await service.get_alerts(
            organization_id=current_user.organization_id,
            car_id=car_id,
            severity=severity_enum,
            alert_type=alert_type_enum,
            is_read=is_read,
            is_resolved=is_resolved,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alerts"
        )

    alert_responses = [
        AlertResponse(
            id=str(a.id),
            car_id=str(a.car_id),
            alert_type=a.alert_type.value,
            severity=a.severity.value,
            title=a.title,
            message=a.message,
            is_read=a.is_read,
            is_resolved=a.is_resolved,
            resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
            resolved_by=str(a.resolved_by) if a.resolved_by else None,
            created_at=a.created_at.isoformat(),
            metadata=a.alert_metadata
        )
        for a in alerts
    ]

    return AlertListResponse(
        alerts=alert_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread alert count",
    description="Get count of unread alerts by severity."
)
async def get_unread_count(
    car_id: Optional[uuid.UUID] = Query(None, description="Filter by car ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get count of unread alerts by severity."""
    service = AlertService(db)

    try:
        counts = await service.get_unread_count(
            organization_id=current_user.organization_id,
            car_id=car_id
        )
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve unread count"
        )

    return UnreadCountResponse(**counts)


@router.post(
    "/{alert_id}/read",
    response_model=AlertResponse,
    summary="Mark alert as read",
    description="Mark an alert as read."
)
async def mark_alert_read(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark an alert as read."""
    service = AlertService(db)

    try:
        alert = await service.mark_as_read(alert_id, current_user.organization_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error marking alert as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark alert as read"
        )

    return AlertResponse(
        id=str(alert.id),
        car_id=str(alert.car_id),
        alert_type=alert.alert_type.value,
        severity=alert.severity.value,
        title=alert.title,
        message=alert.message,
        is_read=alert.is_read,
        is_resolved=alert.is_resolved,
        resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
        resolved_by=str(alert.resolved_by) if alert.resolved_by else None,
        created_at=alert.created_at.isoformat(),
        metadata=alert.alert_metadata
    )


@router.post(
    "/{alert_id}/resolve",
    response_model=AlertResponse,
    summary="Resolve alert",
    description="Resolve an alert."
)
async def resolve_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Resolve an alert."""
    service = AlertService(db)

    try:
        alert = await service.resolve_alert(
            alert_id,
            current_user.organization_id,
            current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve alert"
        )

    # Broadcast resolution to WebSocket
    try:
        await manager.broadcast_to_car(
            alert.car_id,
            {
                "type": "alert_resolved",
                "data": {
                    "alert_id": str(alert.id),
                    "title": alert.title,
                    "resolved_by": current_user.full_name
                }
            }
        )
    except Exception as e:
        logger.error(f"WebSocket broadcast error: {e}")

    return AlertResponse(
        id=str(alert.id),
        car_id=str(alert.car_id),
        alert_type=alert.alert_type.value,
        severity=alert.severity.value,
        title=alert.title,
        message=alert.message,
        is_read=alert.is_read,
        is_resolved=alert.is_resolved,
        resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
        resolved_by=str(alert.resolved_by) if alert.resolved_by else None,
        created_at=alert.created_at.isoformat(),
        metadata=alert.alert_metadata
    )


@router.post(
    "/bulk-read",
    summary="Bulk mark as read",
    description="Mark multiple alerts as read."
)
async def bulk_mark_read(
    alert_ids: List[uuid.UUID],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark multiple alerts as read."""
    if len(alert_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 alerts can be marked as read at once"
        )

    service = AlertService(db)

    try:
        count = await service.bulk_mark_read(alert_ids, current_user.organization_id)
    except Exception as e:
        logger.error(f"Error bulk marking alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark alerts as read"
        )

    return {"success": True, "marked_count": count}


@router.get(
    "/car/{car_id}",
    summary="Get car alerts",
    description="Get recent alerts for a specific car."
)
async def get_car_alerts(
    car_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recent alerts for a car."""
    service = AlertService(db)

    try:
        alerts = await service.get_car_alerts(
            car_id,
            current_user.organization_id,
            limit
        )
    except Exception as e:
        logger.error(f"Error getting car alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alerts"
        )

    return {
        "alerts": [
            {
                "id": str(a.id),
                "alert_type": a.alert_type.value,
                "severity": a.severity.value,
                "title": a.title,
                "message": a.message,
                "is_read": a.is_read,
                "is_resolved": a.is_resolved,
                "created_at": a.created_at.isoformat()
            }
            for a in alerts
        ]
    }
