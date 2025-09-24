import os
from typing import Iterable

from dotenv import load_dotenv
import psycopg2

from sentiment_infer import SentimentService
from text_utils import clean_text


load_dotenv()

DB = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "yt"),
    user=os.getenv("DB_USER", "app"),
    password=os.getenv("DB_PASSWORD", "app1234"),
)


def iter_unprocessed_comments(cur, batch_size: int = 200) -> Iterable[tuple]:
    cur.execute(
        """
        SELECT id, text_raw
        FROM yt.comments
        WHERE sentiment IS NULL
        LIMIT %s
        """,
        (batch_size,),
    )
    return cur.fetchall()


def process_sentiment(batch_size: int = 200):
    svc = SentimentService()
    with psycopg2.connect(**DB) as conn, conn.cursor() as cur:
        while True:
            rows = iter_unprocessed_comments(cur, batch_size=batch_size)
            if not rows:
                print("No more comments to process.")
                break
            for cid, text_raw in rows:
                label, score = svc.infer(text_raw or "")
                cur.execute(
                    "UPDATE yt.comments SET sentiment=%s, sentiment_score=%s WHERE id=%s",
                    (label, score, cid),
                )
            conn.commit()
            print("Processed", len(rows), "comments")


if __name__ == "__main__":
    process_sentiment()


