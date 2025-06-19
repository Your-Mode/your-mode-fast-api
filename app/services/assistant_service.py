import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from app.services.langchain_service import run_body_diagnosis

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def send_message_to_assistant(user_input: str) -> str:
    assistant_id = "asst_kgiinKXSC4jKCWicgHP2HQtL"

    # 최신 방식: create_and_run 사용
    run = client.beta.threads.create_and_run(
        assistant_id=assistant_id,
        thread={"messages": [{"role": "user", "content": user_input}]}
    )

    # polling until completed
    while True:
        status = client.beta.threads.runs.retrieve(thread_id=run.thread_id, run_id=run.id)
        if status.status == "completed":
            break

    messages = client.beta.threads.messages.list(thread_id=run.thread_id)
    return messages.data[0].content[0].text.value


def diagnose_assistant_with_tool(user_input: str, diagnostic_json: dict) -> dict:
    # 메시지와 함수 정의를 dict 그대로 사용
    messages = [
        {"role": "user", "content": user_input}
    ]

    functions = [
        {
            "name": "diagnose_body_type",
            "description": "사용자의 응답 기반 체형 진단 및 스타일링 에세이 생성",
            "parameters": {
                "type": "object",
                "properties": {
                    "answers": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "height": {"type": "number"},
                    "weight": {"type": "number"},
                    "gender": {"type": "string"}
                },
                "required": ["answers", "height", "weight", "gender"]
            }
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        functions=functions,
        function_call={"name": "diagnose_body_type"}  # dict 그대로 사용
    )

    message_out = response.choices[0].message

    if message_out.function_call:
        # function_call.arguments는 str이므로 파싱
        args = json.loads(message_out.function_call.arguments)
        return run_body_diagnosis(**args)

    return {"error": "Function not called"}
