"""
Chat Agent API endpoints
ChatAgent를 사용하는 API 엔드포인트
"""

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from chatbot.agents.chat_agent import ChatAgent, ChatAgentState

router = APIRouter(prefix="/chat-agent", tags=["chat-agent"])

# 세션 저장소 (실제 구현에서는 Redis나 데이터베이스 사용)
chat_sessions: Dict[str, ChatAgentState] = {}
chat_agent = ChatAgent()


class StartChatRequest(BaseModel):
    questions: list[dict[str, Any]]


class SubmitAnswerRequest(BaseModel):
    session_id: str
    answer: str


class ChatResponse(BaseModel):
    session_id: str
    status: str
    current_question: Optional[dict[str, Any]] = None
    chatbot_message: Optional[str] = None
    error_message: Optional[str] = None
    progress: Optional[str] = None
    is_completed: bool = False
    answers: Optional[dict[str, Any]] = None
    # 추가 가이드 관련 필드
    additional_guide: Optional[str] = None
    guide_type: Optional[str] = None  # "hint", "explanation", "example", "correction"
    requires_action: Optional[str] = None  # "retry", "clarify", "continue"


@router.post("/start", response_model=ChatResponse)
async def start_chat(request: StartChatRequest):
    """채팅 시작"""
    try:
        # 세션 ID 생성
        session_id = str(uuid.uuid4())

        # ChatAgent로 대화 시작
        initial_state = chat_agent.start_conversation(request.questions)

        # 세션 저장
        chat_sessions[session_id] = initial_state

        # 첫 번째 질문 가져오기
        current_status = chat_agent.get_current_status(initial_state)

        return ChatResponse(
            session_id=session_id,
            status="started",
            current_question=current_status.get("next_question"),
            progress=current_status.get("progress"),
            is_completed=False,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"채팅 시작 실패: {str(e)}")


@router.post("/answer", response_model=ChatResponse)
async def submit_answer(request: SubmitAnswerRequest):
    """답변 제출"""
    try:
        # 세션 확인
        if request.session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

        current_state = chat_sessions[request.session_id]

        # ChatAgent로 답변 제출 및 LangGraph 실행
        updated_state = chat_agent.submit_answer(current_state, request.answer)

        # 세션 업데이트
        chat_sessions[request.session_id] = updated_state

        # 현재 상태 반환
        current_status = chat_agent.get_current_status(updated_state)

        return ChatResponse(
            session_id=request.session_id,
            status=current_status["current_status"],
            current_question=current_status.get("next_question"),
            chatbot_message=current_status.get("chatbot_message"),
            error_message=current_status.get("error_message"),
            progress=current_status.get("progress"),
            is_completed=current_status["is_completed"],
            answers=current_status.get("answers"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"답변 처리 실패: {str(e)}")


@router.get("/status/{session_id}", response_model=ChatResponse)
async def get_chat_status(session_id: str):
    """채팅 상태 확인"""
    try:
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

        current_state = chat_sessions[session_id]
        current_status = chat_agent.get_current_status(current_state)

        return ChatResponse(
            session_id=session_id,
            status=current_status["current_status"],
            current_question=current_status.get("next_question"),
            chatbot_message=current_status.get("chatbot_message"),
            error_message=current_status.get("error_message"),
            progress=current_status.get("progress"),
            is_completed=current_status["is_completed"],
            answers=current_status.get("answers"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 확인 실패: {str(e)}")


@router.delete("/session/{session_id}")
async def delete_chat_session(session_id: str):
    """채팅 세션 삭제"""
    try:
        if session_id in chat_sessions:
            del chat_sessions[session_id]
            return {"message": "세션이 삭제되었습니다"}
        else:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 삭제 실패: {str(e)}")
