#!/usr/bin/env python3
"""
간단한 API 서버 (테스트용)
"""

import os
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import psycopg2
import psycopg2.extras

# 환경 설정
os.environ["DB_PORT"] = "55432"

# 데이터베이스 연결 설정
DB_CONFIG = {
    'host': os.getenv("DB_HOST", "localhost"),
    'port': int(os.getenv("DB_PORT", "5432")),
    'dbname': os.getenv("DB_NAME", "yt"),
    'user': os.getenv("DB_USER", "app"),
    'password': os.getenv("DB_PASSWORD", "app1234"),
}

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """GET 요청 처리"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        # CORS 헤더 설정
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        try:
            if path == '/health':
                self.handle_health()
            elif path == '/search_methods':
                self.handle_search_methods()
            elif path == '/embedding_stats':
                self.handle_embedding_stats()
            elif path == '/similar_search':
                self.handle_similar_search(query_params)
            elif path == '/similar_keywords':
                self.handle_similar_keywords(query_params)
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")
    
    def handle_health(self):
        """헬스 체크"""
        try:
            with psycopg2.connect(**DB_CONFIG) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    _ = cur.fetchone()
            response = {"ok": True}
        except Exception as e:
            response = {"ok": False, "error": str(e)}
        
        self.wfile.write(json.dumps(response).encode())
    
    def handle_search_methods(self):
        """검색 방법 목록"""
        response = {
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
        self.wfile.write(json.dumps(response).encode())
    
    def handle_embedding_stats(self):
        """임베딩 통계"""
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # 전체 통계
                cur.execute("SELECT * FROM yt.get_embedding_progress()")
                progress = cur.fetchone()
                
                # 타입별 통계
                cur.execute("SELECT * FROM yt.embedding_stats")
                type_stats = cur.fetchall()
                
                response = {
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
        
        self.wfile.write(json.dumps(response).encode())
    
    def handle_similar_search(self, params):
        """행궁 관련 유사 검색"""
        q = params.get('q', [''])[0]
        method = params.get('method', ['jaccard'])[0]
        limit = int(params.get('limit', ['10'])[0])
        
        # 입력 검증 및 정제
        if not q or not q.strip():
            self.send_error(400, "검색어를 입력해주세요")
            return
            
        # 검색어 길이 제한 (XSS 방어)
        if len(q) > 100:
            self.send_error(400, "검색어는 100자 이하로 입력해주세요")
            return
            
        # 특수문자 필터링 (기본적인 XSS 방어)
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', 'script', 'javascript', 'onload', 'onerror']
        q_lower = q.lower()
        for char in dangerous_chars:
            if char in q_lower:
                self.send_error(400, "Invalid characters detected")
                return
        
        # 행궁 관련 키워드와의 유사도 계산
        try:
            from palace_keywords import find_most_similar_keywords
            similar_keywords = find_most_similar_keywords(q, top_k=3)
            
            if not similar_keywords or similar_keywords[0][1] < 0.05:
                # 행궁과 관련성이 낮은 경우 빈 결과 반환 (임계값 0.1 → 0.05로 낮춤)
                self.wfile.write(json.dumps([]).encode())
                return
                
            # 가장 유사한 키워드로 검색
            best_keyword = similar_keywords[0][0]
            print(f"사용자 입력: '{q}' -> 가장 유사한 행궁 키워드: '{best_keyword}'")
            
        except ImportError:
            # palace_keywords 모듈이 없는 경우 기본 검색
            best_keyword = q
            print(f"기본 검색 사용: '{q}'")
        
        # 간단한 텍스트 기반 검색 (임베딩 없이)
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # SQL Injection 방어: 파라미터화된 쿼리 사용
                # 더 유연한 검색을 위해 여러 키워드로 검색
                search_terms = [best_keyword]
                if similar_keywords:
                    # 상위 3개 키워드 모두 사용
                    for keyword, score in similar_keywords[:3]:
                        if keyword not in search_terms:
                            search_terms.append(keyword)
                
                # OR 조건으로 여러 키워드 검색
                where_conditions = " OR ".join(["title ILIKE %s"] * len(search_terms))
                search_params = [f"%{term}%" for term in search_terms] + [limit]
                
                cur.execute(f"""
                    SELECT id, video_yid, title, description, published_at, tags
                    FROM yt.videos
                    WHERE {where_conditions}
                    ORDER BY published_at DESC
                    LIMIT %s
                """, search_params)
                
                videos = cur.fetchall()
                
                # 간단한 유사도 계산 (제목에 행궁 키워드가 포함된 정도)
                results = []
                for video in videos:
                    title = video['title'].lower()
                    original_query = q.lower()
                    matched_keyword = best_keyword.lower()
                    
                    # 원본 쿼리와 매칭된 키워드 모두 고려한 유사도 계산
                    similarity = 0.0
                    
                    # 1. 원본 쿼리가 제목에 포함된 경우
                    if original_query in title:
                        similarity += 0.7 * (len(original_query) / len(title))
                    
                    # 2. 매칭된 행궁 키워드가 제목에 포함된 경우
                    if matched_keyword in title:
                        similarity += 0.3 * (len(matched_keyword) / len(title))
                    
                    # 3. 공통 단어 개수 기반
                    if similarity == 0:
                        query_words = set(original_query.split())
                        title_words = set(title.split())
                        common_words = query_words.intersection(title_words)
                        similarity = len(common_words) / max(len(query_words), 1)
                    
                    results.append({
                        'id': str(video['id']),
                        'video_yid': video['video_yid'],
                        'title': video['title'],
                        'description': video['description'],
                        'published_at': video['published_at'].isoformat() if video['published_at'] else None,
                        'tags': video['tags'],
                        'similarity_score': similarity,
                        'matched_keyword': best_keyword  # 어떤 키워드로 매칭되었는지 표시
                    })
                
                # 유사도 순으로 정렬
                results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        self.wfile.write(json.dumps(results).encode())
    
    def handle_similar_keywords(self, params):
        """유사 키워드"""
        q = params.get('q', [''])[0]
        method = params.get('method', ['jaccard'])[0]
        limit = int(params.get('limit', ['10'])[0])
        
        if not q.strip():
            self.send_error(400, "검색어를 입력해주세요")
            return
        
        # 모든 태그에서 키워드 추출
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT unnest(tags) as keyword
                    FROM yt.videos
                    WHERE tags IS NOT NULL AND array_length(tags, 1) > 0
                """)
                keywords = [row[0] for row in cur.fetchall()]
        
        if not keywords:
            self.wfile.write(json.dumps([]).encode())
            return
        
        # 간단한 유사도 계산
        results = []
        for keyword in keywords:
            if q.lower() in keyword.lower():
                similarity = len(q) / len(keyword)
            else:
                # 공통 문자 개수 기반
                common_chars = set(q.lower()).intersection(set(keyword.lower()))
                similarity = len(common_chars) / max(len(set(q.lower())), 1)
            
            results.append({
                'keyword': keyword,
                'similarity_score': similarity
            })
        
        # 유사도 순으로 정렬하고 상위 limit개 반환
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        results = results[:limit]
        
        self.wfile.write(json.dumps(results).encode())

def main():
    """메인 함수"""
    port = 8000
    server = HTTPServer(('localhost', port), APIHandler)
    print(f"API 서버가 http://localhost:{port} 에서 실행 중입니다.")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
        server.shutdown()

if __name__ == "__main__":
    main()
