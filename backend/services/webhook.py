"""Webhook integration service for external notifications."""

import logging
import hashlib
import hmac
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid

import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models import WebhookConfiguration

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for sending webhook notifications to external systems."""

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def create_webhook(
        self,
        organization_id: uuid.UUID,
        name: str,
        url: str,
        event_types: List[str],
        secret: Optional[str] = None,
    ) -> WebhookConfiguration:
        """Create a new webhook configuration."""
        webhook = WebhookConfiguration(
            organization_id=organization_id,
            name=name,
            url=url,
            secret=secret,
            event_types=event_types,
            is_active=True,
        )
        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)
        logger.info(f"Created webhook: {webhook.id} - {name}")
        return webhook

    async def get_webhooks(
        self, organization_id: uuid.UUID, active_only: bool = False
    ) -> List[WebhookConfiguration]:
        """Get all webhooks for an organization."""
        filters = [WebhookConfiguration.organization_id == organization_id]
        if active_only:
            filters.append(WebhookConfiguration.is_active == True)

        query = select(WebhookConfiguration).filter(and_(*filters))
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_webhook(
        self,
        webhook_id: uuid.UUID,
        organization_id: uuid.UUID,
        name: Optional[str] = None,
        url: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
    ) -> WebhookConfiguration:
        """Update a webhook configuration."""
        query = select(WebhookConfiguration).filter(
            and_(
                WebhookConfiguration.id == webhook_id,
                WebhookConfiguration.organization_id == organization_id,
            )
        )
        result = await self.db.execute(query)
        webhook = result.scalars().first()

        if not webhook:
            raise ValueError(f"Webhook {webhook_id} not found")

        if name is not None:
            webhook.name = name
        if url is not None:
            webhook.url = url
        if event_types is not None:
            webhook.event_types = event_types
        if is_active is not None:
            webhook.is_active = is_active

        await self.db.commit()
        await self.db.refresh(webhook)
        return webhook

    async def delete_webhook(
        self, webhook_id: uuid.UUID, organization_id: uuid.UUID
    ) -> None:
        """Delete a webhook configuration."""
        query = select(WebhookConfiguration).filter(
            and_(
                WebhookConfiguration.id == webhook_id,
                WebhookConfiguration.organization_id == organization_id,
            )
        )
        result = await self.db.execute(query)
        webhook = result.scalars().first()

        if not webhook:
            raise ValueError(f"Webhook {webhook_id} not found")

        await self.db.delete(webhook)
        await self.db.commit()

    async def get_active_webhooks(
        self, organization_id: uuid.UUID, event_type: str
    ) -> List[WebhookConfiguration]:
        """Get active webhooks subscribed to a specific event type."""
        query = select(WebhookConfiguration).filter(
            and_(
                WebhookConfiguration.organization_id == organization_id,
                WebhookConfiguration.is_active == True,
            )
        )
        result = await self.db.execute(query)
        webhooks = result.scalars().all()

        return [w for w in webhooks if event_type in w.event_types]

async def send_alert(
        self,
        organization_id: uuid.UUID,
        alert_data: Dict[str, Any]
    ) -> bool:
        """Send alert to all configured webhooks for an organization."""
        return await self.send_alert_to_org(organization_id, alert_data)

    async def send_alert_to_org(
        self,
        organization_id: uuid.UUID,
        alert_data: Dict[str, Any]
    ) -> bool:
        """Send alert to all configured webhooks for an organization."""
        webhooks = await self.get_active_webhooks(organization_id, "alert")
        if not webhooks:
            return False
        
        payload = {
            "event": "alert",
            "organization_id": str(organization_id),
            "data": alert_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        success = False
        for webhook in webhooks:
            result = await self._send_webhook_payload(payload, webhook.url, webhook.secret)
            if result:
                success = True
            else:
                await self._record_failure(webhook)
        
        return success

    async def send_geofence_event(
        self,
        organization_id: uuid.UUID,
        event_data: Dict[str, Any]
    ) -> bool:
        """Send geofence event to all configured webhooks."""
        webhooks = await self.get_active_webhooks(organization_id, "geofence")
        if not webhooks:
            return False

        payload = {
            "event": "geofence",
            "organization_id": str(organization_id),
            "data": event_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        success = False
        for webhook in webhooks:
            result = await self._send_webhook_payload(payload, webhook.url, webhook.secret)
            if result:
                success = True
            else:
                await self._record_failure(webhook)

        return success

    async def send_maintenance_alert(
        self,
        organization_id: uuid.UUID,
        maintenance_data: Dict[str, Any]
    ) -> bool:
        """Send maintenance notification to all configured webhooks."""
        webhooks = await self.get_active_webhooks(organization_id, "maintenance")
        if not webhooks:
            return False

        payload = {
            "event": "maintenance",
            "organization_id": str(organization_id),
            "data": maintenance_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        success = False
        for webhook in webhooks:
            result = await self._send_webhook_payload(payload, webhook.url, webhook.secret)
            if result:
                success = True
            else:
                await self._record_failure(webhook)

        return success

    async def send_fuel_anomaly(
        self,
        organization_id: uuid.UUID,
        anomaly_data: Dict[str, Any]
    ) -> bool:
        """Send fuel anomaly to all configured webhooks."""
        webhooks = await self.get_active_webhooks(organization_id, "fuel_anomaly")
        if not webhooks:
            return False

        payload = {
            "event": "fuel_anomaly",
            "organization_id": str(organization_id),
            "data": anomaly_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        success = False
        for webhook in webhooks:
            result = await self._send_webhook_payload(payload, webhook.url, webhook.secret)
            if result:
                success = True
            else:
                await self._record_failure(webhook)

        return success

    async def _record_failure(self, webhook: WebhookConfiguration) -> None:
        """Record a webhook failure."""
        webhook.failure_count += 1
        webhook.last_failure_at = datetime.now(timezone.utc)
        
        if webhook.failure_count >= 5:
            webhook.is_active = False
            logger.warning(f"Webhook {webhook.id} disabled after 5 failures")
        
        await self.db.commit()

async def _send_webhook_payload(
        self,
        payload: Dict[str, Any],
        url: str,
        secret: Optional[str] = None
    ) -> bool:
        """Send webhook request."""
        if not url:
            return False

        import json
        body = json.dumps(payload, separators=(',', ':'))
        
        headers = {"Content-Type": "application/json"}
        
        if secret:
            signature = hmac.new(
                secret.encode(),
                body.encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = signature

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, content=body, headers=headers)
                response.raise_for_status()
                logger.info(f"Webhook sent successfully: {payload.get('event')}")
                return True
except httpx.TimeoutException:
            logger.warning(f"Webhook timeout: {url}")
            return False
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return False
