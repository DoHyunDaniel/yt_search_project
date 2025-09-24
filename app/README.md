# FastAPI 검색 API 서버

이 디렉터리는 YouTube 영상 검색을 위한 FastAPI 기반 REST API 서버를 포함합니다.
개발/로컬 테스트 단계에서는 루트의 `simple_api_server.py`(경량 서버)와
`simple_frontend.html`(단일 페이지 UI)을 함께 사용할 수 있습니다.

## 📁 파일 구조

```
app/
├── main.py           # FastAPI 애플리케이션
├── requirements.txt  # Python 의존성
└── Dockerfile       # Docker 이미지 빌드 설정
```

## 🔧 기능 설명

### 1. 검색 API (`main.py`)

**주요 기능:**
- OpenSearch 기반 영상 검색
- Nori 한국어 분석기 지원
- 감성 점수 기반 검색
- PostgreSQL 데이터베이스 연동
 - (로컬) 경량 서버와 별도 운영 가능

**API 엔드포인트:**

#### `GET /health`
- 서버 상태 확인
- 데이터베이스 연결 상태 체크

#### `GET /os_search`
- OpenSearch를 통한 영상 검색
- 한국어 검색 지원 (Nori 분석기)

**파라미터:**
- `q`: 검색어 (선택사항)
- `size`: 결과 개수 (기본값: 10)

**응답 예시:**
```json
[
  {
    "id": "5R63Fl0utBU",
    "score": 1.0,
    "title": "제주 오일장 어떤 게 가장 맛있을까?",
    "published_at": "2025-09-23T06:05:13Z",
    "channel_id": "UCL2FITr_D_xQdClOfSs4o7Q",
    "video_id": "5R63Fl0utBU"
  }
]
```

#### `POST /os/setup_nori`
- Nori 한국어 분석기 인덱스 생성
- 한국어 검색 품질 향상

**파라미터:**
- `index`: 인덱스 이름 (기본값: "videos_ko")

#### `POST /os/reindex`
- 기존 인덱스에서 Nori 인덱스로 데이터 복사
- 별칭 스왑으로 무중단 전환

**파라미터:**
- `src`: 소스 인덱스 (기본값: "videos")
- `dest`: 대상 인덱스 (기본값: "videos_ko")
- `alias`: 별칭 이름 (기본값: "videos")

## 🚀 사용법

### 1. Docker로 실행 (권장)

```bash
# 전체 서비스 실행
docker compose up -d

# 앱만 실행
docker compose up -d app
```

### 2. 로컬에서 실행
# 경량 서버(루트) 실행 예시
python simple_api_server.py  # http://localhost:8000
python -m http.server 3000   # http://localhost:3000/simple_frontend.html


```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정 (PowerShell)
$env:DB_HOST="localhost"
$env:DB_PORT="55432"
$env:DB_NAME="yt"
$env:DB_USER="app"
$env:DB_PASSWORD="app1234"
$env:OS_HOST="http://localhost:9200"
$env:OS_USER="admin"
$env:OS_PASSWORD="App1234!@#"

# 서버 실행
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. API 테스트

```bash
# 서버 상태 확인 (PowerShell)
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing

# 전체 영상 검색
Invoke-WebRequest -Uri "http://localhost:8000/os_search?size=5" -UseBasicParsing

# 키워드 검색
Invoke-WebRequest -Uri "http://localhost:8000/os_search?q=제주&size=3" -UseBasicParsing

# Nori 인덱스 설정
Invoke-WebRequest -Uri "http://localhost:8000/os/setup_nori?index=videos_nori" -Method POST

# 리인덱스 실행
Invoke-WebRequest -Uri "http://localhost:8000/os/reindex?src=videos&dest=videos_nori" -Method POST

# 또는 curl 사용 (Windows에서 curl.exe)
curl.exe http://localhost:8000/health
curl.exe "http://localhost:8000/os_search?size=5"
curl.exe "http://localhost:8000/os_search?q=제주&size=3"
```

## 📊 의존성

### Python 패키지 (`requirements.txt`)
- `fastapi` - 웹 프레임워크
- `uvicorn[standard]` - ASGI 서버
- `psycopg2-binary` - PostgreSQL 연결
- `pydantic` - 데이터 검증
- `python-dotenv` - 환경변수 관리
- `opensearch-py` - OpenSearch 클라이언트

### 외부 서비스
- **PostgreSQL**: 영상 및 댓글 데이터 저장
- **OpenSearch**: 검색 엔진 (Nori 분석기 포함, 로컬 경량 서버에서는 선택)

## 🔧 환경변수 설정

```bash
# 데이터베이스 설정
DB_HOST=localhost
DB_PORT=55432
DB_NAME=yt
DB_USER=app
DB_PASSWORD=app1234

# OpenSearch 설정
OS_HOST=http://localhost:9200
OS_USER=admin
OS_PASSWORD=App1234!@#
```

## 📈 성능 최적화

### 1. OpenSearch 설정
- Nori 한국어 분석기 사용
- 적절한 인덱스 매핑 설정
- 별칭을 통한 무중단 전환

### 2. 데이터베이스 최적화
- 적절한 인덱스 설정
- 연결 풀링 사용
- 쿼리 최적화

### 3. API 최적화
- 비동기 처리
- 응답 캐싱
- 페이지네이션

## 🐳 Docker 설정

### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml
```yaml
app:
  build: ./app
  container_name: yt-app
  restart: unless-stopped
  ports:
    - "8000:8000"
  environment:
    - DB_HOST=pg
    - OS_HOST=https://opensearch:9200
  depends_on:
    - pg
    - opensearch
```

## 🔍 검색 기능 상세

### 1. 기본 검색
- 전체 영상 검색 (`q` 파라미터 없음)
- 최신순 정렬
- 페이지네이션 지원

### 2. 키워드 검색
- 제목 기반 검색
- 한국어 형태소 분석
- 부분 일치 지원

### 3. 감성 기반 검색
- `avg_sentiment_score` 필드 활용
- 긍정/부정 영상 필터링 가능

## ⚠️ 주의사항

1. **OpenSearch 연결**: OpenSearch가 실행 중이어야 함
2. **데이터베이스 연결**: PostgreSQL이 실행 중이어야 함
3. **포트 충돌**: 8000번 포트가 사용 중이지 않아야 함
4. **SSL 인증서**: 개발환경에서는 `verify_certs=False` 사용
5. **메모리 사용량**: OpenSearch와 PostgreSQL 충분한 메모리 필요

## 📚 API 문서

서버 실행 후 다음 URL에서 자동 생성된 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
