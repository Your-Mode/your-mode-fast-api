import re
import json
import time
import os
from openai import OpenAI
from typing import Any, Dict, Optional

if os.getenv("AWS_LAMBDA_FUNCTION_NAME") is None:
    from dotenv import load_dotenv

    load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BODY_ASSISTANT_ID = os.getenv("OPENAI_BODY_ASSISTANT_ID")
STYLE_ASSISTANT_ID = os.getenv("OPENAI_STYLE_ASSISTANT_ID")
CHAT_ASSISTANT_ID = os.getenv("OPENAI_CHAT_ASSISTANT_ID")
SOFT_WAIT_SEC = 25  # API GW(29~30s)보다 짧게


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


RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "body_type": {"type": "string"},
        "type_description": {"type": "string"},
        "detailed_features": {"type": "string"},
        "attraction_points": {"type": "string"},
        "recommended_styles": {"type": "string"},
        "avoid_styles": {"type": "string"},
        "styling_fixes": {"type": "string"},
        "styling_tips": {"type": "string"},
    },
    "required": [
        "body_type",
        "type_description",
        "detailed_features",
        "attraction_points",
        "recommended_styles",
        "avoid_styles",
        "styling_fixes",
        "styling_tips",
    ],
    "additionalProperties": False,
}

def _build_prompt(answers: list[str], height: float, weight: float, gender: str) -> str:
    return (
        "당신은 골격 진단 및 패션 스타일리스트입니다.\n"
        "아래 사용자 정보를 바탕으로 체형을 진단하고, 반드시 JSON으로만 응답하세요.\n"
        "출력은 다음 스키마의 각 필드를 한국어로 충실히 채우세요. 모든 값은 문자열입니다.\n"
        "필드: body_type, type_description, detailed_features, attraction_points, "
        "recommended_styles, avoid_styles, styling_fixes, styling_tips\n\n"
        f"- 성별: {gender}\n"
        f"- 키: {height}cm\n"
        f"- 체중: {weight}kg\n"
        "- 설문 응답:\n"
        + "\n".join(f"{i+1}. {a}" for i, a in enumerate(answers))
        + "\n\n주의: 코드블록 없이 순수 JSON만 출력하세요."
    )

# ---------- 안전한 메시지 텍스트 추출기 ----------
def _as_dict(obj):
    try:
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
    except Exception:
        pass
    return obj if isinstance(obj, dict) else json.loads(json.dumps(obj, default=str))

def _extract_first_text_from_content_items(items):
    for item in items or []:
        d = _as_dict(item)
        itype = d.get("type")

        # 중첩 content(tool_result 등)
        if isinstance(d.get("content"), list):
            inner = _extract_first_text_from_content_items(d["content"])
            if inner:
                return inner

        if itype in ("output_text", "text", "input_text"):
            t = d.get("text")
            if isinstance(t, str):
                return t
            if isinstance(t, dict) and isinstance(t.get("value"), str):
                return t["value"]

        for key in ("output_text", "value"):
            if isinstance(d.get(key), str):
                return d[key]
    return None

def _extract_first_text_from_message(msg):
    m = _as_dict(msg)
    for key in ("text", "output_text"):
        v = m.get(key)
        if isinstance(v, str):
            return v
        if isinstance(v, dict) and isinstance(v.get("value"), str):
            return v["value"]
    content = m.get("content") or []
    if isinstance(content, list):
        return _extract_first_text_from_content_items(content)
    return None

def diagnose_body_type_with_assistant(
    answers: list[str],
    height: float,
    weight: float,
    gender: str,
    *,
    timeout_sec: int = 60,
) -> Dict[str, Any]:
    """
    1) 사용자 정보로 prompt 구성
    2) create_and_run 으로 assistant 호출 (JSON 스키마 강제)
    3) 폴링하여 run 완료 대기(타임아웃/에러 처리)
    4) 마지막 어시스턴트 메시지(raw)에서 JSON 파싱 → dict 반환
    """
    prompt = _build_prompt(answers, height, weight, gender)

    run = client.beta.threads.create_and_run(
        assistant_id=BODY_ASSISTANT_ID,
        thread={"messages": [{"role": "user", "content": prompt}]},
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "BodyDiagnosisResult",
                "strict": True,
                "schema": RESULT_SCHEMA,
            },
        },
    )

    thread_id = run.thread_id
    run_id = run.id

    # 상태 폴링 (에러/타임아웃 처리)
    deadline = time.time() + timeout_sec
    while True:
        status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if status.status == "completed":
            break
        if status.status in {"failed", "cancelled", "expired"}:
            raise RuntimeError(
                f"Assistants run ended with status={status.status}, "
                f"last_error={getattr(status, 'last_error', None)}"
            )
        if time.time() > deadline:
            raise TimeoutError("Assistants run timed out")
        time.sleep(0.3)

    # 최신 assistant 메시지 안전 추출
    # (일반적으로 list()는 최신이 앞에 오지만, role/시간 기준으로 한 번 더 필터)
    messages = client.beta.threads.messages.list(thread_id=thread_id).data
    assistant_msgs = [m for m in messages if getattr(m, "role", "") == "assistant"]
    if not assistant_msgs:
        raise ValueError("No assistant message found")

    # created_at이 있다면 최신 정렬, 없다면 그대로 첫 번째 사용
    try:
        assistant_msgs.sort(key=lambda m: getattr(m, "created_at", 0), reverse=True)
    except Exception:
        pass

    first = assistant_msgs[0]
    if not first.content or getattr(first.content[0], "type", "text") != "text":
        # 도구 호출 등 다른 타입이 섞였을 가능성 방어
        raise ValueError(f"Unexpected message content type: {getattr(first.content[0], 'type', 'unknown')}")

    raw = first.content[0].text.value.strip()

    try:
        # strict json_schema 덕분에 대부분 안전하지만, 혹시 모를 포맷 이슈 방어
        return json.loads(raw)
    except Exception as e:
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


def chat_body_assistant(question: str, answer: str):
    schema = {
        "type": "object",
        "properties": {
            "isSuccess": {"type": "boolean"},
            "selected": {"type": ["string", "null"]},
            "message": {"type": "string"},
            "nextQuestion": {"type": ["string", "null"]},
        },
        # ← 키는 모두 존재해야 함(값은 string 또는 null 허용)
        "required": ["isSuccess", "selected", "message", "nextQuestion"],
        "additionalProperties": False,
    }

    prompt = (
        f"{question}에 대한 응답입니다.\n"
        f"- 응답: {answer}\n"
        "응답을 위 JSON 형식에 맞춰서만 반환하세요."
    )

    run = client.beta.threads.create_and_run(
        assistant_id=CHAT_ASSISTANT_ID,
        thread={"messages": [{"role": "user", "content": prompt}]},
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "BodyQuestionAnswer",
                "strict": True,  # ← 엄격 모드 유지
                "schema": schema,
            },
        },
    )

    thread_id = run.thread_id
    run_id = run.id

    while True:
        status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if status.status == "completed":
            break
        time.sleep(0.3)

    msgs = client.beta.threads.messages.list(thread_id=thread_id).data
    assistant_msg = next((m for m in msgs if getattr(m, "role", "") == "assistant"), None)
    if assistant_msg is None:
        raise ValueError("No assistant message found")

    parts = [p for p in getattr(assistant_msg, "content", []) if getattr(p, "type", "") == "text"]
    if not parts:
        raise ValueError("Assistant message has no text content")

    text_obj = parts[0].text
    raw = (text_obj.value if hasattr(text_obj, "value") else str(text_obj)).strip()

    data = json.loads(raw)

    # (선택) 서버에서 일관 포맷으로 정규화: null -> ""
    #  - FastAPI response_model이 selected/nextQuestion를 str로 요구한다면 필수
    #  - optional로 둘 거면 이 블록은 생략해도 됨
    if data.get("selected") is None:
        data["selected"] = ""
    if data.get("nextQuestion") is None:
        data["nextQuestion"] = ""

    return data


def chat_body_result(
        answers: list[str],
        height: float,
        weight: float,
        gender: str
):
    schema = {
        "type": "object",
        "properties": {
            "body_type": {"type": "string"},
            "type_description": {"type": "string"},
            "detailed_features": {"type": "string"},
            "attraction_points": {"type": "string"},
            "recommended_styles": {"type": "string"},
            "avoid_styles": {"type": "string"},
            "styling_fixes": {"type": "string"},
            "styling_tips": {"type": "string"}
        },
        "required": [
            "body_type",
            "type_description",
            "detailed_features",
            "attraction_points",
            "recommended_styles",
            "avoid_styles",
            "styling_fixes",
            "styling_tips"
        ],
        "additionalProperties": False
    }

    prompt = (
            f"다음 응답 내용을 바탕으로 골격 진단 결과를 알려줘\n"
            f"- 성별: {gender}\n"
            f"- 키: {height}cm\n"
            f"- 체중: {weight}kg\n"
            f"- 설문 응답:\n"
            + "\n".join(f"{i + 1}. {a}" for i, a in enumerate(answers))
            + "\n\n"
              "체형 진단"
    )

    run = client.beta.threads.create_and_run(
        assistant_id=CHAT_ASSISTANT_ID,
        thread={"messages": [{"role": "user", "content": prompt}]},
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "BodyDiagnosisResult",
                "strict": True,
                "schema": schema
            }
        },
    )

    thread_id = run.thread_id
    run_id = run.id

    deadline = time.time() + 60

    while True:
        status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if status.status == "completed":
            break
        if status.status in {"failed", "cancelled", "expired"}:
            raise RuntimeError(
                f"Run ended with status={status.status}, last_error={getattr(status, 'last_error', None)}")
        if time.time() > deadline:
            raise TimeoutError("Assistants run timed out")
        time.sleep(0.3)

    msgs = client.beta.threads.messages.list(thread_id=thread_id).data

    # 최신 assistant 메시지 선택 (created_at 기준 내림차순)
    assistant_msgs = [m for m in msgs if getattr(m, "role", "") == "assistant"]
    if not assistant_msgs:
        raise ValueError("No assistant message found")
    assistant_msgs.sort(key=lambda m: getattr(m, "created_at", 0), reverse=True)
    msg = assistant_msgs[0]

    # content 에서 text 파트만 안전하게 추출
    text_parts = [p for p in getattr(msg, "content", []) if getattr(p, "type", "") == "text"]
    if not text_parts:
        raise ValueError("Assistant message has no text content")

    raw = text_parts[0].text.value.strip()

    # JSON 파싱 후 반환 (여기서 반드시 dict를 return)
    try:
        data = json.loads(raw)
    except Exception as e:
        print("🛠️ [DEBUG] raw from assistant:\n", raw)
        raise ValueError(f"JSON 파싱 실패: {e}")

    return data

def chat_body_result_soft(
    answers: list[str],
    height: float,
    weight: float,
    gender: str,
) -> Dict[str, Any]:
    """
    1) 최대 SOFT_WAIT_SEC 동안만 동기 대기
    2) 완료되면 결과 JSON(dict) 반환
    3) 미완료면 {"thread_id","run_id","status"} 반환(컨트롤러에서 202로 내려주기)
    """
    prompt = _build_prompt(answers, height, weight, gender)

    run = client.beta.threads.create_and_run(
        assistant_id=BODY_ASSISTANT_ID,
        thread={"messages": [{"role": "user", "content": prompt}]},
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "BodyDiagnosisResult",
                "strict": True,
                "schema": RESULT_SCHEMA,
            },
        },
    )

    thread_id = run.thread_id
    run_id = run.id

    # 소프트 대기
    deadline = time.time() + SOFT_WAIT_SEC
    status = run.status
    while time.time() < deadline:
        st = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        status = st.status
        if status == "completed":
            break
        if status in {"failed", "cancelled", "expired"}:
            last_err = getattr(st, "last_error", None)
            raise RuntimeError(f"assistants run {status}: {last_err}")
        time.sleep(0.3)

    if status == "completed":
        # 결과 바로 파싱해서 반환
        msgs = client.beta.threads.messages.list(thread_id=thread_id, order="desc", limit=20).data
        raw: Optional[str] = None
        for m in msgs:
            if getattr(m, "role", "") != "assistant":
                continue
            raw = _extract_first_text_from_message(m)
            if raw:
                break
        if not raw:
            raise RuntimeError("assistant message has no extractable text")

        data = json.loads(raw.strip())

        # 필드 정규화(혹시 None/누락 방어)
        for k in ("body_type","type_description","detailed_features","attraction_points",
                  "recommended_styles","avoid_styles","styling_fixes","styling_tips"):
            if data.get(k) is None:
                data[k] = ""
        return data

    # 미완료면 run 식별자 반환 (컨트롤러가 202로 내려줌)
    return {"thread_id": thread_id, "run_id": run_id, "status": status}

def get_run_status(thread_id: str, run_id: str) -> Dict[str, Any]:
    st = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
    return {"status": st.status, "last_error": getattr(st, "last_error", None)}

def get_run_result(thread_id: str, run_id: str) -> Dict[str, Any]:
    st = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
    if st.status != "completed":
        # 컨트롤러에서 425로 매핑하기 좋게 상태만 던짐
        return {"status": st.status}

    msgs = client.beta.threads.messages.list(thread_id=thread_id, order="desc", limit=20).data
    raw: Optional[str] = None
    for m in msgs:
        if getattr(m, "role", "") != "assistant":
            continue
        raw = _extract_first_text_from_message(m)
        if raw:
            break
    if not raw:
        raise RuntimeError("assistant message has no extractable text")

    data = json.loads(raw.strip())
    for k in ("body_type","type_description","detailed_features","attraction_points",
              "recommended_styles","avoid_styles","styling_fixes","styling_tips"):
        if data.get(k) is None:
            data[k] = ""
    data["status"] = "completed"
    return data

