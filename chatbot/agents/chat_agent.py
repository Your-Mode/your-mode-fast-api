import time
import uuid
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from chatbot.utils.config_handler import load_json, load_yaml
from chatbot.utils.path import BODY_DIAGNOSIS_QUESTIONS, CHATBOT_CONFIG


class ChatAgentState(BaseModel):
    thread_id: str = Field(
        description="Unique conversation thread ID", default_factory=lambda: str(uuid.uuid4())
    )
    current_question_id: int = Field(
        description="Current Question ID",
        default=1,
    )
    retry_count: int = Field(
        description="Retry count for question",
        default=0,
    )
    current_status: str = Field(description="Current conversation status", default="starting")
    chatbot_message: str = Field(
        description="Chatbot's message",
        default="",
    )
    user_answer: str = Field(
        description="User's input message",
        default="",
    )
    chatbot_response: str = Field(
        description="Chatbot's response message about the user's answer",
        default="",
    )
    conversation_history: list[dict[str, Any]] = Field(
        description="Conversation interaction history", default_factory=list
    )
    is_completed: bool = Field(default=False, description="Whether the conversation is completed")


class ChatAgent:
    def __init__(self) -> None:
        self.config = load_yaml(CHATBOT_CONFIG)
        self.questions = load_json(BODY_DIAGNOSIS_QUESTIONS)

        self.max_retries = 3  # 최대 재시도 횟수
        self.graph = self._build_graph()
        self.memory = MemorySaver()

        # 외부 상태 관리
        self.external_answers = {}  # 외부에서 받은 답변 저장소
        self.question_callbacks = {}  # 질문 전송 콜백 함수들
        self.conversation_states = {}  # 대화 상태 저장소

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(ChatAgentState)

        workflow.add_node("ask_question", self._ask_question)
        workflow.add_node("wait_for_answer", self._wait_for_answer)
        workflow.add_node("validate_answer", self._validate_answer)
        workflow.add_node("handle_invalid_answer", self._handle_invalid_answer)
        workflow.add_node("generate_chatbot_response", self._generate_chatbot_response)
        workflow.add_node("save_answer", self._save_answer)
        workflow.add_node("check_completion", self._check_completion)

        workflow.set_entry_point("ask_question")

        workflow.add_edge("ask_question", "wait_for_answer")

        # wait_for_answer → validate_answer (답변 대기 상태 확인을 위한 라우터)
        workflow.add_conditional_edges(
            "wait_for_answer",
            self._route_after_wait,
            {
                "waiting": "wait_for_answer",  # 답변 대기 상태 유지
                "answer_received": "validate_answer",  # 답변 수신됨
                "timeout": "handle_invalid_answer",  # 타임아웃 처리
            },
        )

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
        current_question = self.questions[state.current_question_id - 1]

        # 질문을 state에 저장
        state.chatbot_message = current_question["question"]
        state.current_status = "question_asked"

        # 대화 내역에 질문 추가
        state.conversation_history.append(
            {
                "type": "question",
                "question_id": state.current_question_id,
                "question": current_question["question"],
                "timestamp": time.time(),
                "thread_id": state.thread_id,
            }
        )

        # 외부로 질문 전송 (콜백 함수가 있으면)
        if state.thread_id in self.question_callbacks:
            self.question_callbacks[state.thread_id](
                {
                    "type": "question",
                    "question_id": state.current_question_id,
                    "question": current_question["question"],
                    "thread_id": state.thread_id,
                    "timestamp": time.time(),
                }
            )

        return state

    def _wait_for_answer(self, state: ChatAgentState) -> ChatAgentState:
        """사용자 답변 대기/수집"""
        # 외부 저장소에서 답변 확인
        if state.thread_id in self.external_answers:
            external_data = self.external_answers[state.thread_id]

            # 현재 질문에 대한 답변인지 확인
            if external_data["question_id"] == state.current_question_id:
                # 답변을 state에 저장
                state.user_answer = external_data["answer"]
                state.current_status = "answer_received"

                # 대화 내역에 답변 추가
                state.conversation_history.append(
                    {
                        "type": "user_answer",
                        "question_id": state.current_question_id,
                        "answer": external_data["answer"],
                        "timestamp": time.time(),
                        "thread_id": state.thread_id,
                    }
                )

                # 사용된 답변은 제거
                del self.external_answers[state.thread_id]

                return state

        # 답변이 없으면 대기 상태 유지
        state.current_status = "waiting_answer"
        return state

    def _validate_answer(self, state: ChatAgentState) -> ChatAgentState:
        """답변 유효성 검증"""
        if state.current_status == "answer_received":
            # 간단한 검증 로직 (실제로는 더 복잡한 검증 필요)
            if state.user_answer and len(state.user_answer.strip()) > 0:
                state.current_status = "valid"
            else:
                state.current_status = "invalid"
        return state

    def _handle_invalid_answer(self, state: ChatAgentState) -> ChatAgentState:
        """유효하지 않은 답변 처리 및 재질문 가이드"""
        # 재시도 횟수 증가
        state.retry_count += 1

        # 대화 내역에 에러 추가
        state.conversation_history.append(
            {
                "type": "error",
                "question_id": state.current_question_id,
                "error_message": "답변이 유효하지 않습니다. 다시 시도해주세요.",
                "retry_count": state.retry_count,
                "timestamp": time.time(),
                "thread_id": state.thread_id,
            }
        )

        # 최대 재시도 횟수 확인
        if state.retry_count >= self.max_retries:
            state.current_status = "max_retries_exceeded"
        else:
            state.current_status = "retry"

        return state

    def _generate_chatbot_response(self, state: ChatAgentState) -> ChatAgentState:
        """유효한 답변에 대한 챗봇 응답 생성"""
        # 챗봇 응답 생성 (예시)
        response = f"좋습니다! '{state.user_answer}'에 대한 답변을 받았습니다."
        state.chatbot_response = response

        # 대화 내역에 챗봇 응답 추가
        state.conversation_history.append(
            {
                "type": "chatbot_response",
                "question_id": state.current_question_id,
                "response": response,
                "timestamp": time.time(),
                "thread_id": state.thread_id,
            }
        )

        return state

    def _save_answer(self, state: ChatAgentState) -> ChatAgentState:
        """유효한 답변 저장"""
        # 대화 내역에 성공 기록 추가
        state.conversation_history.append(
            {
                "type": "success",
                "question_id": state.current_question_id,
                "answer": state.user_answer,
                "timestamp": time.time(),
                "thread_id": state.thread_id,
            }
        )

        return state

    def _check_completion(self, state: ChatAgentState) -> ChatAgentState:
        """완료 여부 확인"""
        if state.current_question_id >= len(self.questions):
            state.is_completed = True
            state.current_status = "completed"

            # 대화 내역에 완료 기록 추가
            state.conversation_history.append(
                {
                    "type": "completion",
                    "message": "모든 질문이 완료되었습니다.",
                    "timestamp": time.time(),
                    "thread_id": state.thread_id,
                }
            )
        else:
            # 다음 질문으로 이동
            state.current_question_id += 1
            state.retry_count = 0  # 재시도 횟수 초기화
            state.current_status = "continue"

        return state

    def _route_after_validation(self, state: ChatAgentState) -> str:
        """검증 후 라우팅"""
        if state.current_status == "completed":
            return "completed"
        elif state.current_status == "valid":
            return "valid"
        elif state.current_status == "invalid":
            return "invalid"
        elif state.current_status == "waiting_answer":
            return "waiting"
        else:
            return "invalid"

    def _route_after_wait(self, state: ChatAgentState) -> str:
        """답변 대기 상태 확인 후 라우팅"""
        if state.current_status == "answer_received":
            return "answer_received"  # 답변이 수신됨 → 검증으로
        elif state.current_status == "waiting_answer":
            return "waiting"  # 아직 답변 대기 중 → 계속 대기
        elif state.current_status == "timeout":
            return "timeout"  # 타임아웃 → 에러 처리
        else:
            return "waiting"  # 기본적으로 대기 상태

    def _route_after_save(self, state: ChatAgentState) -> str:
        """저장 후 라우팅"""
        if state.is_completed:
            return "completed"
        else:
            return "continue"

    def start_conversation(self) -> ChatAgentState:
        """대화 시작"""
        thread_id = str(uuid.uuid4())
        initial_state = ChatAgentState(
            thread_id=thread_id,
            current_question_id=1,
            retry_count=0,
            current_status="starting",
            chatbot_message="",
            user_answer="",
            chatbot_response="",
            conversation_history=[],
            is_completed=False,
        )

        # 대화 상태를 저장소에 저장
        self.conversation_states[thread_id] = initial_state

        return initial_state

    def submit_answer(self, thread_id: str, answer: str) -> dict:
        """API에서 답변 제출"""
        if thread_id not in self.conversation_states:
            return {"error": "Conversation not found"}

        # 답변을 외부 저장소에 저장
        current_state = self.conversation_states[thread_id]
        self.external_answers[thread_id] = {
            "answer": answer,
            "timestamp": time.time(),
            "question_id": current_state.current_question_id,
        }

        return {"status": "answer_received", "thread_id": thread_id}

    def register_question_callback(self, thread_id: str, callback_func):
        """질문 전송을 위한 콜백 함수 등록"""
        self.question_callbacks[thread_id] = callback_func

    def get_conversation_state(self, thread_id: str) -> ChatAgentState:
        """특정 대화의 상태 반환"""
        return self.conversation_states.get(thread_id)

    def get_conversation_history(self, thread_id: str) -> list[dict[str, Any]]:
        """특정 대화의 내역 반환"""
        if thread_id in self.conversation_states:
            return self.conversation_states[thread_id].conversation_history
        return []

    def run_conversation(self, thread_id: str) -> ChatAgentState:
        """대화 실행"""
        if thread_id not in self.conversation_states:
            raise ValueError("Conversation not found")

        state = self.conversation_states[thread_id]
        result = self.graph.invoke(state)

        # 결과를 저장소에 업데이트
        self.conversation_states[thread_id] = result

        return result

    def get_current_status(self, thread_id: str) -> dict[str, Any]:
        """현재 상태 반환"""
        if thread_id not in self.conversation_states:
            return {"error": "Conversation not found"}

        state = self.conversation_states[thread_id]
        return {
            "thread_id": state.thread_id,
            "current_question_id": state.current_question_id,
            "total_questions": len(self.questions),
            "progress": f"{state.current_question_id}/{len(self.questions)}",
            "current_status": state.current_status,
            "chatbot_message": state.chatbot_message,
            "chatbot_response": state.chatbot_response,
            "is_completed": state.is_completed,
            "retry_count": state.retry_count,
        }
