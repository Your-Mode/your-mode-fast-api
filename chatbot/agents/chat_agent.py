from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from openai import OpenAI
from pydantic import BaseModel, Field

from chatbot.utils.config_handler import load_config
from chatbot.utils.path import CHATBOT_CONFIG


class ChatAgentState(BaseModel):
    current_question_id: int = Field(..., description="Current question identifier")
    questions: list[dict[str, Any]] = Field(..., description="List of question objects")
    user_answers: dict[int, str] = Field(
        default_factory=dict, description="User answers mapped by question ID"
    )
    validation_results: dict[int, dict[str, Any]] = Field(
        default_factory=dict, description="Validation results for each answer"
    )
    conversation_history: list[dict[str, Any]] = Field(
        default_factory=list, description="Conversation interaction history"
    )
    current_status: str = Field(default="starting", description="Current conversation status")
    error_message: str = Field(default="", description="Error message if validation fails")
    next_question: dict[str, Any] = Field(
        default_factory=dict, description="Next question to be asked"
    )
    is_completed: bool = Field(default=False, description="Whether the conversation is completed")
    retry_count: dict[int, int] = Field(
        default_factory=dict, description="Retry count for each question"
    )
    chatbot_response: str = Field(default="", description="Chatbot response message")
    requires_retry: bool = Field(default=False, description="Whether retry is required")


class ChatAgent:
    def __init__(self) -> None:
        self.config = load_config(CHATBOT_CONFIG)
        self.client = OpenAI(api_key=self.config.get("openai_api_key"))
        self.assistant_id = self.config["assistants"]["chat_assistant_id"]
        self.max_retries = 3  # 최대 재시도 횟수
        self.graph = self._build_graph()
        self.memory = MemorySaver()

    def _build_graph(self) -> StateGraph:
        """대화 그래프 구성"""
        workflow = StateGraph(ChatAgentState)

        # 노드 추가
        workflow.add_node("ask_question", self._ask_question)
        workflow.add_node("validate_answer", self._validate_answer)
        workflow.add_node("handle_invalid_answer", self._handle_invalid_answer)
        workflow.add_node("generate_chatbot_response", self._generate_chatbot_response)
        workflow.add_node("save_answer", self._save_answer)
        workflow.add_node("check_completion", self._check_completion)

        # 엣지 연결
        workflow.set_entry_point("ask_question")

        workflow.add_edge("ask_question", "validate_answer")
        workflow.add_conditional_edges(
            "validate_answer",
            self._route_after_validation,
            {
                "valid": "generate_chatbot_response",
                "invalid": "handle_invalid_answer",
                "completed": END,
            },
        )
        workflow.add_edge("handle_invalid_answer", "ask_question")
        workflow.add_edge("generate_chatbot_response", "save_answer")
        workflow.add_edge("save_answer", "check_completion")
        workflow.add_conditional_edges(
            "check_completion",
            self._route_after_save,
            {"continue": "ask_question", "completed": END},
        )

        return workflow.compile(checkpointer=self.memory)

    def _ask_question(self, state: ChatAgentState) -> ChatAgentState:
        """질문 제시"""
        # TODO: 질문 제시 로직 구현
        # 재시도인 경우 도움말 포함
        return state

    def _validate_answer(self, state: ChatAgentState) -> ChatAgentState:
        """답변 유효성 검증"""
        # TODO: 답변 유효성 검증 로직 구현
        return state

    def _handle_invalid_answer(self, state: ChatAgentState) -> ChatAgentState:
        """유효하지 않은 답변 처리 및 재질문 가이드"""
        # TODO: 재시도 횟수 확인 및 가이드 생성 로직 구현
        return state

    def _generate_chatbot_response(self, state: ChatAgentState) -> ChatAgentState:
        """유효한 답변에 대한 챗봇 응답 생성"""
        # TODO: 챗봇 응답 생성 로직 구현
        return state

    def _save_answer(self, state: ChatAgentState) -> ChatAgentState:
        """유효한 답변 저장"""
        # TODO: 답변 저장 로직 구현
        return state

    def _check_completion(self, state: ChatAgentState) -> ChatAgentState:
        """완료 여부 확인"""
        # TODO: 완료 여부 확인 로직 구현
        return state

    def _route_after_validation(self, state: ChatAgentState) -> str:
        """검증 후 라우팅"""
        # TODO: 검증 후 라우팅 로직 구현
        return "valid"

    def _route_after_save(self, state: ChatAgentState) -> str:
        """저장 후 라우팅"""
        # TODO: 저장 후 라우팅 로직 구현
        return "continue"

    def start_conversation(self, questions: list[dict[str, Any]]) -> ChatAgentState:
        """대화 시작"""
        initial_state = ChatAgentState(
            current_question_id=1,
            questions=questions,
            user_answers={},
            validation_results={},
            conversation_history=[],
            current_status="starting",
            error_message="",
            next_question={},
            is_completed=False,
            retry_count={},
            chatbot_response="",
            requires_retry=False,
        )

        return initial_state

    def submit_answer(self, state: ChatAgentState, answer: str) -> ChatAgentState:
        """답변 제출"""
        current_id = state.current_question_id
        state.user_answers[current_id] = answer

        # 그래프 실행
        result = self.graph.invoke(state)
        return result

    def get_current_status(self, state: ChatAgentState) -> dict[str, Any]:
        """현재 상태 반환"""
        return {
            "current_question_id": state.current_question_id,
            "total_questions": len(state.questions),
            "progress": f"{state.current_question_id}/{len(state.questions)}",
            "current_status": state.current_status,
            "next_question": state.next_question,
            "error_message": state.error_message,
            "is_completed": state.is_completed,
            "chatbot_response": state.chatbot_response,
            "requires_retry": state.requires_retry,
            "answers": state.user_answers,
        }
