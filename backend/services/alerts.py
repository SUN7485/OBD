"""Alert service for managing vehicle alerts."""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models import Alert, AlertType, AlertSeverity, Car

logger = logging.getLogger(__name__)


class AlertService:
    """Service for alert management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_alert(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """
        Create a new alert.
        
        Args:
            car_id: The car ID
            organization_id: The organization ID
            alert_type: Type of alert
            severity: Severity level
            title: Alert title
            message: Optional detailed message
            metadata: Optional additional metadata
            
        Returns:
            The created alert
        """
        alert = Alert(
            organization_id=organization_id,
            car_id=car_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            alert_metadata=metadata or {}
        )

        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(
            f"Created alert: {alert.id} - {title} (severity: {severity.value})"
        )

        return alert

    async def get_alerts(
        self,
        organization_id: uuid.UUID,
        car_id: Optional[uuid.UUID] = None,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
        is_read: Optional[bool] = None,
        is_resolved: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Alert], int]:
        """
        Get alerts with filters.
        
        Args:
            organization_id: The organization ID
            car_id: Optional car filter
            severity: Optional severity filter
            alert_type: Optional type filter
            is_read: Optional read status filter
            is_resolved: Optional resolved status filter
            limit: Maximum results
            offset: Result offset
            
        Returns:
            Tuple of (alerts list, total count)
        """
        # Build filters
        filters = [Alert.organization_id == organization_id]

        if car_id:
            filters.append(Alert.car_id == car_id)
        if severity:
            filters.append(Alert.severity == severity)
        if alert_type:
            filters.append(Alert.alert_type == alert_type)
        if is_read is not None:
            filters.append(Alert.is_read == is_read)
        if is_resolved is not None:
            filters.append(Alert.is_resolved == is_resolved)

        # Get total count
        count_query = select(func.count(Alert.id)).filter(and_(*filters))
        total = await self.db.scalar(count_query) or 0

        # Get alerts
        query = (
            select(Alert)
            .filter(and_(*filters))
            .order_by(Alert.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        alerts = result.scalars().all()

        return alerts, total

    async def get_unread_count(
        self,
        organization_id: uuid.UUID,
        car_id: Optional[uuid.UUID] = None
    ) -> Dict[str, int]:
        """Get count of unread alerts by severity."""
        filters = [
            Alert.organization_id == organization_id,
            Alert.is_read == False,
            Alert.is_resolved == False
        ]
        
        if car_id:
            filters.append(Alert.car_id == car_id)

        counts = {}
        for severity in AlertSeverity:
            query = select(func.count(Alert.id)).filter(
                and_(*filters, Alert.severity == severity)
            )
            counts[severity.value] = await self.db.scalar(query) or 0

        return counts

    async def mark_as_read(
        self,
        alert_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Alert:
        """Mark an alert as read."""
        alert = await self._get_alert_by_id(alert_id, organization_id)
        
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.is_read = True
        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(f"Marked alert {alert_id} as read")

        return alert

    async def resolve_alert(
        self,
        alert_id: uuid.UUID,
        organization_id: uuid.UUID,
        resolved_by: uuid.UUID
    ) -> Alert:
        """Resolve an alert."""
        alert = await self._get_alert_by_id(alert_id, organization_id)
        
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.is_resolved = True
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by = resolved_by
        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(f"Resolved alert {alert_id}")

        return alert

    async def bulk_mark_read(
        self,
        alert_ids: List[uuid.UUID],
        organization_id: uuid.UUID
    ) -> int:
        """Mark multiple alerts as read."""
        result = await self.db.execute(
            select(Alert).filter(
                and_(
                    Alert.id.in_(alert_ids),
                    Alert.organization_id == organization_id,
                    Alert.is_read == False
                )
            )
        )
        alerts = result.scalars().all()

        for alert in alerts:
            alert.is_read = True

        await self.db.commit()

        logger.info(f"Marked {len(alerts)} alerts as read")

        return len(alerts)

    async def get_car_alerts(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID,
        limit: int = 20
    ) -> List[Alert]:
        """Get recent alerts for a specific car."""
        query = (
            select(Alert)
            .filter(
                and_(
                    Alert.car_id == car_id,
                    Alert.organization_id == organization_id
                )
            )
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _get_alert_by_id(
        self,
        alert_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Optional[Alert]:
        """Get alert by ID with organization check."""
        result = await self.db.execute(
            select(Alert).filter(
                and_(
                    Alert.id == alert_id,
                    Alert.organization_id == organization_id
                )
            )
        )
        return result.scalars().first()
