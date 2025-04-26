import enum

from sqlalchemy import ForeignKeyConstraint
from ..utils import db

class AuthorType(enum.Enum):
    USER = "USER"
    AI = "AI"

class ChatMessage(db.Model):
    __tablename__ = 'ChatMessage'

    chat_message_id = db.Column('chatMessageId', db.Integer, primary_key=True)
    benefit_id = db.Column('benefitId', db.Integer, nullable=False)
    author_type = db.Column('authorType',db.Enum(AuthorType), nullable=False)
    content = db.Column(db.Text, nullable=False)
    version = db.Column(db.Integer, server_default=db.text('0'), nullable=False)

    created_at = db.Column('createdAt',db.DateTime, server_default=db.func.now())
    updated_at = db.Column('updatedAt',db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    created_by = db.Column('createdBy',db.String(255), server_default='flask-service')
    updated_by = db.Column('updatedBy',db.String(255), server_default='flask-service')