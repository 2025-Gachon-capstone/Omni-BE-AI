from langchain.embeddings.base import Embeddings
from sentence_transformers import SentenceTransformer

class CustomE5Embedding(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [get_text_embedding(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return get_text_embedding(text)
    
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
