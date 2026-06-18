"""Trip detection and analysis service."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.models import Car, OBDData

logger = logging.getLogger(__name__)


class TripDetectionService:
    """Service for detecting and analyzing vehicle trips."""

    # Configuration
    IDLE_THRESHOLD_MINUTES = 5  # Minutes of no movement to end a trip
    MIN_TRIP_DISTANCE_KM = 0.5  # Minimum distance to count as a trip
    MIN_TRIP_DURATION_MINUTES = 2  # Minimum trip duration

    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_trips(
        self,
        car_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Detect trips from telemetry data.
        
        A trip is defined as a period of movement followed by idle.
        """
        # Get all telemetry with location
        query = select(OBDData).filter(
            and_(
                OBDData.car_id == car_id,
                OBDData.time >= start_time,
                OBDData.time <= end_time,
                OBDData.latitude.isnot(None),
                OBDData.longitude.isnot(None)
            )
        ).order_by(OBDData.time)

        result = await self.db.execute(query)
        records = result.scalars().all()

        if not records:
            return []

        trips = []
        current_trip = None
        idle_start = None
        
        prev_record = None

        for record in records:
            is_moving = record.speed is not None and record.speed > 0
            
            if is_moving:
                # Start a new trip if not already in one
                if current_trip is None:
                    current_trip = {
                        "start_time": record.time,
                        "end_time": record.time,
                        "start_location": {
                            "latitude": float(record.latitude),
                            "longitude": float(record.longitude)
                        },
                        "locations": [],
                        "max_speed": record.speed or 0,
                        "total_distance_km": 0,
                        "fuel_consumed_l": 0,
                        "idle_time_minutes": 0
                    }
                
                # Update trip data
                current_trip["end_time"] = record.time
                current_trip["end_location"] = {
                    "latitude": float(record.latitude),
                    "longitude": float(record.longitude)
                }
                
                if record.speed and record.speed > current_trip["max_speed"]:
                    current_trip["max_speed"] = record.speed
                
                # Add location point
                current_trip["locations"].append({
                    "time": record.time.isoformat(),
                    "latitude": float(record.latitude),
                    "longitude": float(record.longitude),
                    "speed": record.speed
                })
                
                # Calculate distance from previous point
                if prev_record:
                    distance = self._haversine_distance(
                        float(prev_record.latitude), float(prev_record.longitude),
                        float(record.latitude), float(record.longitude)
                    )
                    current_trip["total_distance_km"] += distance / 1000  # Convert to km
                
                # Reset idle counter
                idle_start = None
                
            else:
                # Not moving
                if current_trip is not None:
                    # Check if we've been idle long enough to end trip
                    if idle_start is None:
                        idle_start = record.time
                    else:
                        idle_duration = (record.time - idle_start).total_seconds() / 60
                        
                        if idle_duration >= self.IDLE_THRESHOLD_MINUTES:
                            # End the trip
                            if self._is_valid_trip(current_trip):
                                trips.append(current_trip)
                            current_trip = None
                            idle_start = None
            
            prev_record = record

        # Don't forget the last trip if still active
        if current_trip and self._is_valid_trip(current_trip):
            trips.append(current_trip)

        return trips

    async def get_trip_summary(
        self,
        car_id: uuid.UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get trip summary statistics."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)

        trips = await self.detect_trips(car_id, start_time, end_time)

        if not trips:
            return {
                "total_trips": 0,
                "total_distance_km": 0,
                "total_duration_hours": 0,
                "avg_trip_distance_km": 0,
                "avg_trip_duration_minutes": 0,
                "avg_speed_kmh": 0,
                "max_speed_kmh": 0
            }

        total_distance = sum(t["total_distance_km"] for t in trips)
        total_duration = sum(
            (t["end_time"] - t["start_time"]).total_seconds() / 3600
            for t in trips
        )
        max_speed = max(t["max_speed"] for t in trips)
        
        # Calculate average speed (excluding stops)
        moving_time = sum(
            t["total_distance_km"] / (t["max_speed"] or 1) * 60  # Convert to minutes
            for t in trips if t["max_speed"] > 0
        )

        return {
            "total_trips": len(trips),
            "total_distance_km": round(total_distance, 2),
            "total_duration_hours": round(total_duration, 2),
            "avg_trip_distance_km": round(total_distance / len(trips), 2),
            "avg_trip_duration_minutes": round((total_duration * 60) / len(trips), 1),
            "avg_speed_kmh": round(total_distance / total_duration, 1) if total_duration > 0 else 0,
            "max_speed_kmh": max_speed
        }

    def _is_valid_trip(self, trip: Dict[str, Any]) -> bool:
        """Check if trip meets minimum criteria."""
        if trip["total_distance_km"] < self.MIN_TRIP_DISTANCE_KM:
            return False
        
        duration_minutes = (trip["end_time"] - trip["start_time"]).total_seconds() / 60
        if duration_minutes < self.MIN_TRIP_DURATION_MINUTES:
            return False
        
        return True

    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in meters."""
        import math
        
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
