from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api.endpoints import plates

fast_app = FastAPI()

# Include API routes
fast_app.include_router(plates.router)
