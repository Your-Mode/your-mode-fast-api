from fastapi import APIRouter, HTTPException

from chatbot.agents import BodyDiagnosisAgent, ChatAssistantAgent, StyleContentAgent
from chatbot.schemas import ChatRequest, ChatResponse

router = APIRouter()

# 에이전트 인스턴스 생성
body_diagnosis_agent = BodyDiagnosisAgent()
style_content_agent = StyleContentAgent()
chat_assistant_agent = ChatAssistantAgent()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    """
    챗봇 어시스턴트와 대화
    """
    try:
        response = chat_assistant_agent.chat(request.question, request.answer)
        return ChatResponse(
            is_success=response.get("isSuccess", False),
            selected=response.get("selected", ""),
            message=response.get("message", ""),
            next_question=response.get("nextQuestion", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/diagnose")
async def diagnose_body_type(request: dict):
    """
    체형 진단
    """
    try:
        result = body_diagnosis_agent.diagnose(
            request["answers"], request["height"], request["weight"], request["gender"]
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/diagnose/soft")
async def diagnose_body_type_soft(request: dict):
    """
    소프트 체형 진단 (비동기)
    """
    try:
        result = body_diagnosis_agent.diagnose_soft(
            request["answers"], request["height"], request["weight"], request["gender"]
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/diagnose/status/{thread_id}/{run_id}")
async def get_diagnosis_status(thread_id: str, run_id: str):
    """
    진단 상태 조회
    """
    try:
        result = body_diagnosis_agent.get_run_status(thread_id, run_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/diagnose/result/{thread_id}/{run_id}")
async def get_diagnosis_result(thread_id: str, run_id: str):
    """
    진단 결과 조회
    """
    try:
        result = body_diagnosis_agent.get_run_result(thread_id, run_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/content")
async def create_style_content(request: dict):
    """
    스타일 콘텐츠 생성
    """
    try:
        result = style_content_agent.create_content(
            request["name"],
            request["body_type"],
            request["height"],
            request["weight"],
            request["body_feature"],
            request["recommendation_items"],
            request["recommended_situation"],
            request["recommended_style"],
            request["avoid_style"],
            request["budget"],
        )
        return {"content": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/chat/body-result")
async def chat_body_result(request: dict):
    """
    체형 진단 결과를 위한 채팅
    """
    try:
        result = chat_assistant_agent.chat_body_result(
            request["answers"], request["height"], request["weight"], request["gender"]
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/status")
async def get_assistant_status():
    """
    어시스턴트 상태 확인
    """
    return {"status": "active", "service": "your-mode-chatbot"}
