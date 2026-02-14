from typing import List
from pydantic import BaseModel, Field, ConfigDict

class DiagnoseRequest(BaseModel):
    answers: List[str] = Field(..., description="15개 설문 응답 리스트(문항 순서대로)")
    height: float      = Field(..., description="키 (cm)")
    weight: float      = Field(..., description="체중 (kg)")
    gender: str        = Field(..., description="성별")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "answers": [
                    "피부가 부드럽고 말랑말랑하다",
                    "전체적으로 지방이 잘 느껴지고, 근육이 잘 붙지 않는 편이다",
                    "하체(허벅지, 배, 특히 승마살)에 살이 먼저 붙는 편이다",
                    "목이 가늘고 긴 편이며 승모근이 크게 부각되지 않는 편이다",
                    "쇄골이 가늘고 자연스럽게 보이는 편이다",
                    "어깨가 좁고 둥글며 좁은 편이다",
                    "바스트탑이 낮고 볼륨감이 적으며, 부드러운 편이다",
                    "허리가 길고 자연스럽게 잘록한 느낌이 있다",
                    "입체감이 적고, 근육이 부족해 아래로 쳐진 편이다",
                    "허벅지 바깥쪽(승마살)에 살이 잘 붙는 편이다",
                    "무릎 뼈는 보통이고 약간 눈에 띄는 편이다",
                    "팔이 부드럽게 이어지는 느낌이며 말랑한 편이다",
                    "손 크기는 보통이며, 손가락이 가늘고 얇은 편이다",
                    "손목이 타원형 같거나 납작한 느낌이다",
                    "하체가 상대적으로 부각되며 전체적으로 여리여리한 느낌이다"
                ],
                "height": 164.5,
                "weight": 55.2,
                "gender": "여성"
            }
        }
    )


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
