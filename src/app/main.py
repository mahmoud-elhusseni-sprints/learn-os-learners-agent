from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.api.routes.conversations import router as conversations_router
from src.app.api.routes.health import router as health_router
from src.app.api.routes.users import router as users_router

app = FastAPI(
    title="Professional Learner Graph API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(users_router)
app.include_router(conversations_router)
