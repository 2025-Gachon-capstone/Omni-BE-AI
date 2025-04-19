from ..utils.db import connect_db

def read_chat_message(benefitId, page, size=30):
    """
    주어진 benefitId에 해당하는 메시지를 페이지당 size 개수만큼 조회합니다.
    """     
    connection = connect_db()
    if connection is None:
        return {"error": "데이터베이스 연결 실패"}, 500

    messages = []
    try:
        cursor = connection.cursor(dictionary=True)
        # OFFSET과 LIMIT을 사용하여 페이징 구현
        offset = (page - 1) * size
        sql = "SELECT * FROM Messages WHERE benefitId = %s LIMIT %s OFFSET %s"
        cursor.execute(sql, (benefitId, size, offset))
        messages = cursor.fetchall()  # 모든 결과를 딕셔너리 리스트로 가져옴
    except Exception as e:
        print(f"메시지 조회 오류: {e}")
        return {"error": "DB 조회 오류"}, 500
    finally:
        if connection.is_connected():
            connection.close()  # 연결 해제
            print("데이터베이스 연결 해제됨 (readChatMessage)")

    return messages  # 조회된 메시지 목록 반환

