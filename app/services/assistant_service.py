import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from app.services.langchain_service import run_body_diagnosis

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
assistant_id = "asst_kgiinKXSC4jKCWicgHP2HQtL"

def diagnose_assistant_with_tool(user_input: str) -> dict:
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
        args = json.loads(message_out.function_call.arguments)
        return run_body_diagnosis(**args)

    return {"error": "Function not called"}
