import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from starlette.types import ASGIApp

from chatbot.api.conversation import router as conversation_router
from chatbot.assistant import router as chatbot_router

app = FastAPI()
logger = logging.getLogger("app.logger")


@app.middleware("http")
async def log_path(request: Request, call_next: ASGIApp):
    logger.info(f"▶▶ Raw request path: {request.url.path}")
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://style-me-wine.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "https://spring.yourmode.co.kr",
        "https://yourmode.co.kr/",
    ],  # 허용할 프론트 도메인
    allow_methods=["*"],  # 모든 HTTP 메서드 허용 (GET, POST, OPTIONS 등)
    allow_headers=["*"],  # 모든 헤더 허용 (Content-Type 등)
)


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "your-mode-backend"}


# Include chatbot router
app.include_router(chatbot_router, prefix="/chatbot")

# Include conversation router
app.include_router(conversation_router, prefix="/api")

handler = Mangum(app, api_gateway_base_path="/prod")
