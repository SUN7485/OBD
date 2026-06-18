"""Fuel anomaly detection service."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.models import FuelAnomaly, Car, OBDData, OBDDataHourly, AlertType, AlertSeverity

logger = logging.getLogger(__name__)


class FuelAnomalyService:
    """Service for detecting fuel theft and anomalies."""

    # Thresholds for anomaly detection
    IDLE_FUEL_THRESHOLD_L_PER_HOUR = 0.5  # Engine on, no movement
    SPIKE_THRESHOLD = 2.5  # 2.5x expected consumption
    NEGATIVE_CONSUMPTION_TOLERANCE = -0.1  # Slight negative is OK (refill)

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_fuel_consumption(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID,
        days: int = 7
    ) -> Dict[str, Any]:
        """Analyze fuel consumption patterns and detect anomalies."""
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get hourly data
        query = select(OBDDataHourly).filter(
            and_(
                OBDDataHourly.car_id == car_id,
                OBDDataHourly.organization_id == organization_id,
                OBDDataHourly.time >= start_time
            )
        ).order_by(OBDDataHourly.time)
        
        result = await self.db.execute(query)
        hourly_data = result.scalars().all()
        
        if not hourly_data:
            return {"status": "no_data", "message": "No fuel data available"}
        
        # Calculate statistics
        total_distance = sum(float(h.total_distance_km or 0) for h in hourly_data)
        total_fuel = sum(float(h.total_fuel_consumed_l or 0) for h in hourly_data)
        
        # Calculate expected fuel (based on average consumption)
        avg_fuel_per_km = total_fuel / total_distance if total_distance > 0 else 0
        expected_fuel = avg_fuel_per_km * total_distance
        
        # Detect anomalies
        anomalies = []
        
        for hour in hourly_data:
            hour_distance = float(hour.total_distance_km or 0)
            hour_fuel = float(hour.total_fuel_consumed_l or 0)
            
            # Idle detection: moving < 1km but consumed fuel
            if hour_distance < 1 and hour_fuel > self.IDLE_FUEL_THRESHOLD_L_PER_HOUR:
                anomalies.append({
                    "type": "idle_fuel",
                    "time": hour.time.isoformat(),
                    "fuel_consumed_l": hour_fuel,
                    "distance_km": hour_distance,
                    "severity": "warning"
                })
            
            # Consumption spike: much higher than average
            if hour_distance > 0:
                fuel_per_km = hour_fuel / hour_distance
                if fuel_per_km > avg_fuel_per_km * self.SPIKE_THRESHOLD and hour_distance > 5:
                    anomalies.append({
                        "type": "consumption_spike",
                        "time": hour.time.isoformat(),
                        "fuel_consumed_l": hour_fuel,
                        "distance_km": hour_distance,
                        "expected_fuel": avg_fuel_per_km * hour_distance,
                        "severity": "warning"
                    })
        
        # Create fuel anomaly records
        created_anomalies = []
        for anomaly in anomalies:
            fuel_anomaly = FuelAnomaly(
                organization_id=organization_id,
                car_id=car_id,
                anomaly_type="unusual_consumption",
                severity=AlertSeverity.warning if anomaly["severity"] == "warning" else AlertSeverity.critical,
                expected_fuel_l=anomaly.get("expected_fuel"),
                actual_fuel_l=anomaly["fuel_consumed_l"],
                anomaly_value_l=anomaly["fuel_consumed_l"] - anomaly.get("expected_fuel", 0),
                description=f"{anomaly['type']}: {anomaly['fuel_consumed_l']}L consumed, {anomaly['distance_km']}km traveled"
            )
            self.db.add(fuel_anomaly)
            created_anomalies.append(fuel_anomaly)
        
        await self.db.commit()
        
        return {
            "total_distance_km": round(total_distance, 2),
            "total_fuel_l": round(total_fuel, 2),
            "avg_fuel_efficiency": round(avg_fuel_per_km * 100, 2),  # L/100km
            "anomalies_detected": len(created_anomalies),
            "anomalies": anomalies
        }

    async def check_idle_fuel_theft(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Check for idle fuel theft (engine on, no movement for extended periods)."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Get telemetry with location
        query = select(OBDData).filter(
            and_(
                OBDData.car_id == car_id,
                OBDData.time >= start_time,
                OBDData.speed == 0,
                OBDData.rpm > 0,  # Engine running
                OBDData.latitude.isnot(None),
                OBDData.longitude.isnot(None)
            )
        ).order_by(OBDData.time)
        
        result = await self.db.execute(query)
        idle_records = result.scalars().all()
        
        if not idle_records:
            return []
        
        # Group consecutive idle periods
        idle_periods = []
        current_period = None
        
        for record in idle_records:
            if current_period is None:
                current_period = {
                    "start": record.time,
                    "end": record.time,
                    "fuel_rate": record.fuel_rate or 0,
                    "location": {"lat": float(record.latitude), "lng": float(record.longitude)}
                }
            else:
                # Check if within 5 minutes
                if (record.time - current_period["end"]).total_seconds() < 300:
                    current_period["end"] = record.time
                    current_period["fuel_rate"] = max(current_period["fuel_rate"], record.fuel_rate or 0)
                else:
                    # Save current and start new
                    duration = (current_period["end"] - current_period["start"]).total_seconds() / 3600
                    current_period["duration_hours"] = duration
                    current_period["estimated_fuel_l"] = current_period["fuel_rate"] * duration
                    
                    if duration > 1:  # More than 1 hour
                        idle_periods.append(current_period)
                    
                    current_period = {
                        "start": record.time,
                        "end": record.time,
                        "fuel_rate": record.fuel_rate or 0,
                        "location": {"lat": float(record.latitude), "lng": float(record.longitude)}
                    }
        
        # Don't forget last period
        if current_period:
            duration = (current_period["end"] - current_period["start"]).total_seconds() / 3600
            current_period["duration_hours"] = duration
            current_period["estimated_fuel_l"] = current_period["fuel_rate"] * duration
            if duration > 1:
                idle_periods.append(current_period)
        
        # Create anomaly records for suspicious idle periods
        suspicious = []
        for period in idle_periods:
            if period["estimated_fuel_l"] > 2:  # More than 2L consumed while idle
                suspicious.append(period)
                
                # Check if already reported
                existing_query = select(FuelAnomaly).filter(
                    and_(
                        FuelAnomaly.car_id == car_id,
                        FuelAnomaly.anomaly_type == "fuel_theft",
                        FuelAnomaly.detected_at >= start_time
                    )
                )
                existing = await self.db.execute(existing_query)
                
                if not existing.scalars().first():
                    anomaly = FuelAnomaly(
                        organization_id=organization_id,
                        car_id=car_id,
                        anomaly_type="fuel_theft",
                        severity=AlertSeverity.critical if period["estimated_fuel_l"] > 5 else AlertSeverity.warning,
                        expected_fuel_l=0,
                        actual_fuel_l=period["estimated_fuel_l"],
                        description=f"Suspicious idle: {period['duration_hours']:.1f}h, {period['estimated_fuel_l']:.1f}L fuel consumed while stationary"
                    )
                    self.db.add(anomaly)
        
        await self.db.commit()
        
        return suspicious

    async def get_fuel_anomalies(
        self,
        organization_id: uuid.UUID,
        car_id: Optional[uuid.UUID] = None,
        anomaly_type: Optional[str] = None,
        is_confirmed: Optional[bool] = None,
        limit: int = 50
    ) -> List[FuelAnomaly]:
        """Get fuel anomalies with filters."""
        filters = [FuelAnomaly.organization_id == organization_id]
        
        if car_id:
            filters.append(FuelAnomaly.car_id == car_id)
        if anomaly_type:
            filters.append(FuelAnomaly.anomaly_type == anomaly_type)
        if is_confirmed is not None:
            filters.append(FuelAnomaly.is_confirmed == is_confirmed)
        
        query = (
            select(FuelAnomaly)
            .filter(and_(*filters))
            .order_by(FuelAnomaly.detected_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def mark_anomaly_investigated(
        self,
        anomaly_id: uuid.UUID,
        organization_id: uuid.UUID,
        is_confirmed: bool = False,
        notes: Optional[str] = None
    ) -> FuelAnomaly:
        """Mark an anomaly as investigated."""
        result = await self.db.execute(
            select(FuelAnomaly).filter(
                and_(
                    FuelAnomaly.id == anomaly_id,
                    FuelAnomaly.organization_id == organization_id
                )
            )
        )
        anomaly = result.scalars().first()
        
        if not anomaly:
            raise ValueError(f"Anomaly {anomaly_id} not found")
        
        anomaly.is_investigated = True
        anomaly.is_confirmed = is_confirmed
        if notes:
            anomaly.notes = notes
        
        await self.db.commit()
        await self.db.refresh(anomaly)
        
        return anomaly
