from fastapi import APIRouter

from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.mentor import router as mentor_router


api_router_v1 = APIRouter()
api_router_v1.include_router(health_router)
api_router_v1.include_router(mentor_router)
