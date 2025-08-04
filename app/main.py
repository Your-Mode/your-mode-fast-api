from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.assistant import router as assistant_router
from mangum import Mangum
import logging

app = FastAPI()
logger = logging.getLogger("uvicorn.access")

@app.middleware("http")
async def log_path(request: Request, call_next):
    logger.info(f"▶▶ Raw request path: {request.url.path}")
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://style-me-wine.vercel.app", "http://localhost:3000", "http://localhost:5173", "https://spring.yourmode.co.kr"],  # 허용할 프론트 도메인
    allow_methods=["*"],   # 모든 HTTP 메서드 허용 (GET, POST, OPTIONS 등)
    allow_headers=["*"],   # 모든 헤더 허용 (Content-Type 등)
)

app.include_router(assistant_router, prefix="/assistant")
handler = Mangum(app, api_gateway_base_path="/prod")
