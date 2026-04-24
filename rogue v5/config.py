import os

# AI 내레이션 기능 설정 (선택 사항 — 없어도 게임 정상 실행됨)
# 사용하려면: pip install google-generativeai 후 아래에 키 입력
# 환경변수 GEMINI_API_KEY 설정하거나 문자열 직접 입력
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
MODEL_NAME = "gemini-1.5-flash"