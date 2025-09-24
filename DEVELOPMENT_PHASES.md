# 🚀 검색어 유사도 기능 개발 단계

## 📋 전체 개발 계획

### Phase 1: 백엔드 핵심 기능 개발

#### ✅ 1단계: 벡터 임베딩 모델 설정 (완료)
- **목표**: 한국어 텍스트를 벡터로 변환하는 모델 선택 및 설정
- **구현**: `crawler/embedding_service.py`
- **지원 모델**:
  - `sentence-transformers/all-MiniLM-L6-v2`: 경량, 빠름, 다국어 지원
  - `jhgan/ko-sroberta-multitask`: 한국어 특화, 높은 정확도
- **기능**:
  - 단일/다중 텍스트 벡터화
  - 배치 처리 지원
  - 자동 정규화
  - GPU/CPU 자동 감지

#### 🔄 2단계: 거리 계산 알고리즘 구현 (진행 예정)
- **목표**: 다양한 유사도 계산 방법 구현
- **구현 예정**: `crawler/similarity_utils.py`
- **알고리즘**:
  - 코사인 유사도 (벡터 기반)
  - 자카드 유사도 (집합 기반)
  - 편집 거리 (Levenshtein)
  - N-gram 유사도
  - Jaccard 유사도

#### 🔄 3단계: 임베딩 파이프라인 구축 (진행 예정)
- **목표**: 기존 영상 제목/태그에 대한 임베딩 생성
- **구현 예정**: `crawler/generate_embeddings.py`
- **기능**:
  - 기존 데이터 배치 임베딩화
  - PostgreSQL 임베딩 저장
  - 진행률 표시
  - 에러 처리 및 재시도

#### 🔄 4단계: 유사 검색어 API 개발 (진행 예정)
- **목표**: 실시간 유사 검색어 추천 엔드포인트
- **구현 예정**: `app/main.py` 확장
- **API 설계**:
  ```
  GET /similar_search?q={검색어}&limit={개수}&method={알고리즘}
  ```

### Phase 2: 자동화 및 최적화

#### 🔄 5단계: 데이터 처리 자동화 (진행 예정)
- **목표**: 새로운 데이터 수집 시 자동으로 임베딩 생성
- **구현 예정**:
  - 기존 크롤링 파이프라인에 임베딩 생성 단계 추가
  - `crawler/scheduler.py` 생성
  - Docker Compose에 자동화 서비스 추가

#### 🔄 6단계: 성능 최적화 (진행 예정)
- **목표**: 대용량 데이터에서도 빠른 검색
- **구현 예정**:
  - PostgreSQL 인덱스 최적화
  - OpenSearch 벡터 검색 설정
  - 캐싱 레이어 추가 (Redis 활용)

### Phase 3: 프론트엔드 개발

#### 🔄 7단계: 단일 페이지 인터페이스 (진행 예정)
- **목표**: 사용자 친화적인 검색 인터페이스
- **기능**:
  - 검색어 입력 및 실시간 검색
  - 유사 검색어 목록 표시
  - 검색 결과 시각화
- **기술**: HTML/CSS/JavaScript 또는 React/Vue.js

## 🎯 현재 진행 상황

### ✅ 완료된 작업
1. **프로젝트 구조 분석**: 모듈별 기능과 상호작용 파악
2. **데이터 흐름 분석**: 수집부터 검색까지의 전체 파이프라인 이해
3. **검색 컴포넌트 식별**: 기존 시스템에서 활용 가능한 요소들 파악
4. **기능 설계**: 거리 기반 검색어 유사도 기능 전체 설계
5. **벡터 임베딩 모델 설정**: 한국어 텍스트 벡터화 서비스 구현

### 🔄 현재 작업
- **1단계 완료**: `crawler/embedding_service.py` 구현
- **문서화**: `crawler/README.md` 업데이트
- **의존성 관리**: `crawler/requirements.txt` 업데이트

### 📋 다음 작업
- **2단계 시작**: 거리 계산 알고리즘 구현
- **테스트**: 임베딩 서비스 동작 확인
- **최적화**: 성능 및 메모리 사용량 개선

## 🛠️ 기술 스택

### 백엔드
- **Python 3.12**: 메인 개발 언어
- **Sentence-Transformers**: 벡터 임베딩
- **scikit-learn**: 유사도 계산
- **NumPy**: 수치 계산
- **PostgreSQL**: 데이터 저장
- **OpenSearch**: 검색 엔진

### 프론트엔드 (예정)
- **HTML/CSS/JavaScript**: 기본 웹 인터페이스
- **또는 React/Vue.js**: 고급 SPA 인터페이스

## 📊 성능 목표

### 임베딩 생성
- **all-MiniLM-L6-v2**: ~200개/분
- **ko-sroberta-multitask**: ~100개/분

### 유사도 계산
- **코사인 유사도**: ~1000개/초
- **자카드 유사도**: ~5000개/초
- **편집 거리**: ~1000개/초

### API 응답 시간
- **단일 검색어**: <100ms
- **배치 검색**: <500ms

## 🔧 개발 환경 설정

### 필수 요구사항
- Python 3.12+
- PostgreSQL 17+
- OpenSearch 2.13+
- 최소 8GB RAM
- 최소 20GB 디스크

### 권장 사항
- GPU (CUDA 지원)
- 16GB+ RAM
- SSD 저장소

## 📚 참고 자료

- [Sentence-Transformers 문서](https://www.sbert.net/)
- [scikit-learn 유사도 메트릭](https://scikit-learn.org/stable/modules/metrics.html)
- [PostgreSQL 벡터 확장](https://github.com/pgvector/pgvector)
- [OpenSearch 벡터 검색](https://opensearch.org/docs/latest/search-plugins/knn/)

## 🤝 기여 가이드

1. 각 단계별로 브랜치 생성
2. 기능 구현 후 테스트 코드 작성
3. 문서 업데이트
4. 코드 리뷰 후 머지

## 📄 라이선스

MIT License
