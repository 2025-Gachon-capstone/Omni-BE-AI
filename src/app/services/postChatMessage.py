import datetime
from ..utils.db import connect_db
from ..models.gemini import pr # 가상의 AI 응답 함수 임포트

def post_chat_message(benefitId, user_message):
    connection = connect_db()
    if connection is None:
        return {"error": "데이터베이스 연결 실패", "status_code": 500}
    
    user_message_id = None
    ai_response_content = None

    try:
        cursor = connection.cursor()
        now = datetime.datetime.now(datetime.timezone.utc) # UTC 시간 사용

        # 1. 사용자 메시지 저장 (author='USER')
        sql_insert_user = """
            INSERT INTO ChatMessage (benefit_id, author, content, send_at)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql_insert_user, (benefitId, 'USER', user_message, now))
        user_message_id = cursor.lastrowid # 삽입된 사용자 메시지의 ID 가져오기
        print(f"사용자 메시지 저장 완료 (ID: {user_message_id})")

        # 2. AI 응답 생성 (가상의 함수 호출)
        ai_response_content = get_ai_response(user_message)
        print(f"AI 응답 생성 완료: {ai_response_content}")

        # 3. AI 메시지 저장 (author='AI')
        sql_insert_ai = """
            INSERT INTO ChatMessage (benefit_id, author, content, send_at)
            VALUES (%s, %s, %s, %s)
        """
        # AI 응답 시간도 현재 시간으로 설정 (필요시 조정)
        cursor.execute(sql_insert_ai, (benefitId, 'AI', ai_response_content, datetime.datetime.now(datetime.timezone.utc)))
        ai_message_id = cursor.lastrowid
        print(f"AI 메시지 저장 완료 (ID: {ai_message_id})")

        # 4. 데이터베이스 변경사항 커밋
        connection.commit()

    except Exception as e:
        print(f"메시지 처리 중 오류 발생: {e}")
        if connection:
            connection.rollback() # 오류 발생 시 롤백
        return {"error": "메시지 처리 중 오류 발생", "status_code": 500}
    finally:
        if connection and connection.is_connected():
            cursor.close() # 커서 닫기
            connection.close()
            print("데이터베이스 연결 해제됨 (postChatMessage)")

    # 5. 성공 응답 생성
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    response_data = {
        "isSuccess": True,
        "code": "flask-200", # 성공 시 코드 
        "message": "협찬 추천 템플릿 생성 성공", # 성공 메시지 (필요시 조정)
        "timestamp": timestamp,
        "userMessageId": f"msg-{user_message_id}" if user_message_id else None, # ID 형식 맞춤
        "result": {
            "author": "AI",
            "content": ai_response_content
        }
    }

    return response_data # 딕셔너리 형태의 응답 데이터 반환
    
