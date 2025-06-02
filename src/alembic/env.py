import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# --- 경로 설정 ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- 환경변수 로드 ---
load_dotenv()

# --- Alembic 설정 객체 ---
config = context.config
fileConfig(config.config_file_name)

# --- Flask 앱 로드 ---
from app.utils import create_app, db
from app.models import *

app = create_app()
app.app_context().push()

# --- MetaData 전달 (자동 마이그레이션 핵심) ---
target_metadata = db.metadata

print("Metadata tables:")
for table in target_metadata.tables.values():
    print(f"- {table.name}")

# --- DB URI 설정 (env에서 동적 주입) ---
DB_HOST = app.config.get("DB_HOST")

DB_PORT = app.config.get("DB_PORT")
DB_USER = app.config.get("DB_USER")
DB_PASSWORD = app.config.get("DB_PASSWORD") 
DB_NAME = app.config.get("DB_NAME")

SQLALCHEMY_DATABASE_URI = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    f"?ssl_disabled=True&use_unicode=True&time_zone=Asia/Seoul"
)
config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI)

# --- 마이그레이션 실행 로직 ---
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,  # ✅ 추가
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,  # ✅ 핵심: 메타데이터 연결됨
            include_object=include_object,  # ✅ 추가
        )
        with context.begin_transaction():
            context.run_migrations()

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        return name == "ChatMessage"  # ✅ chat_message 테이블만 관리
    return True

# --- 실행 트리거 ---
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()