from fastapi import FastAPI, Request
from app.api.assistant import router as assistant_router
from mangum import Mangum
import logging

app = FastAPI()
logger = logging.getLogger("uvicorn.access")

@app.middleware("http")
async def log_path(request: Request, call_next):
    logger.info(f"▶▶ Raw request path: {request.url.path}")
    return await call_next(request)

app.include_router(assistant_router, prefix="/assistant")
handler = Mangum(app, api_gateway_base_path="/prod")
