from pydantic import Field, BaseModel, ConfigDict


class ChatRequest(BaseModel):
    question: str = Field(..., description="질문"),
    answer: str = Field(..., description="응답")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "1. 전체적인 골격의 인상은 어떠한가요?",
                "answer": "두께감이 있고, 육감적입니다.",
            }
        }
    )


class ChatResponse(BaseModel):
    isSuccess: bool
    selected: str
    message: str
    nextQuestion: str

    class Config:
        schema_extra = {
            "example": {
                "isSuccess": "스트레이트",
                "selected": "어깨와 엉덩이 폭이 비슷한...",
                "message": "...",
                "nextQuestion": "...",
            }
        }
