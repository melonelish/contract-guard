from fastapi import APIRouter

from app.api.v1 import auth, contracts, health


router = APIRouter(prefix="/api/v1")
router.include_router(health.router, tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
