import json

from sqlalchemy import text

from app.utils import db, ts

def get_chat_room(sponsorId) -> tuple[str, int]:
    
    chatrooms = []
    try:
        with db.engine.connect() as connection:
            sql = text("SELECT * FROM Benefit WHERE sponsor_id = :sponsor_id ORDER BY benefitId DESC")
            result = connection.execute(sql, {"sponsor_id": sponsorId})
            chatrooms = [dict(row) for row in result.mappings()]  # ✅ SQLAlchemy 2.0 스타일
            
            body = {
                "isSuccess": True,
                "code": "FLASK-200",
                "message": "채팅방 조회 성공",
                "timestamp": ts(),
                "result": chatrooms
            }
            return json.dumps(body, ensure_ascii=False, indent=2, default=str), 200
    
    except Exception as e:
        print(f'error: {e}')
        # DB 조회 실패
        error_response = {
            "isSuccess": False,
            "code": "MYSQL-500",
            "message": str(e), # 오류 메시지 문자열로 변환
            "timestamp": ts()
        }
        # 상태 코드 500 반환 (튜플 형태)
        return json.dumps(error_response, ensure_ascii=False, indent=2), 500
