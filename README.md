# 🌐 YourMode FastAPI

OpenAI Responses API와 FastAPI를 활용한 YourMode 백엔드 서버입니다.  
체형 분석 및 패션 스타일링 기능과 개인화 콘텐츠 추천 기능을 지원합니다.

---

## 📁 프로젝트 구조

```bash
my_assistant_app/
├── app/
│   ├── main.py                 # FastAPI 엔트리포인트
│   ├── api/
│   │   └── assistant.py        # Assistant API 라우터
│   ├── services/
│   │   └── assistant_service.py # OpenAI API 호출 로직
│   └── schemas/
│       └── assistant.py        # Pydantic 기반 요청/응답 모델 정의
├── .env                        # 환경변수 (OPENAI_API_KEY 등)
├── requirements.txt
└── README.md
