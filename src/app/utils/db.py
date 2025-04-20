import mysql.connector
from ..config import config 

def connect_db():
    try:
        connection = mysql.connector.connect(
            host=config.DB_HOST,       # 설정 파일에서 가져옴
            user=config.DB_USER,       # 설정 파일에서 가져옴
            password=config.DB_PASSWORD, # 설정 파일에서 가져옴
            database=config.DB_NAME,   # 설정 파일에서 가져옴
            charset='utf8mb4'
        )
        if connection.is_connected():
            return connection
        
    except Error as e:
        print(f"데이터베이스 연결 오류: {e}")
        return None
