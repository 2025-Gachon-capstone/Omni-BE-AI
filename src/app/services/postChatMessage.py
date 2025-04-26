import json
import datetime

from app.utils import db, ts
from .gemini import post_gemini
from ..models.chatMessage import ChatMessage, AuthorType  # ✅ 모델 가져오기


def post_chat_message(benefit_id: int, user_content: str) -> tuple[str, int]:

    try:
        # 사용자 메시지 먼저 DB에 저장
        user_content_obj = ChatMessage(
            benefit_id=benefit_id,
            author_type=AuthorType.USER,
            content=user_content,
        )
        # 사용자 메시지 저장
        db.session.add(user_content_obj)
        db.session.flush()  # 바로 DB에 반영해서 user_message_id 얻기
        user_message_id = user_content_obj.chat_message_id

        # AI 응답 생성
        ai_content, ai_error = post_gemini(user_content)
        if ai_error:
            db.session.commit()  # 사용자 메시지는 커밋
            error_response = {
                "isSuccess": False,
                "code": ai_error.split(":")[0],
                "message": ai_error.split(":")[1].strip(),
                "timestamp": ts(),
                "userMessageId": f"msg-{user_message_id}"
            }
            return json.dumps(error_response, ensure_ascii=False), 503

        # AI 메시지 저장
        ai_message_obj = ChatMessage(
            benefit_id=benefit_id,
            author_type=AuthorType.AI,
            content=ai_content,
            version=1,
            created_by="flask"
        )
        db.session.add(ai_message_obj)

        # 트랜잭션 최종 커밋
        db.session.commit()

        success_response = {
            "isSuccess": True,
            "code": "FLASK-201",
            "message": "AI 응답 생성 및 저장 성공",
            "timestamp": ts(),
            "userMessageId": f"msg-{user_message_id}",
            "result": {
                "chatMessageId": ai_message_obj.chat_message_id,
                "authorType": AuthorType.AI.value,
                "content": ai_content
            }
        }
        return json.dumps(success_response, ensure_ascii=False), 201

    except Exception as e:
        print(f'error: {e}')
        db.session.rollback()
        error_response = {
            "isSuccess": False,
            "code": "FLASK-500",
            "message": f"메시지 처리 중 오류: {e}",
            "timestamp": ts()
        }
        return json.dumps(error_response, ensure_ascii=False), 500
