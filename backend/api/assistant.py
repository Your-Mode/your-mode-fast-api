from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.content import CreateContentRequest
from app.schemas.diagnosis import DiagnoseRequest, DiagnoseResponse
from app.services.assistant_service import (
    chat_body_assistant,
    chat_body_result,
    create_content,
    diagnose_body_type_with_assistant,
    get_run_result,
    get_run_status,
)
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/diagnosis", description="체형 진단", response_model=DiagnoseResponse)
def diagnose_body_type(request: DiagnoseRequest):
    return diagnose_body_type_with_assistant(
        answers=request.answers,
        height=request.height,
        weight=request.weight,
        gender=request.gender,
    )


@router.post("/create-content", description="콘텐츠 초안 작성")
def recommend_content(request: CreateContentRequest):
    return create_content(
        name=request.name,
        body_type=request.body_type,
        height=request.height,
        weight=request.weight,
        body_feature=request.body_feature,
        recommendation_items=request.recommendation_items,
        recommended_situation=request.recommended_situation,
        recommended_style=request.recommended_style,
        avoid_style=request.avoid_style,
        budget=request.budget,
    )


@router.post("/chat", description="체형 진단 개별 질문에 대한 응답", response_model=ChatResponse)
def chat(request: ChatRequest):
    return chat_body_assistant(request.question, request.answer)


# @router.post("/body-result", response_model=DiagnoseResponse)
# def post_body_result(request: DiagnoseRequest):
#     return chat_body_result(
#         answers=request.answers,
#         height=request.height,
#         weight=request.weight,
#         gender=request.gender,
#     )


@router.post("/body-result")
def post_body_result(request: DiagnoseRequest):
    try:
        out = chat_body_result(
            answers=request.answers,
            height=request.height,
            weight=request.weight,
            gender=request.gender,
        )
    except Exception as e:
        raise HTTPException(502, f"assistants error: {e}") from e

    # 완료면 dict(결과) → 200
    if "thread_id" not in out:
        return out  # DiagnoseResponse 스키마와 매칭됨

    # 미완료면 202로 run 식별자 반환
    return JSONResponse(status_code=202, content=out)


# --- 폴링: 상태 조회 ---
@router.get("/run-status")
def run_status(thread_id: str, run_id: str):
    try:
        return get_run_status(thread_id, run_id)
    except Exception as e:
        raise HTTPException(502, f"assistants status error: {e}") from e


# --- 폴링: 결과 조회 ---
@router.get("/run-result", response_model=DiagnoseResponse)
def run_result(thread_id: str, run_id: str):
    try:
        data = get_run_result(thread_id, run_id)
    except Exception as e:
        raise HTTPException(502, f"assistants result error: {e}") from e

    if data.get("status") != "completed":
        # 아직 준비 안 됨
        raise HTTPException(425, f"run not completed: {data.get('status')}")

    # completed이면 DiagnoseResponse 스키마로 반환
    data.pop("status", None)
    return data
