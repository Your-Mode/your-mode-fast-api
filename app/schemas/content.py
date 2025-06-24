from pydantic import Field, BaseModel, ConfigDict


class CreateContentRequest(BaseModel):
    name: str = Field(..., description="이름")
    body_type: str = Field(..., description="체형 타입")
    height: int = Field(..., description="키")
    weight: int = Field(..., description="몸무게")
    body_feature: str = Field(..., description="체형적 특징")
    recommendation_items: list[str] = Field(..., description="추천 받고 싶은 아이템")
    recommended_situation: str = Field(..., description="입고 싶은 상황")
    recommended_style: str = Field(..., description="추천받고 싶은 스타일")
    avoid_style: str = Field(..., description="피하고 싶은 스타일")
    budget: str = Field(..., description="예산")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "전여진",
                "body_type": "웨이브",
                "height": 160,
                "weight": 40,
                "body_feature": "체형이 너무 얇다",
                "recommendation_items": ["상의", "하의"],
                "recommended_situation": "IR발표",
                "recommended_style": "IR 발표에 어울리는 스타일",
                "avoid_style": "스트릿,힙한 스타일",
                "budget": "20만원"
            }
        }
    )
