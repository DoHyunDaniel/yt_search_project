import os
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import psycopg2
import psycopg2.extras
from tqdm import tqdm

from embedding_service import EmbeddingService
from similarity_utils import SimilarityCalculator
from text_utils import clean_text


class EmbeddingPipeline:
    """
    기존 데이터에 대한 임베딩 생성 파이프라인
    
    기능:
    - 영상 제목/태그 임베딩 생성
    - PostgreSQL에 임베딩 저장
    - 배치 처리로 효율적인 처리
    - 진행률 표시 및 에러 처리
    """
    
    def __init__(self, 
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 batch_size: int = 32):
        """
        임베딩 파이프라인 초기화
        
        Args:
            model_name: 사용할 임베딩 모델
            batch_size: 배치 처리 크기
        """
        self.embedding_service = EmbeddingService(model_name)
        self.similarity_calculator = SimilarityCalculator()
        self.batch_size = batch_size
        
        # 데이터베이스 연결 설정
        self.db_config = {
            'host': os.getenv("DB_HOST", "localhost"),
            'port': int(os.getenv("DB_PORT", "5432")),
            'dbname': os.getenv("DB_NAME", "yt"),
            'user': os.getenv("DB_USER", "app"),
            'password': os.getenv("DB_PASSWORD", "app1234"),
        }
    
    def get_videos_without_embeddings(self, limit: Optional[int] = None) -> List[Dict]:
        """
        임베딩이 없는 영상들 조회
        
        Args:
            limit: 조회할 최대 개수
            
        Returns:
            List[Dict]: 영상 정보 리스트
        """
        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                query = """
                SELECT v.id, v.video_yid, v.title, v.tags, v.description
                FROM yt.videos v
                LEFT JOIN yt.video_embeddings ve ON v.id = ve.video_id
                WHERE ve.video_id IS NULL
                ORDER BY v.published_at DESC
                """
                if limit:
                    query += f" LIMIT {limit}"
                
                cur.execute(query)
                return cur.fetchall()
    
    def create_embeddings_table(self):
        """임베딩 저장을 위한 테이블 생성"""
        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                # 임베딩 테이블 생성
                cur.execute("""
                CREATE TABLE IF NOT EXISTS yt.video_embeddings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    video_id UUID NOT NULL REFERENCES yt.videos(id) ON DELETE CASCADE,
                    embedding_type TEXT NOT NULL DEFAULT 'title',
                    embedding_vector FLOAT[] NOT NULL,
                    embedding_dim INTEGER NOT NULL,
                    model_name TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(video_id, embedding_type, model_name)
                );
                """)
                
                # 인덱스 생성
                cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_video_embeddings_video_id 
                ON yt.video_embeddings(video_id);
                """)
                
                cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_video_embeddings_type 
                ON yt.video_embeddings(embedding_type);
                """)
                
                # 벡터 유사도 검색을 위한 인덱스 (PostgreSQL pgvector 확장 필요)
                try:
                    cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_video_embeddings_vector_cosine 
                    ON yt.video_embeddings USING ivfflat (embedding_vector vector_cosine_ops) 
                    WITH (lists = 100);
                    """)
                except Exception as e:
                    print(f"벡터 인덱스 생성 실패 (pgvector 미설치): {e}")
                
                conn.commit()
                print("임베딩 테이블 생성 완료")
    
    def prepare_text_for_embedding(self, video: Dict) -> Dict[str, str]:
        """
        영상 정보에서 임베딩용 텍스트 준비
        
        Args:
            video: 영상 정보 딕셔너리
            
        Returns:
            Dict[str, str]: 임베딩용 텍스트들
        """
        title = clean_text(video.get('title', ''))
        description = clean_text(video.get('description', ''))
        tags = video.get('tags', [])
        
        # 태그를 문자열로 변환
        tags_text = ' '.join(tags) if tags else ''
        
        # 제목 + 태그 조합
        title_tags = f"{title} {tags_text}".strip()
        
        # 제목 + 설명 조합
        title_desc = f"{title} {description}".strip()
        
        # 전체 텍스트 조합
        full_text = f"{title} {description} {tags_text}".strip()
        
        return {
            'title': title,
            'title_tags': title_tags,
            'title_desc': title_desc,
            'full_text': full_text
        }
    
    def generate_video_embeddings(self, video: Dict) -> Dict[str, np.ndarray]:
        """
        단일 영상에 대한 임베딩 생성
        
        Args:
            video: 영상 정보
            
        Returns:
            Dict[str, np.ndarray]: 임베딩 타입별 벡터
        """
        texts = self.prepare_text_for_embedding(video)
        embeddings = {}
        
        for text_type, text in texts.items():
            if text.strip():
                embedding = self.embedding_service.encode(text, normalize=True)
                embeddings[text_type] = embedding[0]  # 단일 벡터로 변환
            else:
                # 빈 텍스트의 경우 0 벡터
                dim = self.embedding_service.get_embedding_dimension()
                embeddings[text_type] = np.zeros(dim)
        
        return embeddings
    
    def save_embeddings(self, video_id: str, embeddings: Dict[str, np.ndarray]):
        """
        임베딩을 데이터베이스에 저장
        
        Args:
            video_id: 영상 ID
            embeddings: 임베딩 딕셔너리
        """
        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                for embedding_type, vector in embeddings.items():
                    cur.execute("""
                    INSERT INTO yt.video_embeddings 
                    (video_id, embedding_type, embedding_vector, embedding_dim, model_name)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (video_id, embedding_type, model_name)
                    DO UPDATE SET 
                        embedding_vector = EXCLUDED.embedding_vector,
                        embedding_dim = EXCLUDED.embedding_dim,
                        created_at = now()
                    """, (
                        video_id,
                        embedding_type,
                        vector.tolist(),
                        len(vector),
                        self.embedding_service.model_name
                    ))
                conn.commit()
    
    def process_videos_batch(self, videos: List[Dict]) -> Tuple[int, int]:
        """
        영상 배치 처리
        
        Args:
            videos: 처리할 영상 리스트
            
        Returns:
            Tuple[int, int]: (성공 개수, 실패 개수)
        """
        success_count = 0
        error_count = 0
        
        for video in tqdm(videos, desc="Processing videos"):
            try:
                # 임베딩 생성
                embeddings = self.generate_video_embeddings(video)
                
                # 데이터베이스 저장
                self.save_embeddings(video['id'], embeddings)
                
                success_count += 1
                
            except Exception as e:
                print(f"Error processing video {video.get('video_yid', 'unknown')}: {e}")
                error_count += 1
        
        return success_count, error_count
    
    def run(self, limit: Optional[int] = None, batch_size: Optional[int] = None):
        """
        임베딩 생성 파이프라인 실행
        
        Args:
            limit: 처리할 최대 영상 수
            batch_size: 배치 크기
        """
        if batch_size:
            self.batch_size = batch_size
        
        print("=== 임베딩 생성 파이프라인 시작 ===")
        print(f"모델: {self.embedding_service.model_name}")
        print(f"배치 크기: {self.batch_size}")
        
        # 테이블 생성
        self.create_embeddings_table()
        
        # 처리할 영상 조회
        videos = self.get_videos_without_embeddings(limit)
        print(f"처리할 영상 수: {len(videos)}")
        
        if not videos:
            print("처리할 영상이 없습니다.")
            return
        
        # 배치별 처리
        total_success = 0
        total_error = 0
        
        for i in range(0, len(videos), self.batch_size):
            batch = videos[i:i + self.batch_size]
            print(f"\n배치 {i//self.batch_size + 1}/{(len(videos)-1)//self.batch_size + 1} 처리 중...")
            
            success, error = self.process_videos_batch(batch)
            total_success += success
            total_error += error
            
            print(f"배치 완료: 성공 {success}, 실패 {error}")
        
        print(f"\n=== 파이프라인 완료 ===")
        print(f"총 성공: {total_success}")
        print(f"총 실패: {total_error}")
        print(f"성공률: {total_success/(total_success+total_error)*100:.1f}%")
    
    def get_embedding_stats(self) -> Dict:
        """임베딩 통계 조회"""
        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                # 전체 임베딩 수
                cur.execute("SELECT COUNT(*) FROM yt.video_embeddings")
                total_embeddings = cur.fetchone()[0]
                
                # 타입별 임베딩 수
                cur.execute("""
                SELECT embedding_type, COUNT(*) 
                FROM yt.video_embeddings 
                GROUP BY embedding_type
                """)
                type_counts = dict(cur.fetchall())
                
                # 모델별 임베딩 수
                cur.execute("""
                SELECT model_name, COUNT(*) 
                FROM yt.video_embeddings 
                GROUP BY model_name
                """)
                model_counts = dict(cur.fetchall())
                
                return {
                    'total_embeddings': total_embeddings,
                    'type_counts': type_counts,
                    'model_counts': model_counts
                }


def test_embedding_pipeline():
    """임베딩 파이프라인 테스트"""
    print("=== 임베딩 파이프라인 테스트 ===")
    
    # 파이프라인 초기화
    pipeline = EmbeddingPipeline(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        batch_size=5
    )
    
    # 통계 조회
    stats = pipeline.get_embedding_stats()
    print(f"현재 임베딩 수: {stats['total_embeddings']}")
    print(f"타입별 분포: {stats['type_counts']}")
    print(f"모델별 분포: {stats['model_counts']}")
    
    # 소규모 테스트 실행
    print("\n소규모 테스트 실행 (최대 10개 영상)...")
    pipeline.run(limit=10, batch_size=2)


if __name__ == "__main__":
    test_embedding_pipeline()
