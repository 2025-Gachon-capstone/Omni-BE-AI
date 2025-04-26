import json
from app.utils import ts

from ..utils.db import db  # ✅ SQLAlchemy 연결된 db 가져오기
from ..models.chatMessage import ChatMessage  # ✅ 모델 가져오기

def get_chat_message(benefitId, page, size=30) -> tuple[str, int]:
    try:
        # 총 메시지 수 조회
        total_messages = db.session.query(ChatMessage).filter_by(benefit_id=benefitId).count()

        # OFFSET과 LIMIT을 사용하여 페이징 조회
        offset = (page - 1) * size
        chat_messages = (
            db.session.query(ChatMessage)
            .filter_by(benefit_id=benefitId)
            .order_by(ChatMessage.chat_message_id.asc())
            .offset(offset)
            .limit(size)
            .all()
        )

        # 딕셔너리 형태로 변환
        messages = [
            {
                "messageId": msg.chat_message_id,
                "author_type": msg.author_type,  # author 필드가 author_type으로 바뀌었지?
                "content": msg.content
            }
            for msg in chat_messages
        ]

        hasNext = (offset + size) < total_messages
        hasPrev = page > 1

        body = {
            "isSuccess": True,
            "code": "FLASK-200",
            "message": "메시지 조회 성공",
            "timestamp": ts(),
            "result": {
                "messages": messages,
                "hasNext": hasNext,
                "hasPrev": hasPrev
            }
        }

        return json.dumps(body, ensure_ascii=False, indent=2, default=str), 200

    except Exception as e:
        print(f'error: {e}')

        error_response = {
            "isSuccess": False,
            "code": "MYSQL-500",
            "message": str(e),
            "timestamp": ts()
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2), 500
