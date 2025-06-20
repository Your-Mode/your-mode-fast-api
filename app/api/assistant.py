# app/api/assistant.py

from fastapi import APIRouter, HTTPException
from app.schemas.assistant import DiagnoseRequest, DiagnoseResponse
from app.services.assistant_service import diagnose_body_type_with_assistant

router = APIRouter()

@router.post("/diagnosis", response_model=DiagnoseResponse)
def diagnose_body_type(request: DiagnoseRequest):
    return diagnose_body_type_with_assistant(
        answers=request.answers,
        height=request.height,
        weight=request.weight,
        gender=request.gender,
    )
