import os
from dotenv import load_dotenv
import openai as oai

from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

load_dotenv()

oai_client = oai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model_name="gpt-4o",
    temperature=0.8,
    model_kwargs={"top_p": 0.95, "max_tokens": 1024}
)


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

diagnosis_chain = LLMChain(llm=llm, prompt=diagnosis_prompt)
section_chains   = { k: LLMChain(llm=llm, prompt=pt) for k,pt in section_prompts.items() }

def run_body_diagnosis(
        answers: list[str],
        height: float,
        weight: float,
        gender: str
) -> dict:
    answers_text = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(answers))

    diag_text: str = diagnosis_chain.predict(
        answers=answers_text,
        gender=gender,
        height=height,
        weight=weight,
    ).strip()

    if "\n" in diag_text:
        header, reason_line = diag_text.split("\n", 1)
        body_type = header.split(":", 1)[1].strip()
        type_desc = reason_line.split(":", 1)[1].strip()
    else:
        body_type = diag_text.split("체형:", 1)[-1].strip()
        type_desc = ""

    result = {"body_type": body_type, "type_description": type_desc}

    for key, chain in section_chains.items():
        result[key] = chain.predict(body_type=body_type).strip()
    return result
