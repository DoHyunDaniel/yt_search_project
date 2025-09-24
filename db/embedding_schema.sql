-- 임베딩 저장을 위한 스키마 확장
-- 기존 yt_schema.sql에 추가할 내용

-- 임베딩 테이블 생성
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

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_video_embeddings_video_id 
ON yt.video_embeddings(video_id);

CREATE INDEX IF NOT EXISTS idx_video_embeddings_type 
ON yt.video_embeddings(embedding_type);

CREATE INDEX IF NOT EXISTS idx_video_embeddings_model 
ON yt.video_embeddings(model_name);

-- 벡터 유사도 검색을 위한 인덱스 (pgvector 확장 필요)
-- pgvector가 설치된 경우에만 실행
-- CREATE INDEX IF NOT EXISTS idx_video_embeddings_vector_cosine 
-- ON yt.video_embeddings USING ivfflat (embedding_vector vector_cosine_ops) 
-- WITH (lists = 100);

-- 임베딩 통계를 위한 뷰
CREATE OR REPLACE VIEW yt.embedding_stats AS
SELECT 
    embedding_type,
    model_name,
    COUNT(*) as count,
    AVG(embedding_dim) as avg_dimension,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM yt.video_embeddings
GROUP BY embedding_type, model_name;

-- 유사도 검색을 위한 함수 (코사인 유사도)
CREATE OR REPLACE FUNCTION yt.cosine_similarity(vec1 FLOAT[], vec2 FLOAT[])
RETURNS FLOAT AS $$
DECLARE
    dot_product FLOAT := 0;
    norm1 FLOAT := 0;
    norm2 FLOAT := 0;
    i INTEGER;
BEGIN
    -- 벡터 길이 확인
    IF array_length(vec1, 1) != array_length(vec2, 1) THEN
        RETURN 0;
    END IF;
    
    -- 내적과 노름 계산
    FOR i IN 1..array_length(vec1, 1) LOOP
        dot_product := dot_product + vec1[i] * vec2[i];
        norm1 := norm1 + vec1[i] * vec1[i];
        norm2 := norm2 + vec2[i] * vec2[i];
    END LOOP;
    
    -- 코사인 유사도 계산
    IF norm1 = 0 OR norm2 = 0 THEN
        RETURN 0;
    END IF;
    
    RETURN dot_product / (sqrt(norm1) * sqrt(norm2));
END;
$$ LANGUAGE plpgsql;

-- 유사 영상 검색 함수
CREATE OR REPLACE FUNCTION yt.find_similar_videos(
    query_vector FLOAT[],
    embedding_type TEXT DEFAULT 'title',
    model_name TEXT DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',
    limit_count INTEGER DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.5
)
RETURNS TABLE(
    video_id UUID,
    video_yid TEXT,
    title TEXT,
    similarity_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.id,
        v.video_yid,
        v.title,
        yt.cosine_similarity(query_vector, ve.embedding_vector) as similarity_score
    FROM yt.video_embeddings ve
    JOIN yt.videos v ON v.id = ve.video_id
    WHERE ve.embedding_type = find_similar_videos.embedding_type
      AND ve.model_name = find_similar_videos.model_name
      AND yt.cosine_similarity(query_vector, ve.embedding_vector) >= similarity_threshold
    ORDER BY similarity_score DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- 임베딩 생성 통계 함수
CREATE OR REPLACE FUNCTION yt.get_embedding_progress()
RETURNS TABLE(
    total_videos INTEGER,
    embedded_videos INTEGER,
    progress_percent FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*)::INTEGER FROM yt.videos) as total_videos,
        (SELECT COUNT(DISTINCT video_id)::INTEGER FROM yt.video_embeddings) as embedded_videos,
        ROUND(
            (SELECT COUNT(DISTINCT video_id)::NUMERIC FROM yt.video_embeddings) / 
            (SELECT COUNT(*)::NUMERIC FROM yt.videos) * 100, 
            2
        ) as progress_percent;
END;
$$ LANGUAGE plpgsql;
