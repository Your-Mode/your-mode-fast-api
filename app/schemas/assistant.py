from pydantic import BaseModel, Field
from typing import List

class DiagnoseRequest(BaseModel):
    answers: List[str] = Field(..., description="설문 응답 리스트")
    height: float      = Field(..., description="키 (cm)")
    weight: float      = Field(..., description="체중 (kg)")
    gender: str        = Field(..., description="성별")

class DiagnoseResponse(BaseModel):
    body_type: str
    type_description: str
    detailed_features: str
    attraction_points: str
    recommended_styles: str
    avoid_styles: str
    styling_fixes: str
    styling_tips: str

    class Config:
        schema_extra = {
            "example": {
                "body_type": "스트레이트",
                "type_description": "어깨와 엉덩이 폭이 비슷한...",
                "detailed_features": "...",
                "attraction_points": "...",
                "recommended_styles": "...",
                "avoid_styles": "...",
                "styling_fixes": "...",
                "styling_tips": "..."
            }
        }
