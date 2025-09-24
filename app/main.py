from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, psycopg2
import psycopg2.extras
import numpy as np
from typing import List, Dict, Optional
from opensearchpy import OpenSearch

# 임베딩 및 유사도 계산을 위한 모듈 (상대 경로로 임포트)
import sys
sys.path.append('../crawler')
from embedding_service import EmbeddingService
from similarity_utils import SimilarityCalculator

app = FastAPI(
    title="YouTube 검색어 유사도 API",
    description="YouTube 영상 검색 및 유사 검색어 추천 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수로 서비스 초기화
embedding_service = None
similarity_calculator = None

def get_embedding_service():
    """임베딩 서비스 싱글톤"""
    global embedding_service
    if embedding_service is None:
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        embedding_service = EmbeddingService(model_name)
    return embedding_service

def get_similarity_calculator():
    """유사도 계산기 싱글톤"""
    global similarity_calculator
    if similarity_calculator is None:
        similarity_calculator = SimilarityCalculator()
    return similarity_calculator

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST","localhost"),
        port=os.getenv("DB_PORT","5432"),
        dbname=os.getenv("DB_NAME","yt"),
        user=os.getenv("DB_USER","app"),
        password=os.getenv("DB_PASSWORD","app1234"),
    )

def get_os_client() -> OpenSearch:
    host = os.getenv("OS_HOST", "https://yt-os:9200")
    user = os.getenv("OS_USER", "admin")
    password = os.getenv("OS_PASSWORD", "App1234!@#")
    # 개발환경: 인증/SSL은 켜고, 인증서 검증은 끔
    return OpenSearch(hosts=[host], http_auth=(user, password), use_ssl=True, verify_certs=False)

@app.get("/health")
def health():
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            _ = cur.fetchone()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/search")
def search(q: str = "", limit: int = 10):
    sql = """
      SELECT v.id, v.title, v.published_at
      FROM yt.videos v
      WHERE v.title ILIKE %s
      ORDER BY v.published_at DESC
      LIMIT %s
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (f"%{q}%", limit))
        rows = cur.fetchall()
    return [{"id": r[0], "title": r[1], "published_at": r[2]} for r in rows]

# OpenSearch: 간단 조회 (title match)
@app.get("/os_search")
def os_search(q: str = "", size: int = 10):
    os_client = get_os_client()
    body = {
        "size": size,
        "query": {"match": {"title": q}} if q else {"match_all": {}},
        "_source": ["video_id", "title", "published_at", "channel_id"],
    }
    resp = os_client.search(index=os.getenv("OS_INDEX", "videos"), body=body)
    hits = resp.get("hits", {}).get("hits", [])
    return [{
        "id": h.get("_id"),
        "score": h.get("_score"),
        **(h.get("_source") or {})
    } for h in hits]

# Nori 분석기 인덱스 생성 (새 인덱스명 지정; 기본: videos_ko)
@app.post("/os/setup_nori")
def os_setup_nori(index: str = "videos_ko"):
    os_client = get_os_client()
    settings = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "korean": {"type": "custom", "tokenizer": "nori_tokenizer"}
                }
            }
        },
        "mappings": {
            "properties": {
                "video_id": {"type": "keyword"},
                "title": {"type": "text", "analyzer": "korean"},
                "description": {"type": "text", "analyzer": "korean"},
                "published_at": {"type": "date"},
                "channel_id": {"type": "keyword"},
                "tags": {"type": "keyword"}
            }
        }
    }
    if os_client.indices.exists(index=index):
        return {"ok": True, "message": f"index '{index}' already exists"}
    os_client.indices.create(index=index, body=settings)
    return {"ok": True, "created": index}

# 기존 인덱스 → 새 인덱스로 리인덱스 후 alias 전환 (기본: videos → videos_ko)
@app.post("/os/reindex")
def os_reindex(src: str = "videos", dest: str = "videos_ko", alias: str = "videos"):
    os_client = get_os_client()
    if not os_client.indices.exists(index=dest):
        return {"ok": False, "error": f"destination index '{dest}' does not exist. call /os/setup_nori first"}
    task = os_client.reindex(body={"source": {"index": src}, "dest": {"index": dest}}, wait_for_completion=True, request_timeout=3600)
    # alias를 신규 인덱스로 가리키도록 스왑
    actions = []
    if os_client.indices.exists_alias(name=alias):
        old = list(os_client.indices.get_alias(name=alias).keys())
        for idx in old:
            actions.append({"remove": {"index": idx, "alias": alias}})
    actions.append({"add": {"index": dest, "alias": alias}})
    os_client.indices.update_aliases({"actions": actions})
    return {"ok": True, "reindexed": task}

# ==============================
# 유사 검색어 추천 API
# ==============================

@app.get("/similar_search")
def similar_search(
    q: str,
    method: str = "cosine",
    embedding_type: str = "title",
    limit: int = 10,
    threshold: float = 0.5
):
    """
    유사 검색어 추천 API
    
    Args:
        q: 검색어
        method: 유사도 계산 방법 (cosine, jaccard, levenshtein, ngram, word_overlap, tfidf)
        embedding_type: 임베딩 타입 (title, title_tags, title_desc, full_text)
        limit: 반환할 최대 개수
        threshold: 유사도 임계값
    
    Returns:
        List[Dict]: 유사한 영상 리스트
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="검색어를 입력해주세요")
    
    try:
        if method == "cosine":
            return _cosine_similarity_search(q, embedding_type, limit, threshold)
        elif method in ["jaccard", "levenshtein", "ngram", "word_overlap"]:
            return _text_similarity_search(q, method, limit)
        elif method == "tfidf":
            return _tfidf_similarity_search(q, limit)
        else:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 방법: {method}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류 발생: {str(e)}")

def _cosine_similarity_search(q: str, embedding_type: str, limit: int, threshold: float) -> List[Dict]:
    """코사인 유사도 기반 검색"""
    # 쿼리 임베딩 생성
    embedding_service = get_embedding_service()
    query_embedding = embedding_service.encode(q, normalize=True)[0]
    
    # 데이터베이스에서 유사한 영상 검색
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    v.id,
                    v.video_yid,
                    v.title,
                    v.description,
                    v.published_at,
                    v.tags,
                    yt.cosine_similarity(%s, ve.embedding_vector) as similarity_score
                FROM yt.video_embeddings ve
                JOIN yt.videos v ON v.id = ve.video_id
                WHERE ve.embedding_type = %s
                  AND ve.model_name = %s
                  AND yt.cosine_similarity(%s, ve.embedding_vector) >= %s
                ORDER BY similarity_score DESC
                LIMIT %s
            """, (
                query_embedding.tolist(),
                embedding_type,
                embedding_service.model_name,
                query_embedding.tolist(),
                threshold,
                limit
            ))
            
            results = cur.fetchall()
            return [dict(row) for row in results]

def _text_similarity_search(q: str, method: str, limit: int) -> List[Dict]:
    """텍스트 기반 유사도 검색"""
    # 모든 영상 제목 조회
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, video_yid, title, description, published_at, tags
                FROM yt.videos
                ORDER BY published_at DESC
                LIMIT 1000
            """)
            videos = cur.fetchall()
    
    if not videos:
        return []
    
    # 유사도 계산
    similarity_calc = get_similarity_calculator()
    candidates = [video['title'] for video in videos]
    
    similar_texts = similarity_calc.find_similar_texts(
        q, candidates, method=method, top_k=limit
    )
    
    # 결과 매핑
    results = []
    for text, score in similar_texts:
        for video in videos:
            if video['title'] == text:
                results.append({
                    'id': str(video['id']),
                    'video_yid': video['video_yid'],
                    'title': video['title'],
                    'description': video['description'],
                    'published_at': video['published_at'],
                    'tags': video['tags'],
                    'similarity_score': score
                })
                break
    
    return results

def _tfidf_similarity_search(q: str, limit: int) -> List[Dict]:
    """TF-IDF 기반 유사도 검색"""
    # 모든 영상 제목 조회
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, video_yid, title, description, published_at, tags
                FROM yt.videos
                ORDER BY published_at DESC
                LIMIT 1000
            """)
            videos = cur.fetchall()
    
    if not videos:
        return []
    
    # TF-IDF 유사도 계산
    similarity_calc = get_similarity_calculator()
    candidates = [video['title'] for video in videos]
    
    similar_texts = similarity_calc.find_similar_texts(
        q, candidates, method="tfidf", top_k=limit
    )
    
    # 결과 매핑
    results = []
    for text, score in similar_texts:
        for video in videos:
            if video['title'] == text:
                results.append({
                    'id': str(video['id']),
                    'video_yid': video['video_yid'],
                    'title': video['title'],
                    'description': video['description'],
                    'published_at': video['published_at'],
                    'tags': video['tags'],
                    'similarity_score': score
                })
                break
    
    return results

@app.get("/embedding_stats")
def get_embedding_stats():
    """임베딩 통계 조회"""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # 전체 통계
                cur.execute("SELECT * FROM yt.get_embedding_progress()")
                progress = cur.fetchone()
                
                # 타입별 통계
                cur.execute("SELECT * FROM yt.embedding_stats")
                type_stats = cur.fetchall()
                
                return {
                    "progress": {
                        "total_videos": progress[0],
                        "embedded_videos": progress[1],
                        "progress_percent": float(progress[2])
                    },
                    "type_stats": [
                        {
                            "embedding_type": row[0],
                            "model_name": row[1],
                            "count": row[2],
                            "avg_dimension": float(row[3]) if row[3] else 0,
                            "first_created": row[4].isoformat() if row[4] else None,
                            "last_created": row[5].isoformat() if row[5] else None
                        }
                        for row in type_stats
                    ]
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류 발생: {str(e)}")

@app.get("/similar_keywords")
def get_similar_keywords(
    q: str,
    method: str = "jaccard",
    limit: int = 10
):
    """
    유사 키워드 추천 API (영상 제목에서 키워드 추출)
    
    Args:
        q: 검색어
        method: 유사도 계산 방법
        limit: 반환할 최대 개수
    
    Returns:
        List[Dict]: 유사한 키워드 리스트
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="검색어를 입력해주세요")
    
    try:
        # 모든 영상 제목에서 키워드 추출
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT unnest(tags) as keyword
                    FROM yt.videos
                    WHERE tags IS NOT NULL AND array_length(tags, 1) > 0
                """)
                keywords = [row[0] for row in cur.fetchall()]
        
        if not keywords:
            return []
        
        # 유사도 계산
        similarity_calc = get_similarity_calculator()
        similar_keywords = similarity_calc.find_similar_texts(
            q, keywords, method=method, top_k=limit
        )
        
        return [
            {
                "keyword": keyword,
                "similarity_score": score
            }
            for keyword, score in similar_keywords
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"키워드 검색 중 오류 발생: {str(e)}")

@app.get("/search_methods")
def get_search_methods():
    """사용 가능한 검색 방법 목록"""
    return {
        "methods": [
            {
                "name": "cosine",
                "description": "코사인 유사도 (벡터 기반, 가장 정확)",
                "requires_embedding": True
            },
            {
                "name": "jaccard",
                "description": "자카드 유사도 (N-gram 기반)",
                "requires_embedding": False
            },
            {
                "name": "levenshtein",
                "description": "편집 거리 유사도",
                "requires_embedding": False
            },
            {
                "name": "ngram",
                "description": "N-gram 유사도",
                "requires_embedding": False
            },
            {
                "name": "word_overlap",
                "description": "단어 겹침 유사도",
                "requires_embedding": False
            },
            {
                "name": "tfidf",
                "description": "TF-IDF 유사도",
                "requires_embedding": False
            }
        ],
        "embedding_types": [
            "title",
            "title_tags", 
            "title_desc",
            "full_text"
        ]
    }
