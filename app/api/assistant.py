from fastapi import APIRouter

from app.schemas.assistant import MessageResponse, MessageRequest
from app.services.assistant_service import send_message_to_assistant

router = APIRouter()

@router.post("/message", response_model=MessageResponse)
def chat_with_assistant(request: MessageRequest):
    response = send_message_to_assistant(request.user_input)
    return MessageResponse(assistant_response=response)