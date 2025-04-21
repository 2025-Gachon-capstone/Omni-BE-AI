import os
import json
import datetime
import pytz

from ..utils.db import connect_db
from ..config import config 
from ..models.gemini import post_gemini

def _ts():
    # 한국 시간대 설정
    kst = pytz.timezone('Asia/Seoul')
    # 현재 UTC 시간을 한국 시간대로 변환
    now_kst = datetime.datetime.now(kst)
    # 연, 월, 일, 시간, 분, 초 포맷
    return now_kst.strftime("%Y-%m-%d %H:%M:%S")


def post_chat_message(benefitId: int, user_message: str) -> tuple[str, int]:
    connection = connect_db()
    if connection is None:
        # DB 연결 실패
        error_response = {
            "isSuccess": False,
            "code": "MYSQL-500",
            "message": "데이터베이스 연결 실패",
            "timestamp": _ts()
        }
        return json.dumps(error_response, ensure_ascii=False), 500

    try:
        cursor = connection.cursor()
        # 사용자 메시지 저장
        sql_user = """
            INSERT INTO ChatMessage (benefitId, author, content, sendAt, version, createdBy)
            VALUES (%s, 'USER', %s, %s, 1, 'flask')
        """
        cursor.execute(sql_user, (benefitId, user_message, datetime.datetime.utcnow()))
        user_message_id = cursor.lastrowid

        # AI 응답 생성
        ai_content, ai_error = post_gemini(user_message)
        if ai_error:
            connection.commit()  # 사용자 메시지는 유효하므로 커밋
            error_response = {
                "isSuccess": False,
                "code": ai_error.split(":")[0],
                "message": ai_error.split(":")[1].strip(),
                "timestamp": _ts(),
                "userMessageId": f"msg-{user_message_id}"
            }
            return json.dumps(error_response, ensure_ascii=False), 503

        # AI 메시지 저장
        sql_ai = """
            INSERT INTO ChatMessage (benefitId, author, content, sendAt, version, createdBy)
            VALUES (%s, 'AI', %s, %s, 1, 'flask')
        """
        cursor.execute(sql_ai, (benefitId, ai_content, datetime.datetime.utcnow()))

        # 트랜잭션 커밋
        connection.commit()

        success_response = {
            "isSuccess": True,
            "code": "FLASK-201",
            "message": "AI 응답 생성 및 저장 성공",
            "timestamp": _ts(),
            "userMessageId": f"msg-{user_message_id}",
            "result": {
                "author": "AI",
                "content": ai_content
            }
        }
        return json.dumps(success_response, ensure_ascii=False), 201

    except Exception as e:
        if connection:
            connection.rollback()
        error_response = {
            "isSuccess": False,
            "code": "SYS-500",
            "message": f"메시지 처리 중 오류: {e}",
            "timestamp": _ts()
        }
        return json.dumps(error_response, ensure_ascii=False), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
