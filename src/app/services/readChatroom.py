from ..utils.db import connect_db

def read_chatroom(sponsorId):
    connection = connect_db()
    if connection is None:
        return {"error": "데이터베이스 연결 실패"}, 500  

    chatrooms = []
    try:
        cursor = connection.cursor(dictionary=True)
        sql = "SELECT * FROM Benefit WHERE sponsorId = %s"
        cursor.execute(sql, (sponsorId,))
        chatrooms = cursor.fetchall()  # 모든 결과를 딕셔너리 리스트로 가져옴
    except Exception as e:
        print(f"채팅방 조회 오류: {e}")
        return {"error": "DB 조회 오류"}, 500
    finally:
        if connection.is_connected():
            connection.close()  # 연결 해제
            print("데이터베이스 연결 해제됨 (readchatroom)")
            
    return chatrooms  