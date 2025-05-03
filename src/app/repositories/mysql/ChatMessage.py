from sqlalchemy import text

from app.models.chatMessage import AuthorType, ChatMessage
from ...utils import db

class MysqlChatMessageRepository:

    @staticmethod
    def save_message(benefit_id: int, author_type: AuthorType, content: str) -> ChatMessage:
        user_message = ChatMessage(
            benefit_id=benefit_id,
            author_type=author_type,
            content=content
        )
        db.session.add(user_message)
        db.session.flush()  # ID 확보
        return user_message
    
    @staticmethod
    def get_messages(benefit_id: int, limit: int = 30):
        messages = (
            db.session.query(ChatMessage)
            .filter_by(benefit_id=benefit_id)
            .order_by(ChatMessage.chat_message_id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "chatMessageId": msg.chat_message_id,
                "author": msg.author_type.value,
                "content": msg.content
            }
            for msg in reversed(messages)  # 최신순 정렬되어 있으므로 reverse
        ]
    
    @staticmethod
    def get_sliced_messages(benefit_id: int, page: int = 1, size: int = 30):
        total_messages = (
            db.session.query(ChatMessage)
            .filter_by(benefit_id=benefit_id)
            .count()
        )
        offset = (page - 1) * size
        messages = (
            db.session.query(ChatMessage)
            .filter_by(benefit_id=benefit_id)
            .order_by(ChatMessage.chat_message_id.desc())
            .offset(offset)
            .limit(size)
            .all()
        )
        return {
            "messages": [
                {
                    "chatMessageId": msg.chat_message_id,
                    "author": msg.author_type.value,
                    "content": msg.content
                }
                for msg in messages
            ],
            "total": total_messages,
            "hasNext": (offset + size) < total_messages,
            "hasPrev": page > 1,
        }