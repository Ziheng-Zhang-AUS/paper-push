import sqlite3
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "paper_assistant.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS papers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        link TEXT NOT NULL UNIQUE,
        authors TEXT,
        summary TEXT,
        published TEXT,
        first_seen TEXT,
        last_seen TEXT,
        pushed INTEGER DEFAULT 0,
        score REAL DEFAULT NULL,
        topic TEXT DEFAULT NULL,
        priority TEXT DEFAULT NULL
    )
    """)

    conn.commit()
    conn.close()


def upsert_papers(papers):
    now = datetime.now().isoformat(timespec="seconds")

    conn = get_conn()
    cur = conn.cursor()

    new_papers = []

    for paper in papers:
        cur.execute("SELECT id FROM papers WHERE link = ?", (paper["link"],))
        row = cur.fetchone()

        if row is None:
            cur.execute("""
            INSERT INTO papers (
                title, link, authors, summary, published, first_seen, last_seen, pushed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                paper["title"],
                paper["link"],
                paper.get("authors", ""),
                paper.get("summary", ""),
                paper.get("published", ""),
                now,
                now,
            ))
            new_papers.append(paper)
        else:
            cur.execute("""
            UPDATE papers
            SET last_seen = ?
            WHERE link = ?
            """, (now, paper["link"]))

    conn.commit()
    conn.close()

    return new_papers


def mark_pushed(papers):
    conn = get_conn()
    cur = conn.cursor()

    for paper in papers:
        cur.execute("""
        UPDATE papers
        SET pushed = 1
        WHERE link = ?
        """, (paper["link"],))

    conn.commit()
    conn.close()


def get_recent_topic_stats(days=7):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT topic, COUNT(*)
    FROM papers
    WHERE topic IS NOT NULL
    GROUP BY topic
    ORDER BY COUNT(*) DESC
    LIMIT 10
    """)

    rows = cur.fetchall()
    conn.close()

    return rows
