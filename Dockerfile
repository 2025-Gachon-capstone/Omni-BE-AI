FROM python:3.11-slim AS builder

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt만 먼저 복사 → 캐시 활용
COPY requirements.txt .

# pip 업그레이드 & 의존성 설치
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

FROM python:3.11-slim

# 환경 변수 설정
## 로그 출력 속도
ENV PYTHONUNBUFFERED=1
ENV PROFILE=${PROFILE}
ENV TZ=Asia/Seoul

# 작업 디렉토리 설정
WORKDIR /app

# 빌더 단계에서 설치한 패키지 복사
COPY --from=builder /install /usr/local

# 애플리케이션 코드 복사
COPY . .

# 컨테이너가 열 포트 지정 (Flask 기본: 5000)
EXPOSE 5000

# 실행 명령 (gunicorn으로 실행, run.py 기준)
CMD ["sh", "-c", "gunicorn src.app.run:app --bind 0.0.0.0:5000 --timeout 120"]
