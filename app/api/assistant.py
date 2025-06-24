from fastapi import APIRouter
from app.schemas.diagnosis import DiagnoseRequest, DiagnoseResponse
from app.schemas.content import CreateContentRequest
from app.services.assistant_service import diagnose_body_type_with_assistant, create_content

router = APIRouter()


@router.post("/diagnosis", description="체형 진단", response_model=DiagnoseResponse)
def diagnose_body_type(request: DiagnoseRequest):
    return diagnose_body_type_with_assistant(
        answers=request.answers,
        height=request.height,
        weight=request.weight,
        gender=request.gender,
    )


@router.post("/create-content", description="콘텐츠 초안 작성" )
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
        budget=request.budget
    )
