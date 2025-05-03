import re
from google import genai
from google.genai import types

from ..config import config

# GEMINI 설정
API_KEY = config.GEMINI_API_KEY
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY 가 설정되지 않았습니다.")

# 클라이언트 생성
client = genai.Client(api_key=API_KEY)

def clean_ai_response(text: str) -> str:
    # 포맷팅 문자를 제거하고 깔끔한 텍스트로 변환
    return re.sub(r'\*\*|\*|\n', '', text).strip()

def post_gemini(user_message: str) -> tuple[str | None, str | None]:
    try:
        # 모델에 요청을 보내고 응답을 받음
        response = client.models.generate_content(
            model="gemini-1.5-pro",
            contents=user_message
        )
        # 응답 텍스트 정리
        cleaned_content = clean_ai_response(response.text)
        return cleaned_content, None
    except Exception as e:
        return None, f"AI-503: AI 서비스 호출 중 오류 발생 ({e})"
    
# def get_text_embedding(text: str):
#     '''
#     임베딩 3072 차원. 
#     몇번 쓰면 더 이상 못쓰게 막힘. 보류
#     '''
#     print(f'text embedding start')
#     try:
#         response = client.models.embed_content(
#             model="gemini-embedding-exp-03-07",
#             contents=text,
#             config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")
#         )
#         print(f'text embedding finish')
#         print(f'response: {response.embeddings}')
#         return response.embeddings[0].values
#     except Exception as e:
#         raise ConnectionError(f"AI-504: 텍스트 임베딩 중 오류 발생 ({e})")
    

from sentence_transformers import SentenceTransformer

# 최초 한 번만 전역 로드 (성능 이유)
_e5_model = SentenceTransformer("intfloat/multilingual-e5-large-instruct")

def get_text_embedding(text: str, task: str = "유사한 고객을 찾기 위한 검색"):
    """
    intfloat/multilingual-e5-large-instruct 기반 로컬 임베딩 (1024차원)
    """
    print("text embedding start")

    try:
        formatted = f"Instruct: {task}\nQuery: {text}"
        embedding = _e5_model.encode(formatted, normalize_embeddings=True)

        print("text embedding finish")
        return embedding.tolist()  # Neo4j ArrayProperty 저장을 위해 list로
    except Exception as e:
        raise ConnectionError(f"LOCAL-504: 텍스트 임베딩 중 오류 발생 ({e})")