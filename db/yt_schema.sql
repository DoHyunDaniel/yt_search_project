-- YouTube Travel Search/Recommend - Core Schema (PostgreSQL)
-- Requires: uuid-ossp OR pgcrypto for UUID generation, and btree_gin for better indexing utilities.

-- Extensions (enable if not already)
CREATE EXTENSION IF NOT EXISTS pgcrypto;         -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS btree_gin;        -- useful for multi-column GIN operations
CREATE EXTENSION IF NOT EXISTS pg_trgm;          -- trigram for text search (optional)

-- Dedicated schema
CREATE SCHEMA IF NOT EXISTS yt;
SET search_path TO yt, public;

-- ==============================
-- 1) Reference: channels
-- ==============================
CREATE TABLE IF NOT EXISTS channels (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform        TEXT NOT NULL DEFAULT 'youtube',                       -- 'youtube' 유지 (확장 가능)
    channel_yid     TEXT NOT NULL,                                         -- YouTube channelId
    title           TEXT NOT NULL,
    description     TEXT,
    country_code    TEXT,                                                  -- ISO-3166-1 alpha-2 (e.g., KR, JP)
    custom_url      TEXT,
    thumbnails      JSONB,                                                 -- {default: url, medium: url, high: url}
    stats           JSONB,                                                 -- {subscribers, videoCount, viewCount...}
    tags            TEXT[],
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,                    -- 자유 확장 필드
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(platform, channel_yid)
);

CREATE INDEX IF NOT EXISTS idx_channels_title_trgm ON channels USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_channels_tags ON channels USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_channels_metadata ON channels USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_channels_stats ON channels USING GIN (stats);

-- ==============================
-- 2) Core: videos
-- ==============================
CREATE TABLE IF NOT EXISTS videos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform        TEXT NOT NULL DEFAULT 'youtube',
    video_yid       TEXT NOT NULL,                                         -- YouTube videoId
    channel_id      UUID NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT,
    published_at    TIMESTAMPTZ,                                           -- video publish date
    duration_sec    INTEGER CHECK (duration_sec IS NULL OR duration_sec >= 0),
    language_code   TEXT,                                                  -- ISO-639-1 (e.g., ko, en, ja)
    thumbnails      JSONB,                                                 -- {default, medium, high, maxres}
    stats           JSONB,                                                 -- {viewCount, likeCount, commentCount ...}
    tags            TEXT[],
    sentiment_score NUMERIC(5,4),                                          -- optional aggregated from comments (-1~1)
    topic_labels    TEXT[],                                                -- NLP topic tags
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(platform, video_yid)
);

CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_videos_published_at ON videos(published_at);
CREATE INDEX IF NOT EXISTS idx_videos_title_trgm ON videos USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_videos_tags ON videos USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_videos_topic_labels ON videos USING GIN (topic_labels);
CREATE INDEX IF NOT EXISTS idx_videos_metadata ON videos USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_videos_stats ON videos USING GIN (stats);

-- Trigger to maintain updated_at
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_channels_updated_at
BEFORE UPDATE ON channels FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_videos_updated_at
BEFORE UPDATE ON videos FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_places_updated_at
BEFORE UPDATE ON places FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ==============================
-- 3) Reference: places (geocoding)
-- ==============================
CREATE TABLE IF NOT EXISTS places (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,                                         -- 장소명 (예: '제주 성산일출봉')
    country_code    TEXT,                                                  -- ISO-3166-1
    admin1          TEXT,                                                  -- 시/도
    admin2          TEXT,                                                  -- 시/군/구
    lat             NUMERIC(10,6),
    lon             NUMERIC(10,6),
    address         TEXT,
    external_refs   JSONB,                                                 -- {kakao_place_id, google_place_id, naver_place_id, ...}
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_places_name_trgm ON places USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_places_geo ON places (lat, lon);
CREATE INDEX IF NOT EXISTS idx_places_metadata ON places USING GIN (metadata);

-- ==============================
-- 4) Bridge: video_places (N:M)
-- ==============================
CREATE TABLE IF NOT EXISTS video_places (
    video_id        UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    place_id        UUID NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    confidence      NUMERIC(5,4) CHECK (confidence >= 0 AND confidence <= 1),
    source          TEXT NOT NULL DEFAULT 'nlp',                            -- 'nlp' | 'manual' | 'heuristic'
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (video_id, place_id)
);

CREATE INDEX IF NOT EXISTS idx_video_places_place ON video_places(place_id);
CREATE INDEX IF NOT EXISTS idx_video_places_metadata ON video_places USING GIN (metadata);

-- ==============================
-- 5) Comments (large; consider partitioning by month)
-- ==============================
-- Parent table
CREATE TABLE IF NOT EXISTS comments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform        TEXT NOT NULL DEFAULT 'youtube',
    comment_yid     TEXT,                                                  -- optional: YouTube commentId
    video_id        UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    author_yid      TEXT,                                                  -- YouTube author channel id (nullable)
    author_name     TEXT,
    text_raw        TEXT NOT NULL,
    text_clean      TEXT,                                                  -- normalized/cleaned text
    lang            TEXT,                                                  -- detected language
    like_count      INTEGER DEFAULT 0,
    published_at    TIMESTAMPTZ,
    sentiment       TEXT CHECK (sentiment IN ('neg','neu','pos')),
    sentiment_score NUMERIC(5,4),                                          -- -1.0000 ~ 1.0000
    keywords        TEXT[],                                                -- keyphrase extraction
    toxicity_score  NUMERIC(5,4),                                          -- optional moderation
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
) PARTITION BY RANGE (published_at);

-- Monthly partitions helper example (create rolling partitions via scheduler)
-- CREATE TABLE IF NOT EXISTS comments_2025_09 PARTITION OF comments
--   FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');

CREATE INDEX IF NOT EXISTS idx_comments_video_id ON comments USING btree (video_id);
CREATE INDEX IF NOT EXISTS idx_comments_published_at ON comments USING btree (published_at);
CREATE INDEX IF NOT EXISTS idx_comments_text_trgm ON comments USING GIN (text_raw gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_comments_keywords ON comments USING GIN (keywords);
CREATE INDEX IF NOT EXISTS idx_comments_metadata ON comments USING GIN (metadata);

-- ==============================
-- 6) Feature Store (compact; per video/day or per place/day)
-- ==============================
CREATE TABLE IF NOT EXISTS features (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type     TEXT NOT NULL CHECK (entity_type IN ('video','place','channel')),  -- 대상 유형
    entity_id       UUID NOT NULL,                                                     -- FK-like (soft link)
    feature_date    DATE NOT NULL,                                                     -- 스냅샷 날짜
    features        JSONB NOT NULL,                                                    -- {"wc":{"맛집":12,...},"emb":[...], "topic":[...], "stat":{...}}
    version         TEXT NOT NULL DEFAULT 'v1',                                        -- 피처 버전
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (entity_type, entity_id, feature_date, version)
);

CREATE INDEX IF NOT EXISTS idx_features_entity ON features(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_features_date ON features(feature_date);
CREATE INDEX IF NOT EXISTS idx_features_gin ON features USING GIN (features);

-- ==============================
-- 7) Trends (aggregated KPIs by period)
-- ==============================
CREATE TABLE IF NOT EXISTS trends (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_type      TEXT NOT NULL CHECK (scope_type IN ('global','place','channel','keyword')),
    scope_id        UUID,                                                                  -- nullable for 'global'
    keyword         TEXT,                                                                  -- nullable unless scope_type='keyword'
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    metrics         JSONB NOT NULL,                                                        -- {"views":12345,"likes":...,"growth":0.42}
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (period_end >= period_start),
    UNIQUE(scope_type, scope_id, keyword, period_start, period_end)
);

CREATE INDEX IF NOT EXISTS idx_trends_scope ON trends(scope_type, scope_id);
CREATE INDEX IF NOT EXISTS idx_trends_period ON trends(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_trends_metrics ON trends USING GIN (metrics);

-- ==============================
-- 8) Ingest bookkeeping (optional but recommended)
-- ==============================
CREATE TABLE IF NOT EXISTS ingest_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type        TEXT NOT NULL CHECK (job_type IN ('crawl','etl','nlp','index','geocode')),
    params          JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','failed')),
    error_message   TEXT,
    stats           JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ingest_jobs_status ON ingest_jobs(status);
CREATE INDEX IF NOT EXISTS idx_ingest_jobs_started ON ingest_jobs(started_at);
CREATE INDEX IF NOT EXISTS idx_ingest_jobs_params ON ingest_jobs USING GIN (params);

-- ==============================
-- 9) Materialized views (illustrative)
-- ==============================
-- Top videos (last 30 days) by engagement (views + likes * weight)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_top_videos_30d AS
SELECT
  v.id,
  v.title,
  v.published_at,
  (COALESCE((v.stats->>'viewCount')::bigint,0)
   + 5 * COALESCE((v.stats->>'likeCount')::bigint,0)) AS engagement_score
FROM videos v
WHERE v.published_at >= now() - interval '30 days'
ORDER BY engagement_score DESC;

CREATE INDEX IF NOT EXISTS idx_mv_top_videos_30d ON mv_top_videos_30d(engagement_score DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_top_videos_30d_unique ON mv_top_videos_30d (id);

-- ==============================

-- psql -U app -d yt 로 접속한 상태에서 실행하거나, -c 로 한 줄씩 실행해도 됨

-- 1) 깨끗하게 재시도: 기존 comments가 일부라도 만들어졌다면 지움
DROP TABLE IF EXISTS yt.comments CASCADE;

-- 2) comments 재생성: published_at 파티셔닝 + (id, published_at) 복합 PK
CREATE TABLE yt.comments (
    id              UUID NOT NULL DEFAULT gen_random_uuid(),
    platform        TEXT NOT NULL DEFAULT 'youtube',
    comment_yid     TEXT,
    video_id        UUID NOT NULL REFERENCES yt.videos(id) ON DELETE CASCADE,
    author_yid      TEXT,
    author_name     TEXT,
    text_raw        TEXT NOT NULL,
    text_clean      TEXT,
    lang            TEXT,
    like_count      INTEGER DEFAULT 0,
    published_at    TIMESTAMPTZ NOT NULL,
    sentiment       TEXT CHECK (sentiment IN ('neg','neu','pos')),
    sentiment_score NUMERIC(5,4),
    keywords        TEXT[],
    toxicity_score  NUMERIC(5,4),
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT comments_pk PRIMARY KEY (id, published_at)
) PARTITION BY RANGE (published_at);

-- 3) 필요한 인덱스 재생성
CREATE INDEX idx_comments_video_id      ON yt.comments USING btree (video_id);
CREATE INDEX idx_comments_published_at  ON yt.comments USING btree (published_at);
CREATE INDEX idx_comments_text_trgm     ON yt.comments USING GIN (text_raw gin_trgm_ops);
CREATE INDEX idx_comments_keywords      ON yt.comments USING GIN (keywords);
CREATE INDEX idx_comments_metadata      ON yt.comments USING GIN (metadata);



-- 4) 월별 파티션 생성 (예시)
CREATE TABLE IF NOT EXISTS comments_2025_09 PARTITION OF comments
FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');

CREATE TABLE IF NOT EXISTS comments_2025_10 PARTITION OF comments
FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
-- Refresh helper:
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_top_videos_30d;

-- ==============================
-- 10) Row Level Security hooks (optional placeholders)
-- (Enable RLS only if you add multi-tenant users later)
-- ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY ...

-- End of schema
