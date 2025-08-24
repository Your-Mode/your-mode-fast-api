from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]

CONFIG_DIR = PROJECT_ROOT / "config"

CHATBOT_CONFIG = CONFIG_DIR / "chatbotAgent.yaml"
BODY_DIAGNOSIS_QUESTIONS = CONFIG_DIR / "body_diagnosis_questions.json"
