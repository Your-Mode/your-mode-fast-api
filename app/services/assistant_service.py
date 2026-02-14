import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI

if os.getenv("AWS_LAMBDA_FUNCTION_NAME") is None:
    from dotenv import load_dotenv

    load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Responses API is model-first. Keep old env vars as optional fallbacks.
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
BODY_MODEL = os.getenv("OPENAI_BODY_MODEL", DEFAULT_MODEL)
STYLE_MODEL = os.getenv("OPENAI_STYLE_MODEL", DEFAULT_MODEL)
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", DEFAULT_MODEL)

SOFT_WAIT_SEC = 25  # API GW(29~30s)보다 짧게
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _extract_json(raw: str) -> dict:
    m = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL)
    json_str = m.group(1) if m else raw
    json_str = json_str.strip().lstrip("```").rstrip("```").strip()
    return json.loads(json_str, strict=False)


def _response_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    data = response.model_dump() if hasattr(response, "model_dump") else response
    for item in data.get("output", []) if isinstance(data, dict) else []:
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                return content["text"].strip()
    raise ValueError("response has no extractable text")


def _load_instructions(filename: str) -> str:
    path = PROMPTS_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return f.read().strip()


CHAT_INSTRUCTIONS = _load_instructions("body_chat_instructions.txt")
RESULT_INSTRUCTIONS = _load_instructions("body_result_instructions.txt")


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
        + "\n".join(f"{i + 1}. {a}" for i, a in enumerate(answers))
        + "\n\n주의: 코드블록 없이 순수 JSON만 출력하세요."
    )


def _json_schema_text_format(name: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": name,
            "strict": True,
            "schema": schema,
        }
    }


def diagnose_body_type_with_assistant(
    answers: list[str],
    height: float,
    weight: float,
    gender: str,
    *,
    timeout_sec: int = 60,
) -> Dict[str, Any]:
    prompt = _build_prompt(answers, height, weight, gender)

    res = client.responses.create(
        model=BODY_MODEL,
        instructions=RESULT_INSTRUCTIONS,
        input=prompt,
        text=_json_schema_text_format("BodyDiagnosisResult", RESULT_SCHEMA),
        timeout=timeout_sec,
    )

    raw = _response_text(res)
    try:
        return _extract_json(raw)
    except Exception as e:
        print("[DEBUG] raw from response:\n", raw)
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
        "다음 정보를 바탕으로 스타일 추천 콘텐츠 초안을 작성해줘.\n\n"
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
        "초안 작성."
    )

    res = client.responses.create(model=STYLE_MODEL, input=prompt)
    return _response_text(res)


def chat_body_assistant(question: str, answer: str):
    schema = {
        "type": "object",
        "properties": {
            "isSuccess": {"type": "boolean"},
            "selected": {"type": ["string", "null"]},
            "message": {"type": "string"},
            "nextQuestion": {"type": ["string", "null"]},
        },
        "required": ["isSuccess", "selected", "message", "nextQuestion"],
        "additionalProperties": False,
    }

    prompt = (
        f"{question}에 대한 응답입니다.\n"
        f"- 응답: {answer}\n"
        "응답을 위 JSON 형식에 맞춰서만 반환하세요."
    )

    res = client.responses.create(
        model=CHAT_MODEL,
        instructions=CHAT_INSTRUCTIONS,
        input=prompt,
        text=_json_schema_text_format("BodyQuestionAnswer", schema),
    )

    raw = _response_text(res)
    data = _extract_json(raw)

    if data.get("selected") is None:
        data["selected"] = ""
    if data.get("nextQuestion") is None:
        data["nextQuestion"] = ""

    return data


def chat_body_result(
    answers: list[str],
    height: float,
    weight: float,
    gender: str,
):
    prompt = (
        "다음 응답 내용을 바탕으로 골격 진단 결과를 알려줘\n"
        f"- 성별: {gender}\n"
        f"- 키: {height}cm\n"
        f"- 체중: {weight}kg\n"
        "- 설문 응답:\n"
        + "\n".join(f"{i + 1}. {a}" for i, a in enumerate(answers))
        + "\n\n체형 진단"
    )

    res = client.responses.create(
        model=CHAT_MODEL,
        instructions=RESULT_INSTRUCTIONS,
        input=prompt,
        text=_json_schema_text_format("BodyDiagnosisResult", RESULT_SCHEMA),
    )

    raw = _response_text(res)
    try:
        return _extract_json(raw)
    except Exception as e:
        print("[DEBUG] raw from response:\n", raw)
        raise ValueError(f"JSON 파싱 실패: {e}")


def chat_body_result_soft(
    answers: list[str],
    height: float,
    weight: float,
    gender: str,
) -> Dict[str, Any]:
    """
    1) background 모드로 실행
    2) 최대 SOFT_WAIT_SEC 동안만 대기 후 완료되면 JSON 반환
    3) 미완료면 {thread_id, run_id, status} 반환 (호환성 유지)
    """
    prompt = _build_prompt(answers, height, weight, gender)

    res = client.responses.create(
        model=BODY_MODEL,
        instructions=RESULT_INSTRUCTIONS,
        input=prompt,
        background=True,
        text=_json_schema_text_format("BodyDiagnosisResult", RESULT_SCHEMA),
    )

    response_id = res.id
    deadline = time.time() + SOFT_WAIT_SEC

    status = getattr(res, "status", "in_progress") or "in_progress"
    current = res
    while time.time() < deadline and status not in {"completed", "failed", "cancelled", "incomplete"}:
        time.sleep(0.4)
        current = client.responses.retrieve(response_id)
        status = getattr(current, "status", "in_progress") or "in_progress"

    if status == "completed":
        raw = _response_text(current)
        data = _extract_json(raw)
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

    if status in {"failed", "cancelled", "incomplete"}:
        raise RuntimeError(f"responses job {status}")

    return {"thread_id": "", "run_id": response_id, "status": status}


def get_run_status(thread_id: str, run_id: str) -> Dict[str, Any]:
    _ = thread_id  # backwards-compatible signature
    st = client.responses.retrieve(run_id)
    return {"status": getattr(st, "status", "unknown"), "last_error": getattr(st, "error", None)}


def get_run_result(thread_id: str, run_id: str) -> Dict[str, Any]:
    _ = thread_id  # backwards-compatible signature
    st = client.responses.retrieve(run_id)
    status = getattr(st, "status", "unknown")
    if status != "completed":
        return {"status": status}

    raw = _response_text(st)
    data = _extract_json(raw)
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
