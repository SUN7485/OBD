"""API routes for AI-powered features."""
import logging
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.db.session import get_db
from backend.middleware.auth import get_current_user
from backend.domain.models import User, UserRole
from backend.services.ai_service import AIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


class AIChatRequest(BaseModel):
    """AI chat request."""
    message: str
    car_id: Optional[uuid.UUID] = None


class AIChatResponse(BaseModel):
    """AI chat response."""
    response: str
    session_id: str
    model: str
    tokens_used: int
    processing_time_ms: int


class DTCDiagnosticRequest(BaseModel):
    """DTC diagnostic request."""
    car_id: uuid.UUID
    dtc_codes: list[str]


class DrivingPatternRequest(BaseModel):
    """Driving pattern analysis request."""
    car_id: uuid.UUID
    days: int = Query(7, ge=1, le=30)


@router.post(
    "/chat",
    response_model=AIChatResponse,
    summary="Chat with AI",
    description="Ask AI questions about vehicles, diagnostics, or fleet management."
)
async def chat_with_ai(
    request: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    User asks AI a question.
    
    - Accepts request with car_id (optional) and message
    - Fetches relevant context (car details, recent telemetry)
    - Calls LLM and processes response
    - Stores in ai_sessions and messages tables
    - Broadcasts AI reply via WebSocket
    """
    if not request.message or len(request.message.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message must be at least 3 characters"
        )

    service = AIService(db)

    try:
        result = await service.chat(
            car_id=request.car_id,
            message=request.message,
            user_id=current_user.id,
            organization_id=current_user.organization_id
        )
    except RuntimeError as e:
        logger.error(f"AI service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is currently unavailable. Please try again later."
        )
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process your request"
        )

    # Broadcast to WebSocket if car context
    if request.car_id:
        try:
            from backend.services.websocket_manager import manager
            await manager.broadcast_to_car(
                request.car_id,
                {
                    "type": "ai_reply",
                    "data": {
                        "session_type": "chat",
                        "content": result["response"]
                    }
                }
            )
        except Exception as e:
            logger.error(f"WebSocket broadcast error: {e}")

    return AIChatResponse(**result)


@router.post(
    "/diagnostic",
    summary="DTC Diagnostic Analysis",
    description="Get AI explanation of diagnostic trouble codes."
)
async def explain_dtc_codes(
    request: DTCDiagnosticRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Explain DTC codes using AI.
    
    Triggers background task for analysis and returns immediately.
    """
    service = AIService(db)

    try:
        # Run synchronously for immediate response
        result = await service.explain_dtc_codes(
            car_id=request.car_id,
            dtc_codes=request.dtc_codes,
            user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except RuntimeError as e:
        logger.error(f"AI service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is currently unavailable"
        )
    except Exception as e:
        logger.error(f"DTC diagnostic error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze DTC codes"
        )

    # Broadcast result
    try:
        from backend.services.websocket_manager import manager
        await manager.broadcast_to_car(
            request.car_id,
            {
                "type": "ai_reply",
                "data": {
                    "session_type": "diagnostic",
                    "content": result["explanation"],
                    "dtc_codes": request.dtc_codes
                }
            }
        )
    except Exception as e:
        logger.error(f"WebSocket broadcast error: {e}")

    return {
        "session_id": result["session_id"],
        "explanation": result["explanation"],
        "model": result["model"],
        "tokens_used": result["tokens_used"],
        "processing_time_ms": result["processing_time_ms"]
    }


@router.post(
    "/driving-pattern",
    summary="Driving Pattern Analysis",
    description="Analyze driving patterns for a vehicle."
)
async def analyze_driving_pattern(
    request: DrivingPatternRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze driving patterns over a period.
    
    Returns analysis including:
    - Driving behavior patterns
    - Areas of concern
    - Recommendations for improvement
    """
    if current_user.role not in [UserRole.admin, UserRole.fleet_manager]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin or fleet_manager role"
        )

    service = AIService(db)

    try:
        result = await service.analyze_driving_pattern(
            car_id=request.car_id,
            days=request.days
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except RuntimeError as e:
        logger.error(f"AI service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is currently unavailable"
        )
    except Exception as e:
        logger.error(f"Driving pattern analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze driving patterns"
        )

    return result


@router.get(
    "/fleet-summary",
    summary="Fleet Summary Report",
    description="Generate AI-powered fleet summary report."
)
async def get_fleet_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate fleet-wide summary report.
    
    Requires admin or fleet_manager role.
    Returns aggregated metrics and AI analysis.
    """
    if current_user.role not in [UserRole.admin, UserRole.fleet_manager]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin or fleet_manager role"
        )

    service = AIService(db)

    try:
        result = await service.generate_fleet_summary(
            organization_id=current_user.organization_id
        )
    except RuntimeError as e:
        logger.error(f"AI service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is currently unavailable"
        )
    except Exception as e:
        logger.error(f"Fleet summary error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate fleet summary"
        )

    return result
