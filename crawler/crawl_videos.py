import os
from datetime import datetime, timedelta

try:
	from dotenv import load_dotenv
except ImportError as e:
	raise SystemExit("python-dotenv가 설치되어 있지 않습니다. 'pip install python-dotenv'로 설치하세요.") from e

try:
	from googleapiclient.discovery import build
except ImportError as e:
	raise SystemExit("google-api-python-client가 설치되어 있지 않습니다. 'pip install google-api-python-client'로 설치하세요.") from e

psycopg3 = None
try:
	import psycopg as psycopg3  # psycopg3 (optional, preferred)  # pyright: ignore[reportMissingImports]
except Exception:
	psycopg3 = None

try:
	import psycopg2
except ImportError as e:
	if psycopg3 is None:
		raise SystemExit("DB 드라이버가 없습니다. 'pip install psycopg[binary]' 또는 'pip install psycopg2-binary'로 설치하세요.") from e

try:
	from opensearchpy import OpenSearch
except ImportError as e:
	raise SystemExit("opensearch-py가 설치되어 있지 않습니다. 'pip install opensearch-py'로 설치하세요.") from e

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
YT = build("youtube", "v3", developerKey=API_KEY)

DB = dict(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

OS = OpenSearch(
    hosts=[os.getenv("OS_HOST", "https://localhost:9200")],
    http_auth=(os.getenv("OS_USER", "admin"), os.getenv("OS_PASSWORD", "App1234!@#")),
    use_ssl=True,
    verify_certs=False,
)

def upsert_channel(cur, channel_id, title):
    cur.execute("""
      INSERT INTO yt.channels (platform, channel_yid, title)
      VALUES ('youtube', %s, %s)
      ON CONFLICT (platform, channel_yid)
      DO UPDATE SET title = EXCLUDED.title, updated_at = now()
      RETURNING id
    """, (channel_id, title))
    return cur.fetchone()[0]

def upsert_video(cur, video_id, channel_db_id, title, published_at):
    cur.execute("""
      INSERT INTO yt.videos (platform, video_yid, channel_id, title, published_at)
      VALUES ('youtube', %s, %s, %s, %s)
      ON CONFLICT (platform, video_yid)
      DO UPDATE SET title = EXCLUDED.title, channel_id = EXCLUDED.channel_id, published_at = EXCLUDED.published_at, updated_at = now()
      RETURNING id
    """, (video_id, channel_db_id, title, published_at))
    return cur.fetchone()[0]

def index_video_os(video_id, title, channel_id, published_at_iso):
    doc = {
        "video_id": video_id,
        "title": title,
        "description": None,
        "published_at": published_at_iso,
        "channel_id": channel_id,
        "tags": [],
        "places": [],
        "place_names": None,
        "sentiment_score": 0.0,
        "views": 0,
        "likes": 0
    }
    OS.index(index="videos", id=video_id, body=doc, refresh=True)

def search_and_ingest(query="행궁", days=30, max_results=50):
    # 행궁 관련 다중 키워드 검색
    palace_keywords = [
        "행궁", "궁궐", "고궁", "경복궁", "창덕궁", "덕수궁", 
        "창경궁", "경희궁", "궁궐 관광", "고궁 투어",
        "궁궐 데이트", "궁궐 카페", "궁궐 맛집", "궁궐 식당",
        "경복궁 데이트", "창덕궁 카페", "덕수궁 맛집",
        "궁궐 주변 카페", "궁궐 주변 맛집", "궁궐 주변 식당",
        "궁궐 데이트코스", "궁궐 커플여행", "궁궐 연인여행"
    ]
    
    all_videos = []
    
    for keyword in palace_keywords:
        print(f"검색 키워드: {keyword}")
        since = (datetime.utcnow() - timedelta(days=days)).isoformat("T") + "Z"
        resp = YT.search().list(
            part="snippet",
            q=keyword,
            type="video",
            publishedAfter=since,
            maxResults=max_results
        ).execute()
        
        all_videos.extend(resp.get("items", []))
        print(f"키워드 '{keyword}'에서 {len(resp.get('items', []))}개 비디오 발견")
    
    # 중복 제거 (videoId 기준)
    unique_videos = {}
    for item in all_videos:
        video_id = item["id"]["videoId"]
        if video_id not in unique_videos:
            unique_videos[video_id] = item
    
    print(f"총 {len(unique_videos)}개의 고유 비디오 발견")
    
    # 중복 제거된 비디오들을 처리
    class MockResponse:
        def get(self, key, default=None):
            if key == "items":
                return list(unique_videos.values())
            return default
    
    resp = MockResponse()
    print("Connecting to database with:", DB)
    if psycopg3 is not None:
        with psycopg3.connect(**DB) as conn:
            with conn.cursor() as cur:
                try:
                    conn.execute("SET client_encoding TO 'UTF8'")
                except Exception:
                    pass
                for item in resp.get("items", []):
                    vid = item["id"]["videoId"]
                    snip = item["snippet"]
                    ch_id = snip["channelId"]
                    ch_title = snip.get("channelTitle","")
                    v_title = snip.get("title","")
                    pub = snip.get("publishedAt")  # ISO8601

                    # 1) 채널 upsert → 내부 UUID
                    channel_db_id = upsert_channel(cur, ch_id, ch_title)
                    # 2) 비디오 upsert
                    upsert_video(cur, vid, channel_db_id, v_title, pub)
                    # 3) OS 색인 (OpenSearch 연결 문제로 임시 비활성화)
                    # index_video_os(vid, v_title, ch_id, pub)

                    print("Ingested & Indexed:", vid, v_title)
    else:
        with psycopg2.connect(**DB) as conn, conn.cursor() as cur:
            try:
                conn.set_client_encoding('UTF8')
            except Exception:
                pass
            for item in resp.get("items", []):
                vid = item["id"]["videoId"]
                snip = item["snippet"]
                ch_id = snip["channelId"]
                ch_title = snip.get("channelTitle","")
                v_title = snip.get("title","")
                pub = snip.get("publishedAt")  # ISO8601

                # 1) 채널 upsert → 내부 UUID
                channel_db_id = upsert_channel(cur, ch_id, ch_title)
                # 2) 비디오 upsert
                upsert_video(cur, vid, channel_db_id, v_title, pub)
                # 3) OS 색인 (OpenSearch 연결 문제로 임시 비활성화)
                # index_video_os(vid, v_title, ch_id, pub)

                print("Ingested & Indexed:", vid, v_title)

if __name__ == "__main__":
    search_and_ingest()
