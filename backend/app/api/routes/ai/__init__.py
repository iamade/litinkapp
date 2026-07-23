from .routes import router
from .cinematic_gates import router as cinematic_gates_router

router.include_router(cinematic_gates_router, prefix="/api/v1")
from .production_bible import router as production_bible_router
