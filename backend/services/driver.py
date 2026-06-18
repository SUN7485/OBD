"""Driver scoring and maintenance prediction service."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.models import (
    DriverScore, User, Car, OBDData, OBDDataHourly,
    MaintenanceSchedule, MaintenancePrediction, MaintenanceType, MaintenanceStatus
)

logger = logging.getLogger(__name__)


class DriverScoreService:
    """Service for calculating driver behavior scores."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_daily_scores(
        self,
        organization_id: uuid.UUID,
        date: Optional[datetime] = None
    ) -> List[DriverScore]:
        """Calculate daily driver scores for all drivers."""
        if date is None:
            date = datetime.now(timezone.utc).date()
        
        start_of_day = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_of_day = datetime.combine(date, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        # Get all drivers in organization
        drivers_result = await self.db.execute(
            select(User).filter(
                User.organization_id == organization_id,
                User.role == "driver",
                User.is_active == True
            )
        )
        drivers = drivers_result.scalars().all()
        
        scores = []
        for driver in drivers:
            score = await self._calculate_driver_score(
                driver.id,
                organization_id,
                start_of_day,
                end_of_day
            )
            if score:
                scores.append(score)
        
        return scores

    async def _calculate_driver_score(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime
    ) -> Optional[DriverScore]:
        """Calculate score for a single driver."""
        # Get cars assigned to this driver
        cars_result = await self.db.execute(
            select(Car).filter(
                Car.assigned_driver_id == user_id,
                Car.organization_id == organization_id,
                Car.is_active == True
            )
        )
        cars = cars_result.scalars().all()
        
        if not cars:
            return None
        
        car_ids = [car.id for car in cars]
        
        # Get aggregated data for these cars
        query = select(
            func.count(func.distinct(OBDDataHourly.car_id)).label('active_days'),
            func.sum(OBDDataHourly.total_distance_km).label('total_distance'),
            func.sum(OBDDataHourly.total_fuel_consumed_l).label('total_fuel'),
            func.avg(OBDDataHourly.avg_speed).label('avg_speed'),
            func.max(OBDDataHourly.max_speed).label('max_speed')
        ).filter(
            and_(
                OBDDataHourly.car_id.in_(car_ids),
                OBDDataHourly.time >= period_start,
                OBDDataHourly.time <= period_end
            )
        )
        
        result = await self.db.execute(query)
        data = result.fetchone()
        
        if not data or not data.total_distance:
            return None
        
        # Calculate metrics
        total_distance = float(data.total_distance or 0)
        total_fuel = float(data.total_fuel or 0)
        avg_speed = float(data.avg_speed or 0)
        max_speed = float(data.max_speed or 0)
        
        # Get raw data for harsh events (speed changes > threshold)
        harsh_events_query = select(OBDData).filter(
            and_(
                OBDData.car_id.in_(car_ids),
                OBDData.time >= period_start,
                OBDData.time <= period_end,
                OBDData.speed.isnot(None)
            )
        ).order_by(OBDData.car_id, OBDData.time)
        
        harsh_events_result = await self.db.execute(harsh_events_query)
        raw_data = harsh_events_result.scalars().all()
        
        # Calculate harsh events (simplified - check speed deltas)
        harsh_braking = 0
        harsh_acceleration = 0
        speeding_violations = 0
        
        prev_speed = None
        for record in raw_data:
            if record.speed is not None:
                if prev_speed is not None:
                    delta = record.speed - prev_speed
                    if delta < -30:  # Sudden braking
                        harsh_braking += 1
                    elif delta > 25:  # Harsh acceleration
                        harsh_acceleration += 1
                if record.speed > 150:  # Speeding
                    speeding_violations += 1
                prev_speed = record.speed
        
        # Calculate scores
        # Safety score: based on harsh events and speeding
        base_safety = 100
        safety_deductions = (harsh_braking * 3) + (harsh_acceleration * 2) + (speeding_violations * 5)
        safety_score = max(0, base_safety - safety_deductions)
        
        # Efficiency score: based on fuel consumption vs distance
        fuel_efficiency = (total_fuel / total_distance * 100) if total_distance > 0 else 0
        # Lower is better, scale: < 8L/100km = 100, > 15L/100km = 0
        efficiency_score = max(0, min(100, 100 - ((fuel_efficiency - 8) * 10)))
        
        # Overall score
        overall_score = (safety_score * 0.6) + (efficiency_score * 0.4)
        
        # Check if score exists
        existing_query = select(DriverScore).filter(
            and_(
                DriverScore.user_id == user_id,
                DriverScore.period_start == period_start
            )
        )
        existing = await self.db.execute(existing_query)
        existing_score = existing.scalars().first()
        
        if existing_score:
            # Update existing
            existing_score.overall_score = overall_score
            existing_score.safety_score = safety_score
            existing_score.efficiency_score = efficiency_score
            existing_score.total_distance_km = total_distance
            existing_score.harsh_braking_count = harsh_braking
            existing_score.harsh_acceleration_count = harsh_acceleration
            existing_score.speeding_violations = speeding_violations
            existing_score.fuel_consumed_l = total_fuel
            await self.db.commit()
            return existing_score
        else:
            # Create new
            score = DriverScore(
                user_id=user_id,
                organization_id=organization_id,
                period_start=period_start,
                period_end=period_end,
                overall_score=overall_score,
                safety_score=safety_score,
                efficiency_score=efficiency_score,
                total_distance_km=total_distance,
                harsh_braking_count=harsh_braking,
                harsh_acceleration_count=harsh_acceleration,
                speeding_violations=speeding_violations,
                fuel_consumed_l=total_fuel,
                total_trips=len(raw_data)
            )
            self.db.add(score)
            await self.db.commit()
            await self.db.refresh(score)
            return score

    async def get_driver_leaderboard(
        self,
        organization_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get driver leaderboard sorted by overall score."""
        query = (
            select(DriverScore, User)
            .join(User, DriverScore.user_id == User.id)
            .filter(
                and_(
                    DriverScore.organization_id == organization_id,
                    DriverScore.period_start >= period_start,
                    DriverScore.period_end <= period_end
                )
            )
            .order_by(DriverScore.overall_score.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        rows = result.fetchall()
        
        leaderboard = []
        for score, user in rows:
            leaderboard.append({
                "rank": len(leaderboard) + 1,
                "driver": {
                    "id": str(user.id),
                    "name": user.full_name
                },
                "overall_score": round(score.overall_score, 1),
                "safety_score": round(score.safety_score, 1),
                "efficiency_score": round(score.efficiency_score, 1),
                "total_distance_km": round(float(score.total_distance_km or 0), 1)
            })
        
        return leaderboard


class MaintenanceService:
    """Service for maintenance scheduling and prediction."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_maintenance_schedule(
        self,
        organization_id: uuid.UUID,
        car_id: uuid.UUID,
        maintenance_type: str,
        scheduled_date: datetime,
        description: Optional[str] = None,
        estimated_cost: Optional[float] = None
    ) -> MaintenanceSchedule:
        """Create a maintenance schedule."""
        schedule = MaintenanceSchedule(
            organization_id=organization_id,
            car_id=car_id,
            maintenance_type=MaintenanceType(maintenance_type),
            scheduled_date=scheduled_date,
            description=description,
            estimated_cost=estimated_cost,
            status=MaintenanceStatus.scheduled
        )
        
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        
        return schedule

    async def get_upcoming_maintenance(
        self,
        organization_id: uuid.UUID,
        days_ahead: int = 30
    ) -> List[MaintenanceSchedule]:
        """Get upcoming maintenance in the next N days."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days_ahead)
        
        query = (
            select(MaintenanceSchedule, Car)
            .join(Car, MaintenanceSchedule.car_id == Car.id)
            .filter(
                and_(
                    MaintenanceSchedule.organization_id == organization_id,
                    MaintenanceSchedule.status == MaintenanceStatus.scheduled,
                    MaintenanceSchedule.scheduled_date >= now,
                    MaintenanceSchedule.scheduled_date <= future
                )
            )
            .order_by(MaintenanceSchedule.scheduled_date)
        )
        
        result = await self.db.execute(query)
        rows = result.fetchall()
        
        schedules = []
        for schedule, car in rows:
            schedules.append({
                "id": str(schedule.id),
                "car": {
                    "id": str(car.id),
                    "license_plate": car.license_plate,
                    "make": car.make,
                    "model": car.model
                },
                "maintenance_type": schedule.maintenance_type.value,
                "scheduled_date": schedule.scheduled_date.isoformat(),
                "description": schedule.description,
                "estimated_cost": schedule.estimated_cost
            })
        
        return schedules

    async def predict_maintenance_needs(
        self,
        car_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """Predict maintenance needs based on telemetry patterns."""
        # Get recent telemetry
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        query = select(
            func.avg(OBDData.coolant_temp).label('avg_coolant'),
            func.max(OBDData.coolant_temp).label('max_coolant'),
            func.avg(OBDData.rpm).label('avg_rpm'),
            func.max(OBDData.rpm).label('max_rpm'),
            func.avg(OBDData.engine_load).label('avg_load'),
            func.count(OBDData.dtc_codes).label('dtc_count')
        ).filter(
            and_(
                OBDData.car_id == car_id,
                OBDData.time >= thirty_days_ago
            )
        )
        
        result = await self.db.execute(query)
        data = result.fetchone()
        
        if not data:
            return []
        
        predictions = []
        
        # Analyze patterns and create predictions
        # Coolant temperature issues
        if data.max_coolant and data.max_coolant > 105:
            predictions.append({
                "type": "coolant",
                "days_until": max(1, 30 - int((data.max_coolant - 105) * 3)),
                "confidence": min(0.9, 0.5 + (data.max_coolant - 105) * 0.05),
                "reasoning": f"High coolant temp detected (max: {data.max_coolant}°C)"
            })
        
        # Engine load issues
        if data.avg_load and data.avg_load > 80:
            predictions.append({
                "type": "engine",
                "days_until": max(1, 30 - int((data.avg_load - 80) * 0.5)),
                "confidence": min(0.8, 0.4 + (data.avg_load - 80) * 0.02),
                "reasoning": f"High average engine load ({data.avg_load}%)"
            })
        
        # High RPM
        if data.max_rpm and data.max_rpm > 6000:
            predictions.append({
                "type": "general",
                "days_until": 20,
                "confidence": 0.6,
                "reasoning": f"Frequent high RPM usage (max: {data.max_rpm})"
            })
        
        # DTC codes
        if data.dtc_count and data.dtc_count > 0:
            predictions.append({
                "type": "inspection",
                "days_until": 7,
                "confidence": 0.9,
                "reasoning": f"{data.dtc_count} DTC codes detected in last 30 days"
            })
        
        # Save predictions
        for pred in predictions:
            prediction = MaintenancePrediction(
                organization_id=organization_id,
                car_id=car_id,
                maintenance_type=MaintenanceType(pred["type"]),
                predicted_days_until_failure=pred["days_until"],
                confidence_score=pred["confidence"],
                reasoning=pred["reasoning"]
            )
            self.db.add(prediction)
        
        await self.db.commit()
        
        return predictions
