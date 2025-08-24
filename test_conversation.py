#!/usr/bin/env python3
"""
Conversation Graph Agent Test Script
대화 그래프 에이전트 테스트 스크립트
"""

from chatbot.agents.conversation_graph import ConversationGraphAgent


def test_conversation_flow():
    """대화 플로우 테스트"""
    print("=== 대화 그래프 에이전트 테스트 ===\n")

    # 에이전트 초기화
    agent = ConversationGraphAgent()

    # 대화 시작
    print("1. 대화 시작")
    state = agent.start_conversation()
    print(f"   세션 상태: {state['current_status']}")
    print(f"   첫 번째 질문: {state['next_question']['question']}")
    print(f"   도움말: {state['next_question']['help_text']}")
    print()

    # 첫 번째 답변 (유효한 답변)
    print("2. 첫 번째 답변 제출 (유효한 답변)")
    print("   답변: 175")
    state = agent.submit_answer(state, "175")
    current_status = agent.get_current_status(state)
    print(f"   상태: {current_status['current_status']}")
    print(f"   진행률: {current_status['progress']}")
    print(f"   다음 질문: {current_status['next_question']['question']}")
    print()

    # 두 번째 답변 (유효한 답변)
    print("3. 두 번째 답변 제출 (유효한 답변)")
    print("   답변: 남성")
    state = agent.submit_answer(state, "남성")
    current_status = agent.get_current_status(state)
    print(f"   상태: {current_status['current_status']}")
    print(f"   진행률: {current_status['progress']}")
    print(f"   다음 질문: {current_status['next_question']['question']}")
    print()

    # 세 번째 답변 (유효한 답변)
    print("4. 세 번째 답변 제출 (유효한 답변)")
    print("   답변: 70")
    state = agent.submit_answer(state, "70")
    current_status = agent.get_current_status(state)
    print(f"   상태: {current_status['current_status']}")
    print(f"   진행률: {current_status['progress']}")
    print(f"   완료 여부: {current_status['is_completed']}")
    print(f"   수집된 답변: {current_status['answers']}")
    print()

    print("=== 모든 질문 완료! ===")


def test_validation_errors():
    """검증 에러 테스트"""
    print("\n=== 검증 에러 테스트 ===\n")

    agent = ConversationGraphAgent()
    state = agent.start_conversation()

    # 첫 번째 질문에 잘못된 답변
    print("1. 잘못된 답변 테스트 (범위 초과)")
    print("   질문: 키는 얼마인가요? (cm)")
    print("   답변: 300")
    state = agent.submit_answer(state, "300")
    current_status = agent.get_current_status(state)
    print(f"   상태: {current_status['current_status']}")
    print(f"   에러 메시지: {current_status['error_message']}")
    print(f"   재질문: {current_status['next_question']['question']}")
    print()

    # 올바른 답변으로 수정
    print("2. 올바른 답변으로 수정")
    print("   답변: 180")
    state = agent.submit_answer(state, "180")
    current_status = agent.get_current_status(state)
    print(f"   상태: {current_status['current_status']}")
    print(f"   진행률: {current_status['progress']}")
    print()


def test_custom_questions():
    """커스텀 질문 테스트"""
    print("\n=== 커스텀 질문 테스트 ===\n")

    custom_questions = [
        {
            "id": 1,
            "question": "나이는 몇 살인가요?",
            "validation": {
                "type": "numeric_range",
                "min": 10,
                "max": 100,
                "error_message": "나이는 10세에서 100세 사이여야 합니다.",
            },
            "help_text": "예: 25, 30",
        },
        {
            "id": 2,
            "question": "직업은 무엇인가요?",
            "validation": {
                "type": "choice",
                "options": ["학생", "회사원", "자영업자", "기타"],
                "error_message": "제시된 옵션 중에서 선택해주세요.",
            },
            "help_text": "학생, 회사원, 자영업자, 기타 중 선택",
        },
    ]

    agent = ConversationGraphAgent()
    state = agent.start_conversation({"questions": custom_questions})

    print("1. 커스텀 질문으로 대화 시작")
    current_status = agent.get_current_status(state)
    print(f"   첫 번째 질문: {current_status['next_question']['question']}")
    print(f"   도움말: {current_status['next_question']['help_text']}")
    print()

    # 답변 제출
    print("2. 답변 제출")
    print("   답변: 25")
    state = agent.submit_answer(state, "25")
    current_status = agent.get_current_status(state)
    print(f"   상태: {current_status['current_status']}")
    print(f"   다음 질문: {current_status['next_question']['question']}")
    print()


if __name__ == "__main__":
    # 기본 대화 플로우 테스트
    test_conversation_flow()

    # 검증 에러 테스트
    test_validation_errors()

    # 커스텀 질문 테스트
    test_custom_questions()

    print("\n=== 모든 테스트 완료 ===")
