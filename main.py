from utils.config import load_interest, load_profile
from utils.arxiv import fetch_arxiv, rough_filter
from utils.llm import score_papers, generate_daily_report
from utils.feishu import push_feishu
from storage.db import (
    init_db,
    upsert_papers,
    update_scores,
    mark_pushed,
    get_recent_topic_stats,
)


def main():
    init_db()

    interest = load_interest()
    profile = load_profile()

    top_k = interest.get("top_k", 20)
    fetch_max_results = interest.get("fetch_max_results", 250)
    categories = interest.get("categories", ["cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.IR"])
    positive_keywords = interest.get("positive_keywords", [])
    negative_keywords = interest.get("negative_keywords", [])

    papers = fetch_arxiv(
        categories=categories,
        max_results=fetch_max_results,
    )

    if not papers:
        push_feishu("论文推送\n\n今日 arXiv 没有抓取到论文。")
        return

    new_papers = upsert_papers(papers)

    if not new_papers:
        push_feishu("论文推送\n\n今日没有新的 arXiv 论文。")
        return

    selected_papers = rough_filter(
        papers=new_papers,
        positive_keywords=positive_keywords,
        negative_keywords=negative_keywords,
        limit=80,
    )

    scored_papers = score_papers(
        papers=selected_papers,
        profile=profile,
    )

    update_scores(scored_papers)

    topic_stats = get_recent_topic_stats(limit=10)

    report = generate_daily_report(
        scored_papers=scored_papers,
        topic_stats=topic_stats,
        top_k=top_k,
    )

    push_feishu(report)
    mark_pushed(scored_papers[:top_k])


if __name__ == "__main__":
    main()
