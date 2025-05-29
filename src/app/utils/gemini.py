import os
from ..config import config

if getattr(config, "GOOGLE_APPLICATION_CREDENTIALS", None):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_PROJECT"] = config.GOOGLE_PROJECT  # 예: "grand-proton-460208"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"  # 예: "us-central1"

import re
from google import genai
from google.genai.types import HttpOptions

# # GEMINI 설정
# API_KEY = config.GEMINI_API_KEY
# if not API_KEY:
#     raise RuntimeError("GEMINI_API_KEY 가 설정되지 않았습니다.")

# 클라이언트 생성
client = genai.Client(http_options=HttpOptions(api_version="v1"))

def clean_ai_response(text: str) -> str:
    # 포맷팅 문자를 제거하고 깔끔한 텍스트로 변환
    text = text.replace("\\n", "\n")
    return re.sub(r'\*\*|\*', '', text).strip()

def post_gemini(user_message: str) -> tuple[str | None, str | None]:
    try:
        # 모델에 요청을 보내고 응답을 받음
        response = client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=user_message
        )
        # 응답 텍스트 정리
        cleaned_content = clean_ai_response(response.text)
        return cleaned_content, None
    except Exception as e:
        return None, f"AI-503: AI 서비스 호출 중 오류 발생 ({e})"