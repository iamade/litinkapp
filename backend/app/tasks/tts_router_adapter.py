from typing import Any, Dict, Optional
from app.core.services.tts.router import tts_router

async def _generate_tts_via_router(
    user_id: Optional[str],
    user_tier: str,
    text: str,
    voice_id: Optional[str] = None,
    model: Optional[str] = None,
    model_chain: Optional[list] = None,
    style: float = 0.0,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Adapter to route TTS requests through the TTSRouter.
    Ensures consistency with the current result shape expected by audio_tasks.py.
    """
    try:
        # The router.synthesize returns a dict via TTSResult.to_dict()
        result = await tts_router.synthesize(
            text=text,
            user_tier=user_tier,
            voice_id=voice_id,
            model=model,
            model_chain=model_chain,
            style=style,
            **kwargs
        )
        
        # Map router/TTSResult fields to the shape expected by audio_tasks.py
        # Current audio_tasks.py expects: {"status": "success", "audio_url": "...", "audio_time": ..., "model_used": "..."}
        return {
            "status": result.get("status", "error"),
            "audio_url": result.get("audio_url"),
            "audio_time": result.get("duration_seconds", 0),
            "model_used": result.get("model", "unknown"),
            "service": result.get("provider", "tts_router"),
            "meta": result.get("metadata", {}),
            "error": result.get("error")
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "service": "tts_router"
        }
