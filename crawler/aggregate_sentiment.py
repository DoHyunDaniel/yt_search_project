import os
from datetime import date, timedelta
from typing import Iterable

from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
from opensearchpy import OpenSearch


load_dotenv()

DB = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "yt"),
    user=os.getenv("DB_USER", "app"),
    password=os.getenv("DB_PASSWORD", "app1234"),
)

def get_os_client() -> OpenSearch:
    host = os.getenv("OS_HOST", "https://localhost:9200")
    user = os.getenv("OS_USER", "admin")
    password = os.getenv("OS_PASSWORD", "App1234!@#")
    return OpenSearch(hosts=[host], http_auth=(user, password), use_ssl=True, verify_certs=False)


def aggregate_video_sentiment(cur, days: int = 30) -> Iterable[tuple]:
    cur.execute(
        """
        SELECT v.id AS video_uuid,
               v.video_yid,
               AVG(c.sentiment_score)::float AS avg_score,
               COUNT(*) AS total_cnt,
               SUM((c.sentiment = 'pos')::int) AS pos_cnt,
               SUM((c.sentiment = 'neg')::int) AS neg_cnt
        FROM yt.comments c
        JOIN yt.videos v ON v.id = c.video_id
        WHERE c.sentiment_score IS NOT NULL
          AND c.published_at >= now() - interval '%s days'
        GROUP BY v.id, v.video_yid
        """,
        (days,),
    )
    return cur.fetchall()


def upsert_features(cur, video_uuid, feature_date: date, payload: dict):
    cur.execute(
        """
        INSERT INTO yt.features (entity_type, entity_id, feature_date, features)
        VALUES ('video', %s, %s, %s::jsonb)
        ON CONFLICT (entity_type, entity_id, feature_date, version)
        DO UPDATE SET features = EXCLUDED.features
        """,
        (video_uuid, feature_date, psycopg2.extras.Json(payload)),
    )


def upsert_global_trend(cur, period_days: int, metrics: dict):
    start = date.today() - timedelta(days=period_days)
    end = date.today()
    cur.execute(
        """
        INSERT INTO yt.trends (scope_type, scope_id, keyword, period_start, period_end, metrics)
        VALUES ('global', NULL, NULL, %s, %s, %s::jsonb)
        ON CONFLICT (scope_type, scope_id, keyword, period_start, period_end)
        DO UPDATE SET metrics = EXCLUDED.metrics
        """,
        (start, end, psycopg2.extras.Json(metrics)),
    )


def update_os_avg_sentiment(os_client: OpenSearch, index: str, video_yid: str, avg_score: float):
    try:
        os_client.update(index=index, id=video_yid, body={"doc": {"avg_sentiment_score": avg_score}})
    except Exception as e:
        print("OS update failed for", video_yid, e)


def run(days: int = 30, os_index: str = None):
    os_index = os_index or os.getenv("OS_INDEX", "videos")
    feat_date = date.today()
    os_client = get_os_client()
    with psycopg2.connect(**DB) as conn:
        with conn.cursor() as cur:
            rows = aggregate_video_sentiment(cur, days=days)
            total_pos = 0
            total_neg = 0
            total = 0
            for video_uuid, video_yid, avg_score, total_cnt, pos_cnt, neg_cnt in rows:
                payload = {
                    "avg_sentiment_score": float(avg_score) if avg_score is not None else None,
                    "counts": {
                        "total": int(total_cnt),
                        "pos": int(pos_cnt or 0),
                        "neg": int(neg_cnt or 0),
                    },
                    "window_days": days,
                }
                upsert_features(cur, video_uuid, feat_date, payload)
                if avg_score is not None and video_yid:
                    update_os_avg_sentiment(os_client, os_index, video_yid, float(avg_score))

                total += int(total_cnt)
                total_pos += int(pos_cnt or 0)
                total_neg += int(neg_cnt or 0)

            pos_rate = (total_pos / total) if total else 0.0
            neg_rate = (total_neg / total) if total else 0.0
            upsert_global_trend(
                cur,
                period_days=days,
                metrics={"total_comments": total, "pos_rate": pos_rate, "neg_rate": neg_rate},
            )
        conn.commit()
    print("Aggregated", len(rows), "videos; updated features/trends and OpenSearch")


if __name__ == "__main__":
    run()


