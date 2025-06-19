import os
import json
from dotenv import load_dotenv
import openai as oai

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

load_dotenv()

# OpenAI 클라이언트 & LLM 설정
oai_client = oai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model_name="gpt-4o",
    temperature=0.8,
    model_kwargs={"top_p": 0.95, "max_tokens": 1024}
)

# 1) 체형 진단 프롬프트 & 체인
diagnosis_prompt = PromptTemplate(
    input_variables=["answers", "gender", "height", "weight"],
    template="""
당신은 골격 진단 전문 퍼스널 스타일리스트입니다.
아래 정보를 바탕으로 체형을 '스트레이트', '웨이브', '내추럴' 중 하나로 판단하고
그 이유를 5~6문장으로 간결하게 설명해 주세요.

성별: {gender}
키: {height}cm
체중: {weight}kg
신체 응답:
{answers}

출력 예시:
체형: 내추럴  
이유: 균형 잡힌 체형으로 인해...
"""
)
diagnosis_chain = diagnosis_prompt | llm

# 2) 섹션별 프롬프트 정의
section_prompts = {
    "type_description": PromptTemplate(
        input_variables=["body_type"],
        template="""
당신의 체형이 '{body_type}'라고 진단되었습니다.
이 결과에 대해 4~6문장으로 간결하게 에세이 스타일로 설명해 주세요.
"""
    ),
    "detailed_features": PromptTemplate(
        input_variables=["body_type"],
        template="""
'{body_type}' 체형의 주요 신체 실루엣과 골격, 비율, 특징을
4~6문장으로 구체적으로 설명해 주세요.
"""
    ),
    "attraction_points": PromptTemplate(
        input_variables=["body_type"],
        template="""
'{body_type}' 체형이 가진 가장 돋보이는 매력 포인트를
4~6문장으로 에세이 스타일로 설명해 주세요.
"""
    ),
    "recommended_styles": PromptTemplate(
        input_variables=["body_type"],
        template="""
'{body_type}' 체형에 가장 잘 어울리는 스타일과
구체적인 아이템(계절·상황별 예시 포함)을 4~6문장으로 제안해 주세요.
"""
    ),
    "avoid_styles": PromptTemplate(
        input_variables=["body_type"],
        template="""
'{body_type}' 체형에서 피해야 할 스타일, 실수하기 쉬운 룩을
4~6문장으로 상세히 설명해 주세요.
"""
    ),
    "styling_fixes": PromptTemplate(
        input_variables=["body_type"],
        template="""
'{body_type}' 체형의 단점을 보완하고 장점을 극대화하는
구체적인 연출법과 노하우를 4~6문장으로 안내해 주세요.
"""
    ),
    "styling_tips": PromptTemplate(
        input_variables=["body_type"],
        template="""
'{body_type}' 체형을 위한 실제 스타일링 팁(아이템 조합·TPO별 연출 등)을
4~6문장으로 에세이 형식으로 제공해 주세요.
"""
    ),
}
# Prompt→LLM 체인 생성
section_chains = {key: prompt | llm for key, prompt in section_prompts.items()}


def run_body_diagnosis(
    answers: list[str],
    height: float,
    weight: float,
    gender: str
) -> dict:
    # 설문 문자열화
    answers_text = "\n".join(f"{i+1}. {a}" for i, a in enumerate(answers))

    # 1) 체형 진단 호출 및 방어적 파싱
    diag_raw = diagnosis_chain.invoke({
        "answers": answers_text,
        "gender":  gender,
        "height":  height,
        "weight":  weight
    })
    diag_text = diag_raw.get("text") if isinstance(diag_raw, dict) else str(diag_raw)
    lines = diag_text.strip().split("\n", 1)
    if len(lines) < 2:
        # 라벨 기준 파싱 시도
        body_type = diag_text.split("체형:", 1)[-1].strip() if "체형:" in diag_text else diag_text.strip()
        type_desc = ""
    else:
        header, reason_line = lines
        body_type = header.split(':', 1)[1].strip() if ':' in header else header.strip()
        type_desc = reason_line.split(':', 1)[1].strip() if ':' in reason_line else reason_line.strip()

    # 2) 섹션별 내용 생성
    result = {"body_type": body_type, "type_description": type_desc}
    for key, chain in section_chains.items():
        sec_raw = chain.invoke({"body_type": body_type})
        sec_text = sec_raw.get("text") if isinstance(sec_raw, dict) else str(sec_raw)
        result[key] = sec_text.strip()

    return result