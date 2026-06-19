"""AI service for diagnostic and analytics functions."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from domain.models import (
    Car,
    OBDData,
    OBDDataHourly,
    AISession,
    AISessionType,
    Message,
    MessageType,
    SenderType,
    MessageScope,
)
from services.llm_client import get_llm_client, LLMError
from services.prompts import (
    DTC_EXPLANATION_SYSTEM_PROMPT,
    DTC_EXPLANATION_USER_PROMPT,
    DRIVING_PATTERN_SYSTEM_PROMPT,
    DRIVING_PATTERN_USER_PROMPT,
    FLEET_SUMMARY_SYSTEM_PROMPT,
    FLEET_SUMMARY_USER_PROMPT,
    AI_CHAT_SYSTEM_PROMPT,
    ANOMALY_ANALYSIS_SYSTEM_PROMPT,
    ANOMALY_ANALYSIS_USER_PROMPT,
)
from services.ai_safety import sanitize_response

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered diagnostics and analytics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def explain_dtc_codes(
        self, car_id: uuid.UUID, dtc_codes: List[str], user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Explain DTC codes using AI.

        Args:
            car_id: The car ID
            dtc_codes: List of DTC codes to explain
            user_id: The user requesting the explanation

        Returns:
            Dictionary with explanation and metadata
        """
        # Get car details
        result = await self.db.execute(select(Car).filter(Car.id == car_id))
        car = result.scalars().first()

        if not car:
            raise ValueError(f"Car {car_id} not found")

        organization_id = car.organization_id

        # Get recent telemetry (last 24 hours)
        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)

        telemetry_query = select(
            func.avg(OBDData.rpm).label("avg_rpm"),
            func.avg(OBDData.speed).label("avg_speed"),
            func.max(OBDData.speed).label("max_speed"),
            func.avg(OBDData.coolant_temp).label("coolant_temp"),
            func.avg(OBDData.engine_load).label("engine_load"),
            func.avg(OBDData.fuel_level).label("fuel_level"),
        ).filter(and_(OBDData.car_id == car_id, OBDData.time >= one_day_ago))

        telemetry_result = await self.db.execute(telemetry_query)
        telemetry = telemetry_result.fetchone()

        # Build prompt
        user_prompt = DTC_EXPLANATION_USER_PROMPT.format(
            make=car.make,
            model=car.model,
            year=car.year,
            dtc_codes=", ".join(dtc_codes),
            avg_rpm=int(telemetry.avg_rpm)
            if telemetry and telemetry.avg_rpm
            else "N/A",
            avg_speed=int(telemetry.avg_speed)
            if telemetry and telemetry.avg_speed
            else "N/A",
            max_speed=int(telemetry.max_speed)
            if telemetry and telemetry.max_speed
            else "N/A",
            coolant_temp=int(telemetry.coolant_temp)
            if telemetry and telemetry.coolant_temp
            else "N/A",
            engine_load=int(telemetry.engine_load)
            if telemetry and telemetry.engine_load
            else "N/A",
            fuel_level=int(telemetry.fuel_level)
            if telemetry and telemetry.fuel_level
            else "N/A",
        )

        messages = [
            {"role": "system", "content": DTC_EXPLANATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # Call LLM
        llm_client = get_llm_client()
        start_time = datetime.now(timezone.utc)

        try:
            response = await llm_client.chat(messages)
            content = response["content"]
            usage = response.get("usage", {})
        except LLMError as e:
            logger.error(f"LLM error: {e}")
            raise RuntimeError(f"AI service unavailable: {e}")

        processing_time = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        # Sanitize response
        content = sanitize_response(content)

        # Save AI session
        ai_session = AISession(
            organization_id=organization_id,
            car_id=car_id,
            user_id=user_id,
            session_type=AISessionType.diagnostic,
            prompt=user_prompt,
            response=content,
            model_used=response.get("model", "unknown"),
            tokens_used=usage.get("total_tokens", 0),
            processing_time_ms=processing_time,
        )
        self.db.add(ai_session)

        # Create message
        message = Message(
            organization_id=organization_id,
            scope=MessageScope.car,
            car_id=car_id,
            message_type=MessageType.ai_reply,
            sender_type=SenderType.ai,
            content=content,
            message_metadata={
                "ai_session_id": str(ai_session.id),
                "dtc_codes": dtc_codes,
                "session_type": "diagnostic",
            },
        )
        self.db.add(message)

        await self.db.commit()

        return {
            "session_id": str(ai_session.id),
            "explanation": content,
            "model": response.get("model", "unknown"),
            "tokens_used": usage.get("total_tokens", 0),
            "processing_time_ms": processing_time,
        }

    async def analyze_driving_pattern(
        self, car_id: uuid.UUID, days: int = 7
    ) -> Dict[str, Any]:
        """Analyze driving patterns for a car."""
        # Get car details
        result = await self.db.execute(select(Car).filter(Car.id == car_id))
        car = result.scalars().first()

        if not car:
            raise ValueError(f"Car {car_id} not found")

        # Get aggregated data
        start_time = datetime.now(timezone.utc) - timedelta(days=days)

        query = select(
            func.sum(OBDDataHourly.total_distance_km).label("total_distance"),
            func.sum(OBDDataHourly.total_fuel_consumed_l).label("total_fuel"),
            func.avg(OBDDataHourly.avg_speed).label("avg_speed"),
            func.max(OBDDataHourly.max_speed).label("max_speed"),
            func.count(func.distinct(func.date(OBDDataHourly.time))).label(
                "active_days"
            ),
        ).filter(and_(OBDDataHourly.car_id == car_id, OBDDataHourly.time >= start_time))

        result = await self.db.execute(query)
        data = result.fetchone()

        total_distance = float(data.total_distance or 0)
        total_fuel = float(data.total_fuel or 0)

        user_prompt = DRIVING_PATTERN_USER_PROMPT.format(
            days=days,
            year=car.year,
            make=car.make,
            model=car.model,
            total_distance=round(total_distance, 1),
            avg_daily_distance=round(total_distance / days, 1),
            avg_speed=int(data.avg_speed) if data.avg_speed else 0,
            max_speed=int(data.max_speed) if data.max_speed else 0,
            total_fuel=round(total_fuel, 1),
            fuel_efficiency=round(total_fuel / total_distance * 100, 1)
            if total_distance > 0
            else 0,
        )

        messages = [
            {"role": "system", "content": DRIVING_PATTERN_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        llm_client = get_llm_client()

        try:
            response = await llm_client.chat(messages)
            content = sanitize_response(response["content"])
        except LLMError as e:
            logger.error(f"LLM error: {e}")
            raise RuntimeError(f"AI service unavailable: {e}")

        return {
            "analysis": content,
            "model": response.get("model", "unknown"),
            "statistics": {
                "total_distance_km": round(total_distance, 1),
                "total_fuel_l": round(total_fuel, 1),
                "avg_speed_kmh": int(data.avg_speed) if data.avg_speed else 0,
                "max_speed_kmh": int(data.max_speed) if data.max_speed else 0,
                "fuel_efficiency_l_per_100km": round(
                    total_fuel / total_distance * 100, 1
                )
                if total_distance > 0
                else 0,
            },
        }

    async def generate_fleet_summary(
        self, organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Generate fleet-wide summary."""
        # Get fleet metrics
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get counts
        from domain.models import Car, Alert

        cars_result = await self.db.execute(
            select(func.count(Car.id)).filter(
                Car.organization_id == organization_id, Car.is_active == True
            )
        )
        total_cars = cars_result.scalar() or 0

        active_result = await self.db.execute(
            select(func.count(func.distinct(OBDDataHourly.car_id))).filter(
                OBDDataHourly.organization_id == organization_id,
                OBDDataHourly.time >= today_start,
            )
        )
        active_cars = active_result.scalar() or 0

        # Get distance and fuel
        fleet_query = select(
            func.sum(OBDDataHourly.total_distance_km).label("distance"),
            func.sum(OBDDataHourly.total_fuel_consumed_l).label("fuel"),
        ).filter(
            OBDDataHourly.organization_id == organization_id,
            OBDDataHourly.time >= today_start,
        )

        fleet_result = await self.db.execute(fleet_query)
        fleet_data = fleet_result.fetchone()

        # Get alerts
        alerts_result = await self.db.execute(
            select(func.count(Alert.id)).filter(
                Alert.organization_id == organization_id, Alert.is_resolved == False
            )
        )
        active_alerts = alerts_result.scalar() or 0

        critical_result = await self.db.execute(
            select(func.count(Alert.id)).filter(
                Alert.organization_id == organization_id,
                Alert.is_resolved == False,
                Alert.severity == "critical",
            )
        )
        critical_alerts = critical_result.scalar() or 0

        user_prompt = FLEET_SUMMARY_USER_PROMPT.format(
            total_cars=total_cars,
            active_cars=active_cars,
            total_distance=round(float(fleet_data.distance or 0), 1),
            total_fuel=round(float(fleet_data.fuel or 0), 1),
            active_alerts=active_alerts,
            critical_alerts=critical_alerts,
            dtc_summary="DTC data not available",
            health_summary="Vehicle health data not available",
        )

        messages = [
            {"role": "system", "content": FLEET_SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        llm_client = get_llm_client()

        try:
            response = await llm_client.chat(messages)
            content = sanitize_response(response["content"])
        except LLMError as e:
            logger.error(f"LLM error: {e}")
            raise RuntimeError(f"AI service unavailable: {e}")

        return {
            "summary": content,
            "model": response.get("model", "unknown"),
            "metrics": {
                "total_cars": total_cars,
                "active_cars": active_cars,
                "total_distance_km": round(float(fleet_data.distance or 0), 1),
                "total_fuel_l": round(float(fleet_data.fuel or 0), 1),
                "active_alerts": active_alerts,
                "critical_alerts": critical_alerts,
            },
        }

    async def chat(
        self,
        car_id: Optional[uuid.UUID],
        message: str,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Handle user chat with AI.

        Args:
            car_id: Optional car ID for context
            message: User message
            user_id: User ID
            organization_id: Organization ID

        Returns:
            AI response
        """
        # Build context
        context_parts = []

        if car_id:
            # Get car details
            result = await self.db.execute(select(Car).filter(Car.id == car_id))
            car = result.scalars().first()

            if car:
                context_parts.append(
                    f"Vehicle: {car.year} {car.make} {car.model} (VIN: {car.vin})"
                )

                # Get latest telemetry
                latest_result = await self.db.execute(
                    select(OBDData)
                    .filter(OBDData.car_id == car_id)
                    .order_by(OBDData.time.desc())
                    .limit(1)
                )
                latest = latest_result.scalars().first()

                if latest:
                    context_parts.append(
                        f"Latest readings - Speed: {latest.speed} km/h, "
                        f"RPM: {latest.rpm}, Coolant: {latest.coolant_temp}°C"
                    )

        context = "\n".join(context_parts)
        if context:
            message_with_context = f"{context}\n\nUser question: {message}"
        else:
            message_with_context = message

        messages = [
            {"role": "system", "content": AI_CHAT_SYSTEM_PROMPT},
            {"role": "user", "content": message_with_context},
        ]

        llm_client = get_llm_client()
        start_time = datetime.now(timezone.utc)

        try:
            response = await llm_client.chat(messages)
            content = sanitize_response(response["content"])
            usage = response.get("usage", {})
        except LLMError as e:
            logger.error(f"LLM error: {e}")
            raise RuntimeError(f"AI service unavailable: {e}")

        processing_time = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        # Save AI session
        ai_session = AISession(
            organization_id=organization_id,
            car_id=car_id,
            user_id=user_id,
            session_type=AISessionType.chat,
            prompt=message,
            response=content,
            model_used=response.get("model", "unknown"),
            tokens_used=usage.get("total_tokens", 0),
            processing_time_ms=processing_time,
        )
        self.db.add(ai_session)

        # Create message if car context
        if car_id:
            msg = Message(
                organization_id=organization_id,
                scope=MessageScope.car,
                car_id=car_id,
                message_type=MessageType.ai_reply,
                sender_type=SenderType.ai,
                content=content,
                message_metadata={"ai_session_id": str(ai_session.id)},
            )
            self.db.add(msg)

        await self.db.commit()

        return {
            "response": content,
            "session_id": str(ai_session.id),
            "model": response.get("model", "unknown"),
            "tokens_used": usage.get("total_tokens", 0),
            "processing_time_ms": processing_time,
        }

    async def get_conversation_history(
        self, user_id: uuid.UUID, car_id: Optional[uuid.UUID] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a user."""
        from sqlalchemy import desc

        query = select(AISession).filter(
            and_(
                AISession.user_id == user_id,
                AISession.session_type == AISessionType.chat,
            )
        )

        if car_id:
            query = query.filter(AISession.car_id == car_id)

        query = query.order_by(desc(AISession.created_at)).limit(limit)

        result = await self.db.execute(query)
        sessions = result.scalars().all()

        history = []
        for session in reversed(list(sessions)):
            history.append(
                {
                    "role": "user",
                    "content": session.prompt,
                    "timestamp": session.created_at.isoformat(),
                }
            )
            history.append(
                {
                    "role": "assistant",
                    "content": session.response,
                    "timestamp": session.created_at.isoformat(),
                }
            )

        return history[-limit * 2 :]

    async def continue_conversation(
        self,
        car_id: Optional[uuid.UUID],
        message: str,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        history_limit: int = 5,
    ) -> Dict[str, Any]:
        """Continue a conversation with context from previous messages."""
        history = await self.get_conversation_history(user_id, car_id, history_limit)

        from services.prompts import AI_CHAT_SYSTEM_PROMPT

        messages = [{"role": "system", "content": AI_CHAT_SYSTEM_PROMPT}]

        for msg in history[-history_limit * 2 :]:
            messages.append(msg)

        messages.append({"role": "user", "content": message})

        llm_client = get_llm_client()
        start_time = datetime.now(timezone.utc)

        try:
            response = await llm_client.chat(messages)
            content = sanitize_response(response["content"])
            usage = response.get("usage", {})
        except LLMError as e:
            logger.error(f"LLM error: {e}")
            raise RuntimeError(f"AI service unavailable: {e}")

        processing_time = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        ai_session = AISession(
            organization_id=organization_id,
            car_id=car_id,
            user_id=user_id,
            session_type=AISessionType.chat,
            prompt=message,
            response=content,
            model_used=response.get("model", "unknown"),
            tokens_used=usage.get("total_tokens", 0),
            processing_time_ms=processing_time,
        )
        self.db.add(ai_session)

        if car_id:
            msg = Message(
                organization_id=organization_id,
                scope=MessageScope.car,
                car_id=car_id,
                message_type=MessageType.ai_reply,
                sender_type=SenderType.ai,
                content=content,
                message_metadata={"ai_session_id": str(ai_session.id)},
            )
            self.db.add(msg)

        await self.db.commit()

        return {
            "response": content,
            "session_id": str(ai_session.id),
            "history": history[-history_limit * 2 :],
            "model": response.get("model", "unknown"),
            "tokens_used": usage.get("total_tokens", 0),
            "processing_time_ms": processing_time,
        }
