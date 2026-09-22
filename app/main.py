from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router


app = FastAPI(
    title="Enterprise RAG Platform",
    version="0.1.0",
)


app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversations_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "enterprise-rag",
    }