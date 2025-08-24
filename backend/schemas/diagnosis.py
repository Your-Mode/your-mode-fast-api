from pydantic import BaseModel, Field


class DiagnoseRequest(BaseModel):
    answers: list[str] = Field(..., description="List of survey responses")
    height: float = Field(..., description="Height in cm")
    weight: float = Field(..., description="Weight in kg")
    gender: str = Field(..., description="Gender")

    class Config:
        json_schema_extra = {
            "example": {
                "answers": [
                    "두께감이 있고 육감적이다",
                    "피부가 탄탄하고 쫀득한 편이다",
                    "근육이 붙기 쉽다",
                    "목이 약간 짧은 편이다",
                    "허리가 짧고 직선적인 느낌이며 굴곡이 적다",
                    "두께감이 있고, 바스트 탑의 위치가 높다",
                    "어깨가 넓고 직선적인 느낌이며, 탄탄한 인상을 준다",
                    "엉덩이 라인의 위쪽부터 볼륨감이 있으며 탄력있다",
                    "허벅지가 단단하고 근육이 많아 탄력이 있다",
                    "손이 작고 손바닥에 두께감이 있다",
                    "손목이 가늘고 둥근 편이다",
                    "발이 작고 발목이 가늘며 단단하다",
                    "무릎이 작고 부각되지 않는 편이다",
                    "쇄골이 거의 보이지 않는다",
                    "둥근 얼굴이며, 볼이 통통한 편이다",
                    "상체가 발달한 느낌이며 허리가 짧고 탄탄한 인상을 준다",
                    "팔, 가슴, 배 등 상체 위주로 찐다",
                ],
                "height": 164.5,
                "weight": 55.2,
                "gender": "여성",
            }
        }


class DiagnoseResponse(BaseModel):
    body_type: str = Field(..., description="Body type classification")
    type_description: str = Field(..., description="Detailed description of body type")
    detailed_features: str = Field(..., description="Specific body features and characteristics")
    attraction_points: str = Field(..., description="Highlighted attractive features")
    recommended_styles: str = Field(..., description="Recommended fashion styles")
    avoid_styles: str = Field(..., description="Styles to avoid")
    styling_fixes: str = Field(..., description="Styling tips and fixes")
    styling_tips: str = Field(..., description="Additional styling advice")

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
                "styling_tips": "...",
            }
        }
