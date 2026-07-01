from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from middleware.auth import get_current_user
from domain.models import User
from services.telemetry import TelemetryService
from api.v1.schemas.telemetry import TelemetryBatchIngestRequest

router = APIRouter()


@router.post("/batch-process")
async def batch_process(
    request: TelemetryBatchIngestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Batch ingest telemetry data with idempotency.
    
    Accepts up to 50 telemetry records and inserts them with deduplication.
    Returns the count of successfully inserted records.
    """
    try:
        service = TelemetryService(db)
        inserted_count, skipped_count = await service.ingest_telemetry_batch(
            items=request.items,
            organization_id=current_user.organization_id,
        )
        return {
            "success": True,
            "message": f"Batch processed: {inserted_count} records",
            "inserted": inserted_count,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch processing failed: {str(e)}"
        )