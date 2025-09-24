# YouTube 댓글 크롤링 및 감성분석 시스템

YouTube 댓글을 수집하고 감성분석을 수행하여 트렌드를 분석하는 크롤링 시스템입니다.

## 🏗️ 시스템 구성

### 핵심 모듈
- **`crawl_comments.py`**: YouTube API를 통한 댓글 수집
- **`sentiment_infer.py`**: KoELECTRA 모델을 사용한 감성분석
- **`process_comments.py`**: 댓글 감성분석 처리
- **`aggregate_sentiment.py`**: 영상별 감성 통계 집계 및 OpenSearch 업데이트
- **`text_utils.py`**: 텍스트 정제 및 전처리 유틸리티

### 🆕 검색어 유사도 기능 (업데이트)
- **`embedding_service.py`**: 한국어 텍스트 벡터 임베딩 변환
- **`similarity_utils.py`**: 다양한 유사도 계산 알고리즘
- **`generate_embeddings.py`**: 기존 데이터 임베딩 생성 파이프라인
 - **`palace_keywords.py`**: '행궁/궁궐' 관련 키워드와 의미 매핑(데이트/카페/식당 등)

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
export YOUTUBE_API_KEY="your_api_key"
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="yt"
export DB_USER="app"
export DB_PASSWORD="app1234"
```

### 2. 데이터 수집 및 분석

```bash
# 비디오 수집 ('행궁' 도메인 다중 키워드, 30일, 키워드당 최대 50개, 중복 제거)
python crawl_videos.py

# 댓글 수집 (비활성화/404 예외 처리 포함)
python crawl_comments.py

# 감성분석
python process_comments.py

# 데이터 집계
python aggregate_sentiment.py
```

### 3. 🆕 임베딩 생성 (새 기능)

```bash
# 임베딩 서비스 테스트
python embedding_service.py

# 기존 데이터 임베딩 생성
python generate_embeddings.py
```

## 📊 데이터 흐름

```
YouTube API → (비디오/댓글) 수집 → PostgreSQL → 감성분석 → 집계 → (선택) OpenSearch
                                    ↓
                              임베딩 생성 → 벡터 검색
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

### 4. 🆕 검색어 유사도 (업데이트)
- 한국어 텍스트 벡터 임베딩 및 문자열 기반 유사도
- 데이트/카페/식당 등 의미 매핑을 통한 확장 매칭
- 로컬 경량 API(`/similar_search`)와 연동

## 🛠️ 기술 스택

### AI/ML
- **Transformers**: HuggingFace 라이브러리
- **PyTorch**: 딥러닝 프레임워크
- **KoELECTRA**: 한국어 감성분석 모델
- **Sentence-Transformers**: 벡터 임베딩 모델

### 데이터베이스
- **PostgreSQL**: 관계형 데이터베이스
- **OpenSearch**: 검색 엔진

### 유틸리티
- **scikit-learn**: 머신러닝 유틸리티
- **NumPy**: 수치 계산
- **Konlpy**: 한국어 자연어 처리

## 📈 성능 지표

### 수집 성능
- 댓글 수집: ~100개/분
- 감성분석: ~50개/분
- 데이터 집계: ~1000개/분

### 🆕 임베딩 성능
- 벡터 생성: ~200개/분 (all-MiniLM-L6-v2)
- 벡터 생성: ~100개/분 (ko-sroberta-multitask)
- 유사도 계산: ~1000개/초

## 🔍 API 사용 예시

### 기본 크롤링
```python
from crawl_comments import collect_comments
from process_comments import process_sentiment
from aggregate_sentiment import run

# 댓글 수집
collect_comments(days=7, per_video_limit=200)

# 감성분석
process_sentiment(batch_size=200)

# 데이터 집계
run(days=30)
```

### 🆕 임베딩 사용
```python
from embedding_service import EmbeddingService

# 임베딩 서비스 초기화
service = EmbeddingService("sentence-transformers/all-MiniLM-L6-v2")

# 텍스트 벡터화
texts = ["제주도 맛집", "제주 여행", "서울 카페"]
embeddings = service.encode(texts)

# 유사도 계산
from sklearn.metrics.pairwise import cosine_similarity
similarity_matrix = cosine_similarity(embeddings)
```

## ⚠️ 주의사항

### 1. API 할당량
- YouTube API 일일 할당량: 10,000 units/day
- 매일 05:00 KST 리셋, 키워드/일자 분할 크롤링 권장

### 2. 리소스 요구사항
- 최소 메모리: 8GB (임베딩 모델 포함)
- 최소 디스크: 20GB
- CPU: 4코어 권장
- GPU: 선택사항 (임베딩 가속화)

### 3. 모델 다운로드
- 첫 실행 시 모델 자동 다운로드
- 인터넷 연결 필요
- 모델 크기: ~400MB (all-MiniLM-L6-v2), ~1.2GB (ko-sroberta-multitask)

## 🔧 문제 해결

### 1. 임베딩 모델 로드 실패
```bash
# 모델 캐시 확인
ls ~/.cache/huggingface/hub/

# 모델 수동 다운로드
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
```

### 2. 메모리 부족
```bash
# CPU 모드로 강제 실행
export CUDA_VISIBLE_DEVICES=""
python embedding_service.py
```

### 3. 의존성 문제
### 4. 크롤링 예외 처리
```
- 댓글 비활성화(403 commentsDisabled): 스킵 후 다음 아이템 진행
- 영상 없음(404 videoNotFound): 스킵
- DB 연결 포트: 로컬 테스트 시 `DB_PORT=55432` 확인
```

```bash
# 가상환경 재생성
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

## 📚 추가 문서

- [API 서버](../app/README.md)
- [데이터베이스](../db/README.md)
- [전체 시스템](../README.md)

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

MIT License