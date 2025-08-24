"""
Conversation API endpoints
대화 그래프 에이전트를 사용하는 API 엔드포인트
"""

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from chatbot.agents.conversation_graph import ConversationGraphAgent, ConversationState

router = APIRouter(prefix="/conversation", tags=["conversation"])

# 세션 저장소 (실제 구현에서는 Redis나 데이터베이스 사용)
conversation_sessions: Dict[str, ConversationState] = {}
conversation_agent = ConversationGraphAgent()


class StartConversationRequest(BaseModel):
    custom_questions: Optional[list] = None
    user_preferences: Optional[Dict[str, Any]] = None


class SubmitAnswerRequest(BaseModel):
    session_id: str
    answer: str


class ConversationResponse(BaseModel):
    session_id: str
    status: str
    current_question: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    progress: Optional[str] = None
    is_completed: bool = False
    answers: Optional[Dict[str, Any]] = None


@router.post("/start", response_model=ConversationResponse)
async def start_conversation(request: StartConversationRequest):
    """대화 시작"""
    try:
        # 세션 ID 생성
        session_id = str(uuid.uuid4())

        # 대화 시작
        initial_state = conversation_agent.start_conversation()

        if request.custom_questions:
            initial_state["questions"] = request.custom_questions

        if request.user_preferences:
            initial_state["user_preferences"] = request.user_preferences

        # 세션 저장
        conversation_sessions[session_id] = initial_state

        # 첫 번째 질문 가져오기
        current_status = conversation_agent.get_current_status(initial_state)

        return ConversationResponse(
            session_id=session_id,
            status="started",
            current_question=current_status.get("next_question"),
            progress=current_status.get("progress"),
            is_completed=False,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대화 시작 실패: {str(e)}")


@router.post("/answer", response_model=ConversationResponse)
async def submit_answer(request: SubmitAnswerRequest):
    """답변 제출"""
    try:
        # 세션 확인
        if request.session_id not in conversation_sessions:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

        current_state = conversation_sessions[request.session_id]

        # 답변 제출 및 검증
        updated_state = conversation_agent.submit_answer(current_state, request.answer)

        # 세션 업데이트
        conversation_sessions[request.session_id] = updated_state

        # 현재 상태 반환
        current_status = conversation_agent.get_current_status(updated_state)

        return ConversationResponse(
            session_id=request.session_id,
            status=current_status["current_status"],
            current_question=current_status.get("next_question"),
            error_message=current_status.get("error_message"),
            progress=current_status.get("progress"),
            is_completed=current_status["is_completed"],
            answers=current_status.get("answers"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"답변 처리 실패: {str(e)}")


@router.get("/status/{session_id}", response_model=ConversationResponse)
async def get_conversation_status(session_id: str):
    """대화 상태 확인"""
    try:
        if session_id not in conversation_sessions:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

        current_state = conversation_sessions[session_id]
        current_status = conversation_agent.get_current_status(current_state)

        return ConversationResponse(
            session_id=session_id,
            status=current_status["current_status"],
            current_question=current_status.get("next_question"),
            error_message=current_status.get("error_message"),
            progress=current_status.get("progress"),
            is_completed=current_status["is_completed"],
            answers=current_status.get("answers"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 확인 실패: {str(e)}")


@router.delete("/session/{session_id}")
async def delete_conversation_session(session_id: str):
    """대화 세션 삭제"""
    try:
        if session_id in conversation_sessions:
            del conversation_sessions[session_id]
            return {"message": "세션이 삭제되었습니다"}
        else:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 삭제 실패: {str(e)}")


@router.get("/sessions")
async def list_conversation_sessions():
    """활성 세션 목록"""
    try:
        sessions = []
        for session_id, state in conversation_sessions.items():
            current_status = conversation_agent.get_current_status(state)
            sessions.append(
                {
                    "session_id": session_id,
                    "status": current_status["current_status"],
                    "progress": current_status.get("progress"),
                    "is_completed": current_status["is_completed"],
                    "created_at": state.get("conversation_history", [{}])[0].get("timestamp")
                    if state.get("conversation_history")
                    else None,
                }
            )

        return {"sessions": sessions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 목록 조회 실패: {str(e)}")
