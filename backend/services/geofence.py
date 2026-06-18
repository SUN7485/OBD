"""Geofencing service for location-based monitoring."""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
import uuid
import math

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.models import Geofence, GeofenceEvent, Car, AlertType, AlertSeverity

logger = logging.getLogger(__name__)


class GeofenceService:
    """Service for geofence management and monitoring."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_geofence(
        self,
        organization_id: uuid.UUID,
        name: str,
        geofence_type: str,
        geometry: dict,
        description: Optional[str] = None,
        notify_on_entry: bool = True,
        notify_on_exit: bool = True
    ) -> Geofence:
        """Create a new geofence."""
        from backend.domain.models import GeofenceType
        
        geofence = Geofence(
            organization_id=organization_id,
            name=name,
            geofence_type=GeofenceType(geofence_type),
            geometry=geometry,
            description=description,
            notify_on_entry=notify_on_entry,
            notify_on_exit=notify_on_exit
        )
        
        self.db.add(geofence)
        await self.db.commit()
        await self.db.refresh(geofence)
        
        logger.info(f"Created geofence: {geofence.id} - {name}")
        return geofence

    async def get_geofences(
        self,
        organization_id: uuid.UUID,
        geofence_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Geofence]:
        """Get all geofences for an organization."""
        filters = [Geofence.organization_id == organization_id]
        
        if geofence_type:
            filters.append(Geofence.geofence_type == geofence_type)
        if is_active is not None:
            filters.append(Geofence.is_active == is_active)
        
        query = select(Geofence).filter(and_(*filters)).order_by(Geofence.name)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def check_point_in_geofence(
        self,
        latitude: float,
        longitude: float,
        geofence: Geofence
    ) -> bool:
        """Check if a point is inside a geofence."""
        geometry = geofence.geometry
        
        if geometry.get("type") == "Point":
            # Point + radius
            center_lat = geometry["coordinates"][1]
            center_lng = geometry["coordinates"][0]
            radius_m = geometry.get("radius", 100)  # meters
            
            distance = self._haversine_distance(
                latitude, longitude, center_lat, center_lng
            )
            return distance <= radius_m
        
        elif geometry.get("type") == "Polygon":
            # Point in polygon using ray casting
            coords = geometry["coordinates"][0]  # Outer ring
            return self._point_in_polygon(latitude, longitude, coords)
        
        return False

    async def check_location(
        self,
        car_id: uuid.UUID,
        latitude: float,
        longitude: float,
        organization_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        Check a location against all geofences.
        
        Returns list of triggered events.
        """
        # Get all active geofences
        geofences = await self.get_geofences(organization_id, is_active=True)
        
        triggered = []
        
        for geofence in geofences:
            is_inside = await self.check_point_in_geofence(latitude, longitude, geofence)
            
            # Check if this is a new event
            if is_inside:
                # Check last event for this car/geofence
                last_event = await self._get_last_event(car_id, geofence.id)
                
                if not last_event:
                    # New enter event
                    event = await self._create_event(
                        geofence, car_id, "enter", latitude, longitude
                    )
                    triggered.append({
                        "type": "enter",
                        "geofence": {
                            "id": str(geofence.id),
                            "name": geofence.name,
                            "geofence_type": geofence.geofence_type.value
                        },
                        "notify": geofence.notify_on_entry
                    })
                elif last_event.event_type == "exit":
                    # Re-entered
                    event = await self._create_event(
                        geofence, car_id, "enter", latitude, longitude
                    )
                    triggered.append({
                        "type": "enter",
                        "geofence": {
                            "id": str(geofence.id),
                            "name": geofence.name
                        },
                        "notify": geofence.notify_on_entry
                    })
            else:
                # Check if we exited
                last_event = await self._get_last_event(car_id, geofence.id)
                
                if last_event and last_event.event_type == "enter":
                    # Exited
                    event = await self._create_event(
                        geofence, car_id, "exit", latitude, longitude
                    )
                    triggered.append({
                        "type": "exit",
                        "geofence": {
                            "id": str(geofence.id),
                            "name": geofence.name
                        },
                        "notify": geofence.notify_on_exit
                    })
        
        return triggered

    async def get_geofence_events(
        self,
        organization_id: uuid.UUID,
        car_id: Optional[uuid.UUID] = None,
        geofence_id: Optional[uuid.UUID] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[GeofenceEvent]:
        """Get geofence events."""
        filters = [GeofenceEvent.organization_id == organization_id]
        
        if car_id:
            filters.append(GeofenceEvent.car_id == car_id)
        if geofence_id:
            filters.append(GeofenceEvent.geofence_id == geofence_id)
        if event_type:
            filters.append(GeofenceEvent.event_type == event_type)
        
        query = (
            select(GeofenceEvent)
            .filter(and_(*filters))
            .order_by(GeofenceEvent.event_time.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_vehicle_location_history(
        self,
        car_id: uuid.UUID,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get vehicle location history from telemetry."""
        from backend.domain.models import OBDData
        from datetime import timedelta
        
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        query = (
            select(OBDData)
            .filter(
                and_(
                    OBDData.car_id == car_id,
                    OBDData.time >= start_time,
                    OBDData.latitude.isnot(None),
                    OBDData.longitude.isnot(None)
                )
            )
            .order_by(OBDData.time)
        )
        
        result = await self.db.execute(query)
        records = result.scalars().all()
        
        return [
            {
                "time": r.time.isoformat(),
                "latitude": float(r.latitude),
                "longitude": float(r.longitude),
                "speed": r.speed
            }
            for r in records
        ]

    async def _get_last_event(
        self,
        car_id: uuid.UUID,
        geofence_id: uuid.UUID
    ) -> Optional[GeofenceEvent]:
        """Get the last event for a car/geofence."""
        query = (
            select(GeofenceEvent)
            .filter(
                and_(
                    GeofenceEvent.car_id == car_id,
                    GeofenceEvent.geofence_id == geofence_id
                )
            )
            .order_by(GeofenceEvent.event_time.desc())
            .limit(1)
        )
        
        result = await self.db.execute(query)
        return result.scalars().first()

    async def _create_event(
        self,
        geofence: Geofence,
        car_id: uuid.UUID,
        event_type: str,
        latitude: float,
        longitude: float
    ) -> GeofenceEvent:
        """Create a geofence event."""
        event = GeofenceEvent(
            organization_id=geofence.organization_id,
            geofence_id=geofence.id,
            car_id=car_id,
            event_type=event_type,
            location={"latitude": latitude, "longitude": longitude}
        )
        
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        
        return event

    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in meters."""
        R = 6371000  # Earth radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c

    def _point_in_polygon(
        self,
        lat: float, lon: float,
        polygon: List[List[float]]
    ) -> bool:
        """Check if point is inside polygon using ray casting."""
        n = len(polygon)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            
            if ((yi > lat) != (yj > lat)) and \
               (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            
            j = i
        
        return inside
