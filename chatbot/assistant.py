from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.assistant_service import AssistantService

router = APIRouter()
assistant_service = AssistantService()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    """
    챗봇 어시스턴트와 대화
    """
    try:
        response = await assistant_service.process_chat(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/status")
async def get_assistant_status():
    """
    어시스턴트 상태 확인
    """
    return {"status": "active", "service": "your-mode-chatbot"}
