import sqlite3
from pathlib import Path
from datetime import datetime, timedelta


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "paper_assistant.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def get_columns(cur, table_name):
    cur.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cur.fetchall()}


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

        topic TEXT DEFAULT NULL,
        paper_type TEXT DEFAULT NULL,
        priority TEXT DEFAULT NULL,

        business_score REAL DEFAULT NULL,
        research_score REAL DEFAULT NULL,
        trend_score REAL DEFAULT NULL,
        innovation_score REAL DEFAULT NULL,
        engineering_score REAL DEFAULT NULL,
        overall_score REAL DEFAULT NULL,

        reason TEXT DEFAULT NULL,
        relation TEXT DEFAULT NULL,

        favorite INTEGER DEFAULT 0,
        downloaded INTEGER DEFAULT 0,
        obsidian INTEGER DEFAULT 0,
        read_status TEXT DEFAULT 'unread'
    )
    """)

    existing_columns = get_columns(cur, "papers")

    migrations = {
        "paper_type": "ALTER TABLE papers ADD COLUMN paper_type TEXT DEFAULT NULL",
        "business_score": "ALTER TABLE papers ADD COLUMN business_score REAL DEFAULT NULL",
        "research_score": "ALTER TABLE papers ADD COLUMN research_score REAL DEFAULT NULL",
        "trend_score": "ALTER TABLE papers ADD COLUMN trend_score REAL DEFAULT NULL",
        "innovation_score": "ALTER TABLE papers ADD COLUMN innovation_score REAL DEFAULT NULL",
        "engineering_score": "ALTER TABLE papers ADD COLUMN engineering_score REAL DEFAULT NULL",
        "overall_score": "ALTER TABLE papers ADD COLUMN overall_score REAL DEFAULT NULL",
        "reason": "ALTER TABLE papers ADD COLUMN reason TEXT DEFAULT NULL",
        "relation": "ALTER TABLE papers ADD COLUMN relation TEXT DEFAULT NULL",
        "favorite": "ALTER TABLE papers ADD COLUMN favorite INTEGER DEFAULT 0",
        "downloaded": "ALTER TABLE papers ADD COLUMN downloaded INTEGER DEFAULT 0",
        "obsidian": "ALTER TABLE papers ADD COLUMN obsidian INTEGER DEFAULT 0",
        "read_status": "ALTER TABLE papers ADD COLUMN read_status TEXT DEFAULT 'unread'",
    }

    for column, sql in migrations.items():
        if column not in existing_columns:
            cur.execute(sql)

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


def update_scores(scored_papers):
    conn = get_conn()
    cur = conn.cursor()

    for paper in scored_papers:
        cur.execute("""
        UPDATE papers
        SET
            topic = ?,
            paper_type = ?,
            priority = ?,
            business_score = ?,
            research_score = ?,
            trend_score = ?,
            innovation_score = ?,
            engineering_score = ?,
            overall_score = ?,
            reason = ?,
            relation = ?
        WHERE link = ?
        """, (
            paper.get("topic"),
            paper.get("paper_type"),
            paper.get("priority"),
            paper.get("business_score"),
            paper.get("research_score"),
            paper.get("trend_score"),
            paper.get("innovation_score"),
            paper.get("engineering_score"),
            paper.get("overall_score"),
            paper.get("reason"),
            paper.get("relation"),
            paper.get("link"),
        ))

    conn.commit()
    conn.close()


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


def get_recent_topic_stats(limit=10):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT topic, COUNT(*)
    FROM papers
    WHERE topic IS NOT NULL
    GROUP BY topic
    ORDER BY COUNT(*) DESC
    LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_topic_trends(limit=10):
    """
    Trend Engine v1:
    统计最近 7 天和 30 天 topic 频次，并计算增长率。
    """
    conn = get_conn()
    cur = conn.cursor()

    now = datetime.now()
    date_7d = (now - timedelta(days=7)).isoformat(timespec="seconds")
    date_30d = (now - timedelta(days=30)).isoformat(timespec="seconds")

    cur.execute("""
    SELECT topic, COUNT(*)
    FROM papers
    WHERE topic IS NOT NULL
      AND last_seen >= ?
    GROUP BY topic
    """, (date_7d,))
    rows_7d = dict(cur.fetchall())

    cur.execute("""
    SELECT topic, COUNT(*)
    FROM papers
    WHERE topic IS NOT NULL
      AND last_seen >= ?
    GROUP BY topic
    """, (date_30d,))
    rows_30d = dict(cur.fetchall())

    conn.close()

    topics = set(rows_7d.keys()) | set(rows_30d.keys())
    trends = []

    for topic in topics:
        count_7d = rows_7d.get(topic, 0)
        count_30d = rows_30d.get(topic, 0)

        expected_7d = max(count_30d / 4.0, 1)
        growth_rate = round(count_7d / expected_7d, 2)

        if count_7d >= 5 and growth_rate >= 1.8:
            status = "快速上升"
        elif count_7d >= 5 and growth_rate >= 1.0:
            status = "持续高热"
        elif count_7d >= 2:
            status = "有一定活跃"
        else:
            status = "低频观察"

        trends.append({
            "topic": topic,
            "count_7d": count_7d,
            "count_30d": count_30d,
            "growth_rate": growth_rate,
            "status": status,
        })

    trends.sort(
        key=lambda x: (x["count_7d"], x["growth_rate"]),
        reverse=True,
    )

    return trends[:limit]