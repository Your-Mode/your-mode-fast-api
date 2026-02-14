"""
Body Diagnosis Agent
체형 진단을 담당하는 에이전트
"""

import contextlib
import json
import time
from typing import Any, Optional

from openai import OpenAI

from chatbot.config import load_config


class BodyDiagnosisAgent:
    """체형 진단 에이전트"""

    def __init__(self) -> None:
        self.config = load_config()
        self.client = OpenAI(api_key=self.config.get("openai_api_key"))
        self.assistant_id = self.config["assistants"]["body_assistant_id"]
        self.timeout = self.config["models"]["timeout_seconds"]
        self.soft_wait = self.config["models"]["soft_wait_seconds"]

    def diagnose(
        self,
        answers: list[str],
        height: float,
        weight: float,
        gender: str,
        *,
        timeout_sec: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        체형 진단 수행

        Args:
            answers: 설문 응답 리스트
            height: 키 (cm)
            weight: 체중 (kg)
            gender: 성별
            timeout_sec: 타임아웃 시간 (초)

        Returns:
            진단 결과 딕셔너리
        """
        timeout = timeout_sec or self.timeout
        prompt = self._build_prompt(answers, height, weight, gender)

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

        # 상태 폴링 (에러/타임아웃 처리)
        deadline = time.time() + timeout
        while True:
            status = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            if status.status == "completed":
                break
            if status.status in {"failed", "cancelled", "expired"}:
                raise RuntimeError(
                    f"Assistants run ended with status={status.status}, "
                    f"last_error={getattr(status, 'last_error', None)}"
                )
            if time.time() > deadline:
                raise TimeoutError(self.config["error_messages"]["run_timeout"])
            time.sleep(0.3)

        # 최신 assistant 메시지 추출
        messages = self.client.beta.threads.messages.list(thread_id=thread_id).data
        assistant_msgs = [m for m in messages if getattr(m, "role", "") == "assistant"]
        if not assistant_msgs:
            raise ValueError(self.config["error_messages"]["no_assistant_message"])

        # created_at 기준으로 최신 정렬
        with contextlib.suppress(Exception):
            assistant_msgs.sort(key=lambda m: getattr(m, "created_at", 0), reverse=True)

        first = assistant_msgs[0]
        if not first.content or getattr(first.content[0], "type", "text") != "text":
            content_type = getattr(first.content[0], "type", "unknown")
            raise ValueError(f"Unexpected message content type: {content_type}")

        raw = first.content[0].text.value.strip()

        try:
            return json.loads(raw)
        except Exception as e:
            print("🛠️ [DEBUG] raw from assistant:\n", raw)
            raise ValueError(
                self.config["error_messages"]["json_parsing_failed"].format(error=e)
            ) from e

    def diagnose_soft(
        self,
        answers: list[str],
        height: float,
        weight: float,
        gender: str,
    ) -> dict[str, Any]:
        """
        소프트 체형 진단 (비동기 대기)

        Args:
            answers: 설문 응답 리스트
            height: 키 (cm)
            weight: 체중 (kg)
            gender: 성별

        Returns:
            완료시: 진단 결과 딕셔너리
            미완료시: {"thread_id", "run_id", "status"}
        """
        prompt = self._build_prompt(answers, height, weight, gender)

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

        # 소프트 대기
        deadline = time.time() + self.soft_wait
        status = run.status
        while time.time() < deadline:
            st = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            status = st.status
            if status == "completed":
                break
            if status in {"failed", "cancelled", "expired"}:
                last_err = getattr(st, "last_error", None)
                raise RuntimeError(f"assistants run {status}: {last_err}")
            time.sleep(0.3)

        if status == "completed":
            # 결과 파싱해서 반환
            msgs = self.client.beta.threads.messages.list(
                thread_id=thread_id, order="desc", limit=20
            ).data
            raw: Optional[str] = None
            for m in msgs:
                if getattr(m, "role", "") != "assistant":
                    continue
                raw = self._extract_text_from_message(m)
                if raw:
                    break
            if not raw:
                raise RuntimeError("assistant message has no extractable text")

            data = json.loads(raw.strip())

            # 필드 정규화
            for k in (
                "body_type",
                "type_description",
                "detailed_features",
                "attraction_points",
                "recommended_styles",
                "avoid_styles",
                "styling_fixes",
                "styling_tips",
            ):
                if data.get(k) is None:
                    data[k] = ""
            return data

        # 미완료시 run 식별자 반환
        return {"thread_id": thread_id, "run_id": run_id, "status": status}

    def get_run_status(self, thread_id: str, run_id: str) -> dict[str, Any]:
        """Run 상태 조회"""
        st = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        return {"status": st.status, "last_error": getattr(st, "last_error", None)}

    def get_run_result(self, thread_id: str, run_id: str) -> dict[str, Any]:
        """Run 결과 조회"""
        st = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if st.status != "completed":
            return {"status": st.status}

        msgs = self.client.beta.threads.messages.list(
            thread_id=thread_id, order="desc", limit=20
        ).data
        raw: Optional[str] = None
        for m in msgs:
            if getattr(m, "role", "") != "assistant":
                continue
            raw = self._extract_text_from_message(m)
            if raw:
                break
        if not raw:
            raise RuntimeError("assistant message has no extractable text")

        data = json.loads(raw.strip())
        for k in (
            "body_type",
            "type_description",
            "detailed_features",
            "attraction_points",
            "recommended_styles",
            "avoid_styles",
            "styling_fixes",
            "styling_tips",
        ):
            if data.get(k) is None:
                data[k] = ""
        data["status"] = "completed"
        return data

    def _build_prompt(self, answers: list[str], height: float, weight: float, gender: str) -> str:
        """프롬프트 구성"""
        system_prompt = self.config["prompts"]["body_diagnosis"]["system"]
        user_template = self.config["prompts"]["body_diagnosis"]["user_template"]

        answers_formatted = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(answers))

        return f"{system_prompt}\n\n{
            user_template.format(
                gender=gender,
                height=height,
                weight=weight,
                answers_formatted=answers_formatted,
            )
        }"

    def _extract_text_from_message(self, msg: Any) -> Optional[str]:
        """메시지에서 텍스트 추출"""
        try:
            if hasattr(msg, "content") and msg.content:
                for content_item in msg.content:
                    if getattr(content_item, "type", "") == "text":
                        return content_item.text.value.strip()
        except Exception:
            pass
        return None
