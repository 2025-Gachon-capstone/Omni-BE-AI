'''
사용법: /src 경로의 터미널에 아래 명령어를 입력. 문자열 자리에는 임의로 적으면 됨
1. alembic revision --autogenerate -m "Focus only ChatMessage table" # 스크립트 파일 (src/alembic/versions/..._.py) 생성 확인
2. alembic upgrade head # 해당 마이그레이션을 데이터베이스에 적용
'''

from ..utils import create_app, db

app = create_app()

with app.app_context():
    db.create_all()
    print("✅ All tables created!")