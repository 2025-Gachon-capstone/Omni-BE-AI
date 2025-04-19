import os
import re
import google.generativeai as genai
from flask import json
from app import db
from app.models.prompt_log import PromptLog

from app.services.graph_service import save_benefit_to_graph

# Gemini 설정
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
models = genai.list_models()
# 사용가능한 제미나이 모델 출력
for model in models:
    print(model.name, model.supported_generation_methods)

model = genai.GenerativeModel("gemini-1.5-flash-latest")

def process_chat_and_store(sponsor_id: str, chat_text: str):
    # MySQL 저장
    try:
        log = PromptLog(sponsor_id=sponsor_id, chat_text=chat_text)
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return {"error": f"[MySQL] 저장 실패: {str(e)}"}

    # Gemini 호출 + 파싱
    try:
        prompt = f"""
        아래 문장에서 혜택 정보를 JSON으로 추출해줘. 필드는 다음과 같아:
        benefit_type, discount_percent, target_product, target_condition

        "{chat_text}"
        """
        res = model.generate_content(prompt)
        result = res.text.strip()
        # markdown-style JSON 블럭 제거
        clean_result = re.sub(r"^```json\n|```$", "", result.strip())
        benefit = json.loads(clean_result)
    except Exception as e:
        return {"error": f"[Gemini] 처리 실패: {str(e)}", "raw": result if 'result' in locals() else None}

    # GraphDB 저장
    try:
        save_benefit_to_graph(sponsor_id, benefit)
    except Exception as e:
        return {"error": f"[GraphDB] 저장 실패: {str(e)}"}

    return benefit
