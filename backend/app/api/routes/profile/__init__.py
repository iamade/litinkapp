from fastapi import APIRouter

router = APIRouter()

from .me import router as me_router
from .stats import router as stats_router

router.include_router(me_router)
router.include_router(stats_router)
