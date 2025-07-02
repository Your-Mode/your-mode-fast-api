import re
import json
import time
import os
from openai import OpenAI

if os.getenv("AWS_LAMBDA_FUNCTION_NAME") is None:
    from dotenv import load_dotenv
    load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 여러분이 생성해 둔 Assistant ID
BODY_ASSISTANT_ID = os.getenv("OPENAI_BODY_ASSISTANT_ID")
STYLE_ASSISTANT_ID = os.getenv("OPENAI_STYLE_ASSISTANT_ID")


def _extract_json(raw: str) -> dict:
    """
    raw 에서 ```json ... ``` 블록 안의 순수 JSON만 꺼내서 dict로 반환.
    ```json
    { ... }
    ```
    코드블록이 없으면 raw 전체를 json.loads 시도.
    """
    # 1) ```json … ``` 코드블록 추출
    m = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL)
    json_str = m.group(1) if m else raw
    # 2) 불필요한 ``` 제거 (혹시 raw에만 있을 때)
    json_str = json_str.strip().lstrip("```").rstrip("```").strip()
    # 3) 파싱
    return json.loads(json_str, strict=False)


def diagnose_body_type_with_assistant(
        answers: list[str],
        height: float,
        weight: float,
        gender: str
) -> dict:
    """
    1) 사용자 정보로 prompt 구성
    2) create_and_run 으로 assistant 호출
    3) 폴링하여 run 완료 대기
    4) 마지막 어시스턴트 메시지(raw)에서 JSON 추출 → dict 반환
    """
    prompt = (
            f"제 체형을 진단해 주세요.\n"
            f"- 성별: {gender}\n"
            f"- 키: {height}cm\n"
            f"- 체중: {weight}kg\n"
            f"- 설문 응답:\n"
            + "\n".join(f"{i + 1}. {a}" for i, a in enumerate(answers))
            + "\n\n"
              "체형 진단"
    )

    # 2) create_and_run 호출
    run = client.beta.threads.create_and_run(
        assistant_id=BODY_ASSISTANT_ID,
        thread={"messages": [{"role": "user", "content": prompt}]}
    )
    thread_id = run.thread_id
    run_id = run.id

    # 3) 완료될 때까지 폴링
    while True:
        status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        if status.status == "completed":
            break
        time.sleep(0.3)

    # 4) 메시지 리스트에서 어시스턴트 응답 꺼내기
    msgs = client.beta.threads.messages.list(thread_id=thread_id).data
    raw = msgs[0].content[0].text.value  # 어시스턴트가 첫 번째 메시지로 보낸 응답

    # 5) JSON 부분만 파싱해서 dict 로 반환
    try:
        return _extract_json(raw)
    except Exception as e:
        # 파싱 실패 시 디버그 로그와 함께 예외 올리기
        print("🛠️ [DEBUG] raw from assistant:\n", raw)
        raise ValueError(f"JSON 파싱 실패: {e}")


def create_content(
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
):
    items_section = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(recommendation_items))
    prompt = (
        "다음 정보를 바탕으로 **스타일 추천 콘텐츠 초안**을 작성해줘.\n\n"
        f"- 이름: {name}\n"
        f"- 체형 타입: {body_type}\n"
        f"- 키: {height}cm\n"
        f"- 몸무게: {weight}kg\n"
        f"- 체형 특징: {body_feature}\n"
        "- 추천 아이템:\n"
        f"{items_section}\n\n"
        f"- 입고 싶은 상황: {recommended_situation}\n"
        f"- 추천 스타일: {recommended_style}\n"
        f"- 피하고 싶은 스타일: {avoid_style}\n"
        f"- 예산: {budget}\n\n"
        "↳ 초안 작성."
    )

    run = client.beta.threads.create_and_run(
        assistant_id=STYLE_ASSISTANT_ID,
        thread={"messages": [{"role": "user", "content": prompt}]}
    )
    thread_id = run.thread_id
    run_id = run.id

    while True:
        status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        if status.status == "completed":
            break
        time.sleep(0.3)

    msgs = client.beta.threads.messages.list(thread_id=thread_id).data
    raw = msgs[0].content[0].text.value  # 어시스턴트가 첫 번째 메시지로 보낸 응답

    return raw
