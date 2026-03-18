import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.auth import get_current_active_user
from app.core.database import get_session
from app.core.services.modelslab_upscale import ModelsLabUpscaleService
from app.credits.dependencies import require_credits
from app.credits.constants import OperationType, IMAGE_UPSCALE
from app.credits.service import CreditService
from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter()


class UpscaleRequest(BaseModel):
    image_url: str
    user_tier: str = "free"
    face_enhance: bool = False


@router.post("/upscale")
async def upscale_image(
    request: UpscaleRequest,
    current_user: dict = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
    reservation_id: uuid.UUID = Depends(require_credits(OperationType.IMAGE_UPSCALE, IMAGE_UPSCALE)),
):
    """
    Upscale an image using ModelsLab V6 service based on user tier.
    """
    try:
        upscale_service = ModelsLabUpscaleService()
        result = await upscale_service.upscale_with_tier(
            image_url=request.image_url,
            user_tier=request.user_tier,
            face_enhance=request.face_enhance,
        )
        credit_service = CreditService(session)
        await credit_service.confirm_deduction(reservation_id, IMAGE_UPSCALE)
        await session.commit()
        return {
            "upscaled_url": result.get(
                "upscaled_url",
                result.get("output", [])[0] if result.get("output") else None,
            )
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
