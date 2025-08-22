# 🌐 YourMode FastAPI

OpenAI Assistants API와 FastAPI를 활용한 YourMode 백엔드 서버입니다.
체형 분석 및 패션 스타일링 기능과 개인화 콘텐츠 추천 기능을 지원합니다.

---

## 📁 프로젝트 구조

```bash
your-mode-fast-api/
├── backend/                    # 백엔드 서버 관련
│   ├── main.py                # FastAPI 메인 애플리케이션
│   └── __init__.py
├── chatbot/                    # 챗봇 관련 기능
│   ├── assistant.py           # 챗봇 API 라우터
│   ├── schemas.py             # 통합 스키마 (채팅, 콘텐츠, 진단)
│   └── __init__.py
├── .env-example               # 환경변수 템플릿
├── pyproject.toml            # 프로젝트 설정 및 의존성
└── README.md
```