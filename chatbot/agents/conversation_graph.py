import time
from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from chatbot.config.chatbot_config import config


class ConversationState(TypedDict):
    current_question_id: int
    questions: list[dict[str, Any]]
    user_answers: dict[int, str]
    validation_results: dict[int, dict[str, Any]]
    conversation_history: list[dict[str, Any]]
    current_status: str
    error_message: str
    next_question: dict[str, Any]
    is_completed: bool
    retry_count: dict[int, int]


class ConversationGraphAgent:
    """LangGraph를 사용한 대화 그래프 에이전트"""

    def __init__(self) -> None:
        self.questions = config.body_diagnosis_config.questions
        self.graph = self._build_graph()
        self.memory = MemorySaver()

    def _build_graph(self) -> StateGraph:
        """대화 그래프 구성"""
        workflow = StateGraph(ConversationState)

        # 노드 추가
        workflow.add_node("ask_question", self._ask_question)
        workflow.add_node("validate_answer", self._validate_answer)
        workflow.add_node("handle_error", self._handle_error)
        workflow.add_node("save_answer", self._save_answer)
        workflow.add_node("check_completion", self._check_completion)

        # 엣지 연결
        workflow.set_entry_point("ask_question")

        workflow.add_edge("ask_question", "validate_answer")
        workflow.add_conditional_edges(
            "validate_answer",
            self._route_after_validation,
            {"valid": "save_answer", "invalid": "handle_error", "completed": END},
        )
        workflow.add_edge("handle_error", "ask_question")
        workflow.add_edge("save_answer", "check_completion")
        workflow.add_conditional_edges(
            "check_completion",
            self._route_after_save,
            {"continue": "ask_question", "completed": END},
        )

        return workflow.compile(checkpointer=self.memory)

    def _ask_question(self, state: ConversationState) -> ConversationState:
        """질문 제시"""
        current_id = state["current_question_id"]
        question = next((q for q in state["questions"] if q["id"] == current_id), None)

        if question:
            state["next_question"] = question
            state["current_status"] = "asking"
            state["error_message"] = ""
        else:
            state["is_completed"] = True
            state["current_status"] = "completed"

        return state

    def _validate_answer(self, state: ConversationState) -> ConversationState:
        """답변 검증"""
        current_id = state["current_question_id"]
        question = next((q for q in state["questions"] if q["id"] == current_id), None)

        if not question:
            state["current_status"] = "completed"
            return state

        # 사용자 답변 가져오기 (실제 구현에서는 외부에서 주입)
        user_answer = state.get("user_answers", {}).get(current_id, "")

        if not user_answer:
            state["current_status"] = "waiting_answer"
            return state

        # 검증 수행
        validation_result = self._perform_validation(user_answer, question["validation"])

        if validation_result["valid"]:
            state["current_status"] = "valid"
            state["validation_results"][current_id] = validation_result
        else:
            state["current_status"] = "invalid"
            state["error_message"] = validation_result["error_message"]

        return state

    def _perform_validation(self, answer: str, rules: dict[str, Any]) -> dict[str, Any]:
        """답변 검증 로직"""
        validation_type = rules["type"]

        if validation_type == "numeric_range":
            try:
                value = float(answer)
                min_val = rules["min"]
                max_val = rules["max"]

                if min_val <= value <= max_val:
                    return {
                        "valid": True,
                        "normalized_value": value,
                        "error_message": "",
                    }
                else:
                    return {"valid": False, "error_message": rules["error_message"]}
            except ValueError:
                return {"valid": False, "error_message": "숫자를 입력해주세요."}

        elif validation_type == "choice":
            if answer in rules["options"]:
                return {"valid": True, "normalized_value": answer, "error_message": ""}
            else:
                return {"valid": False, "error_message": rules["error_message"]}

        return {"valid": True, "normalized_value": answer, "error_message": ""}

    def _generate_help_message(self, question: dict[str, Any], user_answer: str) -> str:
        """사용자 답변을 분석하여 도움말 생성"""
        validation_type = question["validation"]["type"]
        retry_count = question.get("retry_count", 0)

        # 기본 도움말
        base_help = question.get("help_text", "")

        if validation_type == "numeric_range":
            min_val = question["validation"]["min"]
            max_val = question["validation"]["max"]

            if retry_count == 1:
                return f"{base_help}\n💡 힌트: {min_val}에서 {max_val} 사이의 숫자를 입력해주세요."
            elif retry_count == 2:
                return f"{base_help}\n💡 구체적 예시: {min_val + (max_val - min_val) // 2}와 같은 숫자를 입력해보세요."
            else:
                return f"{base_help}\n💡 자세한 설명: {question['question']}에 대한 답변은 {min_val}에서 {max_val} 사이의 숫자여야 합니다."

        elif validation_type == "choice":
            options = question["validation"]["options"]

            if retry_count == 1:
                return f"{base_help}\n💡 힌트: 다음 중에서 선택해주세요: {', '.join(options)}"
            elif retry_count == 2:
                return f"{base_help}\n💡 구체적 예시: '{options[0]}' 또는 '{options[1]}' 중 하나를 입력해보세요."
            else:
                return f"{base_help}\n💡 자세한 설명: 정확히 '{' 또는 '.join(options)}' 중 하나를 입력해야 합니다."

        # 일반적인 경우
        if retry_count == 1:
            return f"{base_help}\n💡 힌트: 질문을 다시 한 번 읽어보세요."
        elif retry_count == 2:
            return f"{base_help}\n💡 구체적 예시: {base_help}에 나와있는 형식으로 답변해보세요."
        else:
            return f"{base_help}\n💡 자세한 설명: {question['question']}에 대한 답변을 정확히 입력해주세요."

    def _handle_error(self, state: ConversationState) -> ConversationState:
        """에러 처리 및 재질문 (도움말 포함)"""
        current_id = state["current_question_id"]
        question = next((q for q in state["questions"] if q["id"] == current_id), None)

        # 에러 분석 및 도움말 생성
        help_message = self._generate_help_message(
            question, state.get("user_answers", {}).get(current_id, "")
        )

        # 질문에 도움말 추가
        enhanced_question = question.copy()
        enhanced_question["help_message"] = help_message
        enhanced_question["retry_count"] = state.get("retry_count", {}).get(current_id, 0) + 1

        # 재시도 횟수 업데이트
        if "retry_count" not in state:
            state["retry_count"] = {}
        state["retry_count"][current_id] = enhanced_question["retry_count"]

        # 에러 메시지와 함께 같은 질문 다시 제시
        state["next_question"] = enhanced_question
        state["current_status"] = "retry"

        # 대화 히스토리에 에러 기록
        state["conversation_history"].append(
            {
                "type": "error",
                "question_id": current_id,
                "error": state["error_message"],
                "help_message": help_message,
                "retry_count": enhanced_question["retry_count"],
                "timestamp": time.time(),
            }
        )

        return state

    def _save_answer(self, state: ConversationState) -> ConversationState:
        """유효한 답변 저장"""
        current_id = state["current_question_id"]
        validation_result = state["validation_results"][current_id]

        # 답변 저장
        state["user_answers"][current_id] = validation_result["normalized_value"]

        # 대화 히스토리에 성공 기록
        state["conversation_history"].append(
            {
                "type": "success",
                "question_id": current_id,
                "answer": validation_result["normalized_value"],
                "timestamp": time.time(),
            }
        )

        return state

    def _check_completion(self, state: ConversationState) -> ConversationState:
        """완료 여부 확인"""
        current_id = state["current_question_id"]

        if current_id >= len(state["questions"]):
            state["is_completed"] = True
            state["current_status"] = "completed"
            return state

        # 다음 질문으로 이동
        state["current_question_id"] = current_id + 1
        state["current_status"] = "continue"

        return state

    def _route_after_validation(self, state: ConversationState) -> str:
        """검증 후 라우팅"""
        if state["current_status"] == "completed":
            return "completed"
        elif state["current_status"] == "valid":
            return "valid"
        else:
            return "invalid"

    def _route_after_save(self, state: ConversationState) -> str:
        """저장 후 라우팅"""
        if state["is_completed"]:
            return "completed"
        else:
            return "continue"

    def start_conversation(self, config: dict[str, Any] = None) -> ConversationState:
        """대화 시작"""
        initial_state = ConversationState(
            current_question_id=1,
            questions=self.questions,
            user_answers={},
            validation_results={},
            conversation_history=[],
            current_status="starting",
            error_message="",
            next_question={},
            is_completed=False,
            retry_count={},
        )

        if config:
            initial_state.update(config)

        return initial_state

    def submit_answer(self, state: ConversationState, answer: str) -> ConversationState:
        """답변 제출"""
        current_id = state["current_question_id"]
        state["user_answers"][current_id] = answer

        # 그래프 실행
        result = self.graph.invoke(state)
        return result

    def get_current_status(self, state: ConversationState) -> dict[str, Any]:
        """현재 상태 반환"""
        return {
            "current_question_id": state["current_question_id"],
            "total_questions": len(state["questions"]),
            "progress": f"{state['current_question_id']}/{len(state['questions'])}",
            "current_status": state["current_status"],
            "next_question": state.get("next_question", {}),
            "error_message": state.get("error_message", ""),
            "is_completed": state["is_completed"],
            "answers": state["user_answers"],
        }
