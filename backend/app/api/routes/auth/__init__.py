from fastapi import APIRouter
from .login import router as login_router
from .register import router as register_router
from .password_reset import router as password_reset_router
from .refresh import router as refresh_router
from .activate import router as activate_router
from .logout import router as logout_router
from .oauth import router as oauth_router

router = APIRouter()

# Include routers
router.include_router(login_router)
router.include_router(register_router)
router.include_router(password_reset_router)
router.include_router(refresh_router)
router.include_router(activate_router)
router.include_router(logout_router)
router.include_router(oauth_router)
