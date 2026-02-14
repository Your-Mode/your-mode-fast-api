# AGENTS.md

This document is a working guide for agents operating in the `/Users/minsu/Documents/your-mode-fast-api` repository.

## 1) Project Overview
- This is a FastAPI-based backend service.
- It uses the OpenAI Assistants API for body-type diagnosis, chat, and style content generation.
- The production deployment target is AWS Lambda, using `Mangum` to wrap ASGI.

## 2) Code Structure
- `app/main.py`: FastAPI entrypoint, CORS setup, router registration, `handler = Mangum(app)`
- `app/api/assistant.py`: HTTP endpoint definitions
- `app/services/assistant_service.py`: OpenAI calls, run polling, and result parsing
- `app/schemas/*.py`: Pydantic request/response models
- `Dockerfile`: Local/container server runtime
- `Dockerfile.build`: Builds Lambda deployment artifacts (`layer.zip`, `function.zip`)
- `.github/workflows/deploy.yml`: Deploys to Lambda on pushes to `main`/`dev`

## 3) Local Run
1. Install dependencies
   - `pip install -r requirements-dev.txt`
2. Configure environment variables (`.env`)
   - `OPENAI_API_KEY`
   - `OPENAI_BODY_ASSISTANT_ID`
   - `OPENAI_STYLE_ASSISTANT_ID`
   - `OPENAI_CHAT_ASSISTANT_ID`
3. Start the server
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## 4) Change Principles
- Make code changes in `app/` by default.
- Treat `package/`, `layer/`, `function.zip`, and `layer.zip` as build/deployment artifacts; do not edit them manually.
- If API specs change, keep router definitions (`app/api`) and schemas (`app/schemas`) in sync.
- When editing OpenAI response parsing logic, validate error paths too (incomplete run, timeout, JSON parse failures).

## 5) Deployment Notes
- Lambda environment variables are injected from GitHub Actions secrets.
- `deploy.yml` maps branch to alias:
  - `main` -> `prod`
  - `dev` -> `dev`
- If `Dockerfile.build` is changed, verify both layer/function zip outputs are still valid.

## 6) Work Checklist
- Confirm changed files are in the intended scope (primarily `app`)
- Check endpoint/schema consistency
- Run local server or at least perform import-level validation
- Ensure no unnecessary generated files or IDE files are committed

## 7) Commit Guidance (Recommended)
- Keep commit messages concise and intent-focused
  - Example: `feat: add polling endpoints for body-result`
  - Example: `fix: normalize assistant JSON parsing`
