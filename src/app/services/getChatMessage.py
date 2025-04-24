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

def get_chat_message(benefitId, page, size=30) -> tuple[str, int]:
    connection = connect_db()
    if connection is None:
        # DB 연결 실패
        error_response = {
            "isSuccess": False,
            "code": "MYSQL-500",
            "message": "데이터베이스 연결 실패",
            "timestamp": _ts()
        }
        # 상태 코드 500 반환 (튜플 형태)
        return json.dumps(error_response, ensure_ascii=False, indent=2), 500
    
    messages = []
    cursor = None # cursor 초기화
    try:
        cursor = connection.cursor(dictionary=True)
        
        # 총 메시지 수 조회
        count_sql = "SELECT COUNT(*) as total FROM chatMessage WHERE benefitId = %s"
        cursor.execute(count_sql, (benefitId,))
        total_messages = cursor.fetchone()['total']
        
        # OFFSET과 LIMIT을 사용하여 페이징 구현
        offset = (page - 1) * size
        sql = "SELECT id as messageId, author, content FROM chatMessage WHERE benefitId = %s LIMIT %s OFFSET %s"
        cursor.execute(sql, (benefitId, size, offset))
        messages = cursor.fetchall()  # 모든 결과를 딕셔너리 리스트로 가져옴

        # 페이지네이션 정보 계산
        hasNext = (offset + size) < total_messages
        hasPrev = page > 1

        # DB 조회 성공
        body = {
            "isSuccess": True,
            "code": "FLASK-200",
            "message": "메시지 조회 성공",
            "timestamp": _ts(),
            "userMessageId": f"msg-{benefitId:03}",  # 예시로 benefitId를 사용하여 userMessageId 생성
            "result": {
                "messages": messages,
                "hasNext": hasNext,
                "hasPrev": hasPrev
            }
        }

        # 상태 코드 200 반환 (튜플 형태)
        return json.dumps(body, ensure_ascii=False, indent=2, default=str), 200
    
    # DB 조회 실패
    except Exception as e:
        error_response = {
            "isSuccess": False,
            "code": "DB-500",
            "message": str(e),
            "timestamp": _ts()
        }
        # 상태 코드 500 반환 (튜플 형태)
        return json.dumps(error_response, ensure_ascii=False, indent=2), 500
    
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            


