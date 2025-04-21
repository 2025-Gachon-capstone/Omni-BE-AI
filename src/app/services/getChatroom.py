import json
import datetime
import pytz 
from ..utils.db import connect_db

def _ts():
    # 한국 시간대 설정
    kst = pytz.timezone('Asia/Seoul')
    # 현재 UTC 시간을 한국 시간대로 변환
    now_kst = datetime.datetime.now(kst)
    # 연, 월, 일, 시간, 분, 초 포맷
    return now_kst.strftime("%Y-%m-%d %H:%M:%S")


def get_chat_room(sponsorId):
    connection = connect_db()
    if connection is None:
        # DB 연결 실패
        error_response = {
            "isSuccess": False,
            "code": "MYSQL-500",
            "message": "데이터베이스 연결 실패",
            "timestamp": _ts()
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2, default=str)
    
    chatrooms = []
    try:
        cursor = connection.cursor(dictionary=True)
        sql = "SELECT * FROM Benefit WHERE id = %s"
        cursor.execute(sql, (sponsorId,))
        chatrooms = cursor.fetchall()

        # DB 조회 성공
        body = {
            "isSuccess": True,
            "code": "FLASK-200",
            "message": "채팅방 조회 성공",
            "timestamp": _ts(),
            "result": chatrooms
        }

        json_string = json.dumps(body, ensure_ascii=False, indent=2, default=str)
        return json_string
    
    except Exception as e:
        # DB 조회 실패
        error_response = {
            "isSuccess": False,
            "code": "MYSQL-500",
            "message": e,
            "timestamp": _ts()
        }
        return json.dumps(body, ensure_ascii=False, indent=2)
    
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
