from fastapi import FastAPI
from mangum import Mangum

from app.api.assistant import router as assistant_router
app = FastAPI()
app.include_router(assistant_router, prefix="/assistant")

handler = Mangum(app)