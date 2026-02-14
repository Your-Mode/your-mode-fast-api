from pydantic import Field, BaseModel, ConfigDict


class ChatRequest(BaseModel):
    question: str = Field(..., description="질문")
    answer: str = Field(..., description="응답")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "1. 피부는 어떤 느낌인가요?",
                "answer": "피부가 부드럽고 말랑말랑해요.",
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
