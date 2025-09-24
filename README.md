# YouTube 댓글 감성분석 시스템

YouTube 댓글을 수집하고 감성분석을 수행하여 트렌드를 분석하는 종합 시스템입니다.

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   YouTube API   │───▶│  댓글 수집      │───▶│  PostgreSQL     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  OpenSearch     │◀───│  데이터 집계    │◀───│  감성분석       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI 검색   │
└─────────────────┘
```

## 📁 프로젝트 구조

```
yt/
├── crawler/                 # 댓글 수집 및 감성분석
│   ├── crawl_comments.py   # YouTube 댓글 수집
│   ├── sentiment_infer.py  # 감성분석 모델
│   ├── process_comments.py # 댓글 처리
│   ├── aggregate_sentiment.py # 데이터 집계
│   ├── text_utils.py       # 텍스트 유틸리티
│   └── README.md           # 크롤러 문서
├── app/                    # FastAPI 검색 서버
│   ├── main.py            # API 서버
│   ├── requirements.txt   # Python 의존성
│   └── README.md          # 앱 문서
├── db/                     # 데이터베이스
│   ├── yt_schema.sql      # PostgreSQL 스키마
│   └── README.md          # DB 문서
├── docker-compose.yml      # 컨테이너 오케스트레이션
├── .env                    # 환경변수 설정
└── README.md              # 이 파일
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/DoHyunDaniel/yt_search_project.git
cd yt_search_project

# 환경변수 설정
cp env.example .env
# .env 파일을 편집하여 실제 API 키와 비밀번호 입력

# Python 의존성 설치
pip install -r requirements.txt
pip install -r crawler/requirements.txt
pip install -r app/requirements.txt
```

### 2. 서비스 실행

```bash
# 전체 서비스 실행
docker-compose up -d

# 개별 서비스 실행
docker-compose up -d opensearch  # 검색 엔진
docker-compose up -d pg          # 데이터베이스
docker-compose up -d app         # API 서버
```

### 3. 데이터 수집

```bash
# 댓글 수집 (PowerShell)
$env:YOUTUBE_API_KEY="실제_API_키"
python crawler/crawl_comments.py

# 감성분석
python crawler/process_comments.py

# 데이터 집계
python crawler/aggregate_sentiment.py
```

### 4. 검색 테스트

```bash
# API 상태 확인 (PowerShell)
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing

# 영상 검색
Invoke-WebRequest -Uri "http://localhost:8000/os_search?q=제주&size=5" -UseBasicParsing

# 또는 curl 사용 (Windows에서 curl.exe)
curl.exe http://localhost:8000/health
curl.exe "http://localhost:8000/os_search?q=제주&size=5"
```

## 🔧 주요 기능

### 1. 댓글 수집
- YouTube Data API v3를 통한 댓글 수집
- 영상별 댓글 메타데이터 저장
- 배치 처리로 효율적인 수집

### 2. 감성분석
- KoELECTRA 모델을 사용한 한국어 감성분석
- 긍정/부정/중립 분류 및 점수 생성
- 텍스트 전처리 및 정제

### 3. 데이터 집계
- 영상별 감성 통계 생성
- 전역 트렌드 분석
- OpenSearch 인덱스 업데이트

### 4. 검색 시스템
- Nori 한국어 분석기 지원
- 감성 점수 기반 검색
- RESTful API 제공

## 📊 데이터 흐름

1. **수집**: YouTube API → PostgreSQL
2. **분석**: PostgreSQL → 감성분석 → PostgreSQL
3. **집계**: PostgreSQL → 집계 → PostgreSQL + OpenSearch
4. **검색**: OpenSearch → FastAPI → 사용자

## 🛠️ 기술 스택

### 백엔드
- **Python 3.12**: 메인 개발 언어
- **FastAPI**: REST API 프레임워크
- **PostgreSQL**: 관계형 데이터베이스
- **OpenSearch**: 검색 엔진

### AI/ML
- **Transformers**: HuggingFace 라이브러리
- **PyTorch**: 딥러닝 프레임워크
- **KoELECTRA**: 한국어 감성분석 모델

### 인프라
- **Docker**: 컨테이너화
- **Docker Compose**: 오케스트레이션
- **Nori**: 한국어 형태소 분석기

## 📈 성능 지표

### 수집 성능
- 댓글 수집: ~100개/분
- 감성분석: ~50개/분
- 데이터 집계: ~1000개/분

### 검색 성능
- 평균 응답 시간: <100ms
- 동시 사용자: 100명
- 인덱스 크기: ~1GB

## 🔍 API 엔드포인트

### 검색 API
- `GET /health` - 서버 상태 확인
- `GET /search` - PostgreSQL 기반 영상 검색
- `GET /os_search` - OpenSearch 기반 영상 검색
- `POST /os/setup_nori` - Nori 인덱스 설정
- `POST /os/reindex` - 데이터 리인덱스

### 사용 예시
```bash
# PostgreSQL 기반 검색 (PowerShell)
Invoke-WebRequest -Uri "http://localhost:8000/search?q=제주&limit=5" -UseBasicParsing

# OpenSearch 기반 검색
Invoke-WebRequest -Uri "http://localhost:8000/os_search?q=제주맛집&size=5" -UseBasicParsing

# 서버 상태 확인
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing

# 또는 curl 사용
curl.exe "http://localhost:8000/search?q=제주&limit=5"
curl.exe "http://localhost:8000/os_search?q=제주맛집&size=5"
curl.exe http://localhost:8000/health
```

## 📊 모니터링

### 로그 확인
```bash
# 앱 로그
docker logs yt-app

# 데이터베이스 로그
docker logs yt-pg

# OpenSearch 로그
docker logs yt-os
```

### 데이터 확인
```bash
# 댓글 수 확인
docker exec yt-pg psql -U app -d yt -c "SELECT COUNT(*) FROM yt.comments;"

# 감성 분포 확인
docker exec yt-pg psql -U app -d yt -c "SELECT sentiment, COUNT(*) FROM yt.comments GROUP BY sentiment;"
```

## ⚠️ 주의사항

### 1. API 할당량
- YouTube API 일일 할당량: 10,000 단위
- 댓글 수집 시 할당량 소모 주의

### 2. 리소스 요구사항
- 최소 메모리: 8GB
- 최소 디스크: 20GB
- CPU: 4코어 권장

### 3. 보안
- API 키 보안 관리
- 데이터베이스 접근 제한
- HTTPS 사용 권장

## 🔧 문제 해결

### 1. 댓글 수집 실패
```bash
# API 키 확인
echo $env:YOUTUBE_API_KEY

# 데이터베이스 연결 확인
docker exec yt-pg psql -U app -d yt -c "SELECT 1;"
```

### 2. 감성분석 실패
```bash
# 모델 다운로드 확인
ls ~/.cache/huggingface/hub/models--beomi--KcELECTRA-base-v2022/

# 메모리 사용량 확인
docker stats
```

### 3. 검색 실패
```bash
# OpenSearch 상태 확인 (PowerShell)
Invoke-WebRequest -Uri "http://localhost:9200" -UseBasicParsing

# 또는 curl 사용
curl.exe http://localhost:9200

# 인덱스 확인
curl.exe "http://localhost:9200/_cat/indices"
```

## 📚 추가 문서

- [크롤러 시스템](./crawler/README.md)
- [API 서버](./app/README.md)
- [데이터베이스](./db/README.md)

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

MIT License

---

## 🆕 Updates (2025-09-24)

- Domain focus: '행궁' 중심으로 데이터 수집 및 유사 검색 제공
- Added lightweight local stack for rapid iteration:
  - `simple_api_server.py`: local API with endpoints
    - `GET /health`, `GET /search_methods`, `GET /embedding_stats`,
      `GET /similar_search`, `GET /similar_keywords`
  - `simple_frontend.html`: single-page UI with re-search, stats, loading UI, and XSS-safe rendering
- Security hardening:
  - Backend input validation (rejects `<`, `script`, inline handlers)
  - Frontend escapes user text and uses safe setters
- Data collection changes:
  - `crawler/crawl_videos.py` now searches multiple palace-related keywords (행궁/궁궐/경복궁/… + 데이트/카페/맛집 연관 키워드), default window 30 days, per-keyword up to 50 videos, duplicate removal by `videoId`
  - OpenSearch indexing is temporarily disabled in the crawler for local runs
  - `crawler/crawl_comments.py` increases per-video cap (up to 500) and handles disabled comments/404 gracefully
  - `crawler/palace_keywords.py` defines palace keyword sets and semantic mapping for 데이트/카페/식당
- Scheduler (`crawler/scheduler.py`) tuning:
  - Comments every 4h, sentiment every 1h, aggregate every 2h, embeddings every 4h
  - One-shot mode for manual runs
- YouTube API quota guidance:
  - Daily reset: 05:00 KST; split large crawls across days; prioritize 데이트/카페/맛집 queries first day