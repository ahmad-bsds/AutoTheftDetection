from fastapi import APIRouter
from api.endpoints.plates import router as plates_router

router = APIRouter()
router.include_router(plates_router, prefix="/plates", tags=["plates"])

