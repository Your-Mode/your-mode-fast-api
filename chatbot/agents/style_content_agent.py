"""
Style Content Agent
스타일 콘텐츠 생성을 담당하는 에이전트
"""

import time

from openai import OpenAI

from chatbot.config import load_config


class StyleContentAgent:
    """스타일 콘텐츠 생성 에이전트"""

    def __init__(self) -> None:
        self.config = load_config()
        self.client = OpenAI(api_key=self.config.get("openai_api_key"))
        self.assistant_id = self.config["assistants"]["style_assistant_id"]

    def create_content(
        self,
        name: str,
        body_type: str,
        height: int,
        weight: int,
        body_feature: str,
        recommendation_items: list[str],
        recommended_situation: str,
        recommended_style: str,
        avoid_style: str,
        budget: str,
    ) -> str:
        """
        스타일 추천 콘텐츠 생성

        Args:
            name: 이름
            body_type: 체형 타입
            height: 키 (cm)
            weight: 몸무게 (kg)
            body_feature: 체형적 특징
            recommendation_items: 추천 받고 싶은 아이템
            recommended_situation: 입고 싶은 상황
            recommended_style: 추천받고 싶은 스타일
            avoid_style: 피하고 싶은 스타일
            budget: 예산

        Returns:
            생성된 콘텐츠 문자열
        """
        prompt = self._build_prompt(
            name=name,
            body_type=body_type,
            height=height,
            weight=weight,
            body_feature=body_feature,
            recommendation_items=recommendation_items,
            recommended_situation=recommended_situation,
            recommended_style=recommended_style,
            avoid_style=avoid_style,
            budget=budget,
        )

        run = self.client.beta.threads.create_and_run(
            assistant_id=self.assistant_id,
            thread={"messages": [{"role": "user", "content": prompt}]},
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
                raise RuntimeError(f"Style content generation failed: {last_error}")
            time.sleep(0.3)

        # 결과 추출
        msgs = self.client.beta.threads.messages.list(thread_id=thread_id).data
        if not msgs:
            raise RuntimeError("No messages found from style assistant")

        # 첫 번째 메시지에서 텍스트 추출
        first_msg = msgs[0]
        if not first_msg.content or getattr(first_msg.content[0], "type", "text") != "text":
            raise RuntimeError("Style assistant message has no text content")

        return first_msg.content[0].text.value

    def _build_prompt(
        self,
        name: str,
        body_type: str,
        height: int,
        weight: int,
        body_feature: str,
        recommendation_items: list[str],
        recommended_situation: str,
        recommended_style: str,
        avoid_style: str,
        budget: str,
    ) -> str:
        """프롬프트 구성"""
        system_prompt = self.config["prompts"]["style_content"]["system"]
        user_template = self.config["prompts"]["style_content"]["user_template"]

        items_section = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(recommendation_items))

        return f"{system_prompt}\n\n{
            user_template.format(
                name=name,
                body_type=body_type,
                height=height,
                weight=weight,
                body_feature=body_feature,
                items_section=items_section,
                recommended_situation=recommended_situation,
                recommended_style=recommended_style,
                avoid_style=avoid_style,
                budget=budget,
            )
        }"
