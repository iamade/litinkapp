from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.auth import get_current_active_user
from app.core.services.modelslab_upscale import ModelsLabUpscaleService

router = APIRouter()


class UpscaleRequest(BaseModel):
    image_url: str
    user_tier: str = "free"
    face_enhance: bool = False


@router.post("/upscale")
async def upscale_image(
    request: UpscaleRequest,
    current_user: dict = Depends(get_current_active_user),
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
        return {
            "upscaled_url": result.get(
                "upscaled_url",
                result.get("output", [])[0] if result.get("output") else None,
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
