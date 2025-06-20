from typing import List

from pydantic import BaseModel


class DiagnoseRequest(BaseModel):
    answers: List[str]
    height: float
    weight: float
    gender: str


class DiagnoseResponse(BaseModel):
    body_type: str
    type_description: str
    detailed_features: str
    attraction_points: str
    recommended_styles: str
    avoid_styles: str
    styling_fixes: str
    styling_tips: str
