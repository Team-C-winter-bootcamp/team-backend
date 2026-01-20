FROM python:3.12

# Python 환경 변수
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 작업 디렉토리
WORKDIR /app

# 시스템 의존성 설치
# 4. 필수 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . /app

# 포트 노출
EXPOSE 8000

# 실행 명령
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
