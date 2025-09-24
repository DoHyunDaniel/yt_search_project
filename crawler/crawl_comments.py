import os
from datetime import datetime, timedelta
from typing import Iterable, Optional

from dotenv import load_dotenv
from googleapiclient.discovery import build
import psycopg2


load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
YT = build("youtube", "v3", developerKey=API_KEY)

DB = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "yt"),
    user=os.getenv("DB_USER", "app"),
    password=os.getenv("DB_PASSWORD", "app1234"),
)


def fetch_comment_threads(video_id: str, max_total: int = 500) -> Iterable[dict]:
    fetched = 0
    page_token: Optional[str] = None
    while True:
        req = YT.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            pageToken=page_token,
            order="time",
            textFormat="plainText",
        )
        try:
            resp = req.execute()
            for item in resp.get("items", []):
                yield item
                fetched += 1
                if fetched >= max_total:
                    return
            page_token = resp.get("nextPageToken")
            if not page_token:
                return
        except Exception as e:
            print(f"댓글 수집 오류 (비디오 {video_id}): {e}")
            return


def upsert_comment(cur, video_db_id, comment_item):
    snip = comment_item["snippet"]["topLevelComment"]["snippet"]
    comment_yid = comment_item["snippet"]["topLevelComment"]["id"]
    author_channel_id = snip.get("authorChannelId", {}).get("value")
    author_name = snip.get("authorDisplayName")
    text_raw = snip.get("textDisplay") or snip.get("textOriginal") or ""
    like_count = snip.get("likeCount") or 0
    published_at = snip.get("publishedAt")

    # 존재 여부 확인 (comment_yid 기준)
    cur.execute(
        "SELECT id FROM yt.comments WHERE platform='youtube' AND comment_yid=%s LIMIT 1",
        (comment_yid,),
    )
    exists = cur.fetchone()
    if exists:
        return exists[0]

    cur.execute(
        """
        INSERT INTO yt.comments (
          platform, comment_yid, video_id, author_yid, author_name,
          text_raw, published_at, like_count, sentiment, sentiment_score, metadata
        )
        VALUES (
          'youtube', %s, %s, %s, %s,
          %s, %s, %s, NULL, NULL, '{}'::jsonb
        )
        RETURNING id
        """,
        (
            comment_yid,
            video_db_id,
            author_channel_id,
            author_name,
            text_raw,
            published_at,
            like_count,
        ),
    )
    return cur.fetchone()[0]


def get_recent_video_ids(cur, days: int = 7, limit: int = 50) -> Iterable[tuple[str, str]]:
    cur.execute(
        """
        SELECT id, video_yid
        FROM yt.videos
        WHERE published_at >= now() - interval '%s days'
        ORDER BY published_at DESC
        LIMIT %s
        """,
        (days, limit),
    )
    return cur.fetchall()


def collect_comments(days: int = 7, per_video_limit: int = 200, video_ids: Optional[list[str]] = None):
    with psycopg2.connect(**DB) as conn, conn.cursor() as cur:
        rows: Iterable[tuple[str, str]]
        if video_ids:
            # 주어진 video_yid → 내부 id 조회
            cur.execute(
                "SELECT id, video_yid FROM yt.videos WHERE video_yid = ANY(%s)",
                (video_ids,),
            )
            rows = cur.fetchall()
        else:
            rows = get_recent_video_ids(cur, days=days, limit=50)

        for video_db_id, video_yid in rows:
            print("Collecting comments for", video_yid)
            for item in fetch_comment_threads(video_yid, max_total=per_video_limit):
                _cid = upsert_comment(cur, video_db_id, item)
            conn.commit()
            print("Done:", video_yid)


if __name__ == "__main__":
    collect_comments()


