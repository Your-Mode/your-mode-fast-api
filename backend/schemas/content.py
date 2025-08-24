from pydantic import BaseModel, Field


class CreateContentRequest(BaseModel):
    name: str = Field(..., description="Name")
    body_type: str = Field(..., description="Body type")
    height: int = Field(..., description="Height in cm")
    weight: int = Field(..., description="Weight in kg")
    body_feature: str = Field(..., description="Body features")
    recommendation_items: list[str] = Field(..., description="Items to recommend")
    recommended_situation: str = Field(..., description="Desired situation")
    recommended_style: str = Field(..., description="Desired style")
    avoid_style: str = Field(..., description="Style to avoid")
    budget: str = Field(..., description="Budget")

    class Config:
        json_schema_extra = {
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
                "budget": "20만원",
            }
        }
