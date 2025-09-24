# 데이터베이스 스키마 및 설정

이 디렉터리는 PostgreSQL 데이터베이스 스키마와 관련 설정을 포함합니다.

## 📁 파일 구조

```
db/
├── yt_schema.sql     # PostgreSQL 스키마 정의
└── README.md         # 이 파일
```

## 🗄️ 데이터베이스 스키마

### 1. 채널 테이블 (`yt.channels`)

**목적:** YouTube 채널 정보 저장

**컬럼:**
- `id`: UUID (기본키)
- `channel_yid`: YouTube 채널 ID
- `title`: 채널명
- `description`: 채널 설명
- `subscriber_count`: 구독자 수
- `video_count`: 영상 수
- `view_count`: 총 조회수
- `created_at`: 생성일시
- `updated_at`: 수정일시

### 2. 영상 테이블 (`yt.videos`)

**목적:** YouTube 영상 정보 저장

**컬럼:**
- `id`: UUID (기본키)
- `video_yid`: YouTube 영상 ID
- `channel_id`: 채널 ID (외래키)
- `title`: 영상 제목
- `description`: 영상 설명
- `published_at`: 업로드 일시
- `duration`: 영상 길이 (초)
- `view_count`: 조회수
- `like_count`: 좋아요 수
- `comment_count`: 댓글 수
- `tags`: 태그 배열
- `created_at`: 생성일시
- `updated_at`: 수정일시

### 3. 댓글 테이블 (`yt.comments`)

**목적:** YouTube 댓글 및 감성분석 결과 저장

**컬럼:**
- `id`: UUID (기본키)
- `video_id`: 영상 ID (외래키)
- `comment_yid`: YouTube 댓글 ID
- `author_yid`: 작성자 YouTube ID
- `author_name`: 작성자명
- `text_raw`: 원본 댓글 텍스트
- `text_clean`: 정제된 댓글 텍스트
- `lang`: 언어 코드
- `like_count`: 좋아요 수
- `published_at`: 작성일시
- `sentiment`: 감성 라벨 (pos/neg/neu)
- `sentiment_score`: 감성 점수 (-1.0~1.0)
- `keywords`: 키워드 배열
- `toxicity_score`: 독성 점수
- `metadata`: 추가 메타데이터 (JSON)
- `created_at`: 생성일시

**파티셔닝:** `published_at` 컬럼 기준으로 월별 파티션

### 4. 장소 테이블 (`yt.places`)

**목적:** 영상에 언급된 장소 정보 저장

**컬럼:**
- `id`: UUID (기본키)
- `name`: 장소명
- `address`: 주소
- `latitude`: 위도
- `longitude`: 경도
- `place_type`: 장소 유형
- `created_at`: 생성일시

### 5. 영상-장소 연결 테이블 (`yt.video_places`)

**목적:** 영상과 장소의 다대다 관계 저장

**컬럼:**
- `video_id`: 영상 ID (외래키)
- `place_id`: 장소 ID (외래키)
- `created_at`: 생성일시

### 6. 특징 테이블 (`yt.features`)

**목적:** 영상별 감성 분석 특징 저장

**컬럼:**
- `id`: UUID (기본키)
- `entity_type`: 엔티티 유형 (video)
- `entity_id`: 엔티티 ID (영상 ID)
- `feature_date`: 특징 날짜
- `features`: 특징 데이터 (JSON)
- `version`: 버전
- `metadata`: 메타데이터 (JSON)
- `created_at`: 생성일시

**JSON 구조 예시:**
```json
{
  "avg_sentiment_score": 0.8,
  "counts": {
    "pos": 10,
    "neg": 2,
    "total": 12
  },
  "window_days": 30
}
```

### 7. 트렌드 테이블 (`yt.trends`)

**목적:** 전역 및 키워드별 트렌드 데이터 저장

**컬럼:**
- `id`: UUID (기본키)
- `scope_type`: 집계 범위 (global, keyword)
- `scope_id`: 집계 ID
- `keyword`: 키워드 (키워드별 트렌드용)
- `period_start`: 집계 시작일
- `period_end`: 집계 종료일
- `metrics`: 트렌드 메트릭 (JSON)
- `metadata`: 메타데이터 (JSON)
- `created_at`: 생성일시

**JSON 구조 예시:**
```json
{
  "pos_rate": 0.6,
  "neg_rate": 0.1,
  "total_comments": 1000
}
```

### 8. 수집 작업 테이블 (`yt.ingest_jobs`)

**목적:** 데이터 수집 작업 로그 저장

**컬럼:**
- `id`: UUID (기본키)
- `job_type`: 작업 유형 (video, comment)
- `status`: 상태 (running, completed, failed)
- `started_at`: 시작일시
- `completed_at`: 완료일시
- `error_message`: 오류 메시지
- `metadata`: 작업 메타데이터 (JSON)
- `created_at`: 생성일시

## 🔧 인덱스 설정

### 1. 기본 인덱스
- 모든 테이블의 `id` 컬럼에 기본키 인덱스
- 외래키 컬럼에 인덱스

### 2. 검색 최적화 인덱스
- `videos.title` - 영상 제목 검색용
- `videos.published_at` - 날짜별 정렬용
- `comments.text_raw` - 댓글 텍스트 검색용 (trigram)
- `comments.published_at` - 댓글 날짜별 정렬용

### 3. JSON 인덱스
- `comments.metadata` - GIN 인덱스
- `features.features` - GIN 인덱스
- `trends.metrics` - GIN 인덱스

## 🚀 사용법

### 1. 스키마 생성

```bash
# Docker 컨테이너에서 실행 (PowerShell)
Get-Content db/yt_schema.sql | docker exec -i yt-pg psql -U app -d yt

# 또는 직접 실행
docker exec -i yt-pg psql -U app -d yt < db/yt_schema.sql

# 로컬에서 실행
psql -h localhost -p 55432 -U app -d yt -f db/yt_schema.sql
```

### 2. 데이터베이스 연결

```bash
# 환경변수 설정 (PowerShell)
$env:DB_HOST="localhost"
$env:DB_PORT="55432"
$env:DB_NAME="yt"
$env:DB_USER="app"
$env:DB_PASSWORD="app1234"

# psql로 연결
psql -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_USER -d $env:DB_NAME

# 또는 Docker 컨테이너를 통해 연결
docker exec -it yt-pg psql -U app -d yt
```

### 3. 테이블 확인

```sql
-- 테이블 목록 확인
\dt yt.*

-- 특정 테이블 구조 확인
\d yt.comments

-- 데이터 개수 확인
SELECT COUNT(*) FROM yt.comments;
```

## 📊 성능 최적화

### 1. 파티셔닝
- `comments` 테이블을 `published_at` 기준으로 월별 파티션
- 오래된 데이터 자동 관리

### 2. 인덱스 최적화
- 자주 사용되는 쿼리 패턴에 맞는 인덱스 설정
- JSON 필드에 GIN 인덱스 적용

### 3. 연결 풀링
- 애플리케이션에서 연결 풀 사용
- 적절한 최대 연결 수 설정

## 🔍 주요 쿼리 예시

### 1. 영상별 댓글 통계
```sql
SELECT 
    v.title,
    COUNT(c.id) as comment_count,
    AVG(c.sentiment_score) as avg_sentiment
FROM yt.videos v
LEFT JOIN yt.comments c ON v.id = c.video_id
GROUP BY v.id, v.title
ORDER BY comment_count DESC;
```

### 2. 감성별 댓글 분포
```sql
SELECT 
    sentiment,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM yt.comments
WHERE sentiment IS NOT NULL
GROUP BY sentiment
ORDER BY count DESC;
```

### 3. 최근 트렌드
```sql
SELECT 
    period_start,
    period_end,
    metrics->>'pos_rate' as pos_rate,
    metrics->>'neg_rate' as neg_rate,
    metrics->>'total_comments' as total_comments
FROM yt.trends
WHERE scope_type = 'global'
ORDER BY period_start DESC
LIMIT 10;
```

## ⚠️ 주의사항

1. **데이터 타입**: UUID, JSONB 등 PostgreSQL 특화 타입 사용
2. **파티셔닝**: 댓글 테이블은 월별 파티션으로 관리
3. **인덱스**: JSON 필드 검색을 위한 GIN 인덱스 필수
4. **백업**: 정기적인 데이터베이스 백업 필요
5. **성능**: 대용량 데이터 처리를 위한 쿼리 최적화 필요
