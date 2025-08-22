from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# Chat related schemas
class ChatRequest(BaseModel):
    """채팅 요청 모델"""

    message: str = Field(..., description="사용자 메시지")
    user_id: Optional[str] = Field(None, description="사용자 ID")
    session_id: Optional[str] = Field(None, description="세션 ID")
    context: Optional[dict[str, Any]] = Field(None, description="대화 컨텍스트")


class ChatResponse(BaseModel):
    """채팅 응답 모델"""

    message: str = Field(..., description="어시스턴트 응답")
    session_id: str = Field(..., description="세션 ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    context: Optional[dict[str, Any]] = Field(None, description="업데이트된 컨텍스트")


# Content related schemas
class ContentType(str, Enum):
    """콘텐츠 타입"""

    ARTICLE = "article"
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"


class ContentItem(BaseModel):
    """콘텐츠 아이템 모델"""

    id: str = Field(..., description="콘텐츠 ID")
    title: str = Field(..., description="콘텐츠 제목")
    description: Optional[str] = Field(None, description="콘텐츠 설명")
    type: ContentType = Field(..., description="콘텐츠 타입")
    url: Optional[str] = Field(None, description="콘텐츠 URL")
    tags: list[str] = Field(default_factory=list, description="콘텐츠 태그")
    created_at: datetime = Field(default_factory=datetime.now)


class ContentRecommendation(BaseModel):
    """콘텐츠 추천 모델"""

    user_id: str = Field(..., description="사용자 ID")
    recommendations: list[ContentItem] = Field(..., description="추천 콘텐츠 목록")
    reason: str = Field(..., description="추천 이유")
    confidence: float = Field(..., ge=0.0, le=1.0, description="추천 신뢰도")


# Diagnosis related schemas
class DiagnosisType(str, Enum):
    """진단 타입"""

    BODY_SHAPE = "body_shape"
    FASHION_STYLE = "fashion_style"
    SKIN_TONE = "skin_tone"
    PERSONALITY = "personality"


class DiagnosisQuestion(BaseModel):
    """진단 질문 모델"""

    id: str = Field(..., description="질문 ID")
    question: str = Field(..., description="질문 내용")
    type: DiagnosisType = Field(..., description="진단 타입")
    options: Optional[list[str]] = Field(None, description="선택지 옵션")
    required: bool = Field(True, description="필수 질문 여부")


class DiagnosisAnswer(BaseModel):
    """진단 답변 모델"""

    question_id: str = Field(..., description="질문 ID")
    answer: str = Field(..., description="사용자 답변")
    timestamp: datetime = Field(default_factory=datetime.now)


class DiagnosisResult(BaseModel):
    """진단 결과 모델"""

    user_id: str = Field(..., description="사용자 ID")
    diagnosis_type: DiagnosisType = Field(..., description="진단 타입")
    answers: list[DiagnosisAnswer] = Field(..., description="답변 목록")
    result: dict[str, Any] = Field(..., description="진단 결과")
    confidence: float = Field(..., ge=0.0, le=1.0, description="진단 신뢰도")
    created_at: datetime = Field(default_factory=datetime.now)
    recommendations: Optional[list[str]] = Field(None, description="추천사항")


# Assistant service schemas
class AssistantConfig(BaseModel):
    """어시스턴트 설정 모델"""

    model: str = Field(default="gpt-4", description="사용할 AI 모델")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="창의성 수준")
    max_tokens: int = Field(default=1000, ge=1, description="최대 토큰 수")
    system_prompt: Optional[str] = Field(None, description="시스템 프롬프트")


class AssistantContext(BaseModel):
    """어시스턴트 컨텍스트 모델"""

    user_profile: Optional[dict[str, Any]] = Field(None, description="사용자 프로필")
    conversation_history: list[dict[str, Any]] = Field(
        default_factory=list, description="대화 히스토리"
    )
    current_diagnosis: Optional[DiagnosisResult] = Field(
        None, description="현재 진단 결과"
    )
    preferences: Optional[dict[str, Any]] = Field(None, description="사용자 선호도")
