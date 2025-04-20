import google.generativeai as genai
from ..config import config
import re

# gemini 설정
API_KEY = config.GEMINI_API_KEY
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY 가 설정되지 않았습니다.")

genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-pro")  # 지원되는 모델로 변경

def clean_ai_response(response_text: str) -> str:
    # 포맷팅 문자를 제거하고 깔끔한 텍스트로 변환
    cleaned_text = re.sub(r'\*\*|\*|\n', '', response_text)
    return cleaned_text.strip()

def post_gemini(user_message: str) -> tuple[str | None, str | None]:
    try:
        # 사용자 메시지를 gemini API로 전송하여 응답을 받음
        response = gemini_model.generate_content(user_message)
        ai_content = response.text.strip()
        # 응답 텍스트 정리
        cleaned_content = clean_ai_response(ai_content)
        return cleaned_content, None
    except Exception as e:
        return None, f"AI-503: AI 서비스 호출 중 오류 발생 ({e})"
    
