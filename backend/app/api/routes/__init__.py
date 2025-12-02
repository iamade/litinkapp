from fastapi import APIRouter
from .home import router as home_router
from .auth import router as auth_router
from .books import router as books_router
from .ai import router as ai_router
from .profile import router as users_router
from .quizzes import router as quizzes_router
from .badges import router as badges_router
from .nfts import router as nfts_router
from .payments import router as payments_router
from .subscriptions import router as subscriptions_router
from .plots import router as plots_router
from .characters import router as characters_router
from .chapters import router as chapters_router
from .merge import router as merge_router
from .image_generations import router as image_generations_router
from .admin import router as admin_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(books_router, prefix="/books", tags=["books"])
api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
api_router.include_router(plots_router, prefix="/plots", tags=["plots"])
api_router.include_router(characters_router, prefix="/characters", tags=["characters"])
api_router.include_router(chapters_router, prefix="/chapters", tags=["chapters"])
api_router.include_router(quizzes_router, prefix="/quizzes", tags=["quizzes"])
api_router.include_router(badges_router, prefix="/badges", tags=["badges"])
api_router.include_router(nfts_router, prefix="/nfts", tags=["nfts"])
api_router.include_router(payments_router, prefix="/payments", tags=["payments"])
api_router.include_router(
    subscriptions_router, prefix="/subscriptions", tags=["subscriptions"]
)
api_router.include_router(merge_router, prefix="/merge", tags=["merge"])
api_router.include_router(
    image_generations_router, prefix="/image-generations", tags=["image-generations"]
)
api_router.include_router(admin_router, tags=["admin"])
api_router.include_router(home_router, tags=["home"])
