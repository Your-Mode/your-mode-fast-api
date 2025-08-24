"""
Chat Assistant Agent
채팅 상호작용을 담당하는 에이전트
"""

import contextlib
import json
import time
from typing import Any

from openai import OpenAI

from chatbot.config import load_config


class ChatAssistantAgent:
    """채팅 어시스턴트 에이전트"""

    def __init__(self) -> None:
        self.config = load_config()
        self.client = OpenAI(api_key=self.config.get("openai_api_key"))
        self.assistant_id = self.config["assistants"]["chat_assistant_id"]

    def chat(
        self,
        question: str,
        answer: str,
    ) -> dict[str, Any]:
        """
        채팅 상호작용 처리

        Args:
            question: 질문
            answer: 응답

        Returns:
            채팅 응답 딕셔너리
        """
        prompt = self._build_prompt(question, answer)

        run = self.client.beta.threads.create_and_run(
            assistant_id=self.assistant_id,
            thread={"messages": [{"role": "user", "content": prompt}]},
            response_format={
                "type": "json_schema",
                "json_schema": self.config["json_schemas"]["chat_response"],
            },
        )

        thread_id = run.thread_id
        run_id = run.id

        # 완료 대기
        while True:
            status = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            if status.status == "completed":
                break
            if status.status in {"failed", "cancelled", "expired"}:
                last_error = getattr(status, "last_error", None)
                raise RuntimeError(f"Chat assistant failed: {last_error}")
            time.sleep(0.3)

        # 결과 추출
        msgs = self.client.beta.threads.messages.list(thread_id=thread_id).data
        assistant_msg = next((m for m in msgs if getattr(m, "role", "") == "assistant"), None)
        if assistant_msg is None:
            raise ValueError(self.config["error_messages"]["no_assistant_message"])

        # 텍스트 콘텐츠 추출
        text_parts = [
            p for p in getattr(assistant_msg, "content", []) if getattr(p, "type", "") == "text"
        ]
        if not text_parts:
            raise ValueError(self.config["error_messages"]["no_text_content"])

        text_obj = text_parts[0].text
        raw = (text_obj.value if hasattr(text_obj, "value") else str(text_obj)).strip()

        try:
            data = json.loads(raw)
        except Exception as e:
            raise ValueError(
                self.config["error_messages"]["json_parsing_failed"].format(error=e)
            ) from e

        # null 값 정규화
        if data.get("selected") is None:
            data["selected"] = ""
        if data.get("nextQuestion") is None:
            data["nextQuestion"] = ""

        return data

    def chat_body_result(
        self,
        answers: list[str],
        height: float,
        weight: float,
        gender: str,
    ) -> dict[str, Any]:
        """
        체형 진단 결과를 위한 채팅

        Args:
            answers: 설문 응답 리스트
            height: 키 (cm)
            weight: 체중 (kg)
            gender: 성별

        Returns:
            진단 결과 딕셔너리
        """
        prompt = self._build_body_result_prompt(answers, height, weight, gender)

        run = self.client.beta.threads.create_and_run(
            assistant_id=self.assistant_id,
            thread={"messages": [{"role": "user", "content": prompt}]},
            response_format={
                "type": "json_schema",
                "json_schema": self.config["json_schemas"]["body_diagnosis"],
            },
        )

        thread_id = run.thread_id
        run_id = run.id

        deadline = time.time() + self.config["models"]["timeout_seconds"]

        while True:
            status = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            if status.status == "completed":
                break
            if status.status in {"failed", "cancelled", "expired"}:
                last_error = getattr(status, "last_error", None)
                raise RuntimeError(
                    f"Run ended with status={status.status}, last_error={last_error}"
                )
            if time.time() > deadline:
                raise TimeoutError(self.config["error_messages"]["run_timeout"])
            time.sleep(0.3)

        msgs = self.client.beta.threads.messages.list(thread_id=thread_id).data

        # 최신 assistant 메시지 선택
        assistant_msgs = [m for m in msgs if getattr(m, "role", "") == "assistant"]
        if not assistant_msgs:
            raise ValueError(self.config["error_messages"]["no_assistant_message"])

        # created_at 기준으로 정렬
        with contextlib.suppress(Exception):
            assistant_msgs.sort(key=lambda m: getattr(m, "created_at", 0), reverse=True)

        msg = assistant_msgs[0]

        # 텍스트 콘텐츠 추출
        text_parts = [p for p in getattr(msg, "content", []) if getattr(p, "type", "") == "text"]
        if not text_parts:
            raise ValueError(self.config["error_messages"]["no_text_content"])

        raw = text_parts[0].text.value.strip()

        try:
            return json.loads(raw)
        except Exception as e:
            print("🛠️ [DEBUG] raw from assistant:\n", raw)
            raise ValueError(
                self.config["error_messages"]["json_parsing_failed"].format(error=e)
            ) from e

    def _build_prompt(self, question: str, answer: str) -> str:
        """프롬프트 구성"""
        system_prompt = self.config["prompts"]["chat_assistant"]["system"]
        user_template = self.config["prompts"]["chat_assistant"]["user_template"]

        return f"{system_prompt}\n\n{user_template.format(question=question, answer=answer)}"

    def _build_body_result_prompt(
        self, answers: list[str], height: float, weight: float, gender: str
    ) -> str:
        """체형 진단 결과 프롬프트 구성"""
        return (
            f"다음 응답 내용을 바탕으로 골격 진단 결과를 알려줘\n"
            f"- 성별: {gender}\n"
            f"- 키: {height}cm\n"
            f"- 체중: {weight}kg\n"
            f"- 설문 응답:\n" + "\n".join(f"{i + 1}. {a}" for i, a in enumerate(answers)) + "\n\n"
            "체형 진단"
        )
