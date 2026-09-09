from fastapi import FastAPI

from src.app.api.routes.conversations import router as conversations_router
from src.app.api.routes.health import router as health_router
from src.app.api.routes.users import router as users_router


app = FastAPI(
    title="Professional Learner Graph API",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(users_router)
app.include_router(conversations_router)