from fastapi import APIRouter

from app.schemas.assistant import DiagnoseResponse, DiagnoseRequest
from app.services.assistant_service import diagnose_assistant_with_tool

router = APIRouter()

"""
사용자의 신체 정보를 바탕으로 OpenAI Assistant + LangChain Tool을 통해
체형을 진단하고 7개 항목으로 된 스타일링 에세이를 반환합니다.
"""
@router.post("/diagnosis", response_model=DiagnoseResponse)
def diagnose_body_type(request: DiagnoseRequest):
    user_input = "제 체형을 진단해 주세요. 아래 항목은 설문 응답이에요."
    result = diagnose_assistant_with_tool(user_input, request.model_dump())
    return result
