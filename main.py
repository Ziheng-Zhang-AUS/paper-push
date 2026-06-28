from utils.config import load_interest, load_profile
from utils.arxiv import fetch_arxiv, rough_filter
from utils.llm import enrich_with_llm_scores, generate_daily_report
from ranking.rule_ranker import rule_score_papers, finalize_scores
from ranking.diversity_ranker import diversify_papers
from utils.feishu import push_feishu
from storage.db import (
    init_db,
    upsert_papers,
    update_scores,
    mark_pushed,
    get_recent_topic_stats,
)


TEST_MODE_REPROCESS_EXISTING = True
# True：测试模式。即使没有新论文，也重新处理当前抓到的 papers。
# False：正式模式。没有新论文时直接退出，避免重复推送。


def main():
    init_db()

    interest = load_interest()
    profile = load_profile()

    top_k = interest.get("top_k", 20)
    fetch_max_results = interest.get("fetch_max_results", 250)
    categories = interest.get(
        "categories",
        ["cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.IR"],
    )
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
        if TEST_MODE_REPROCESS_EXISTING:
            selected_source = papers
        else:
            push_feishu("论文推送\n\n今日没有新的 arXiv 论文。")
            return
    else:
        selected_source = new_papers

    selected_papers = rough_filter(
        papers=selected_source,
        positive_keywords=positive_keywords,
        negative_keywords=negative_keywords,
        limit=80,
    )

    # Step 1: 规则评分
    rule_scored_papers = rule_score_papers(selected_papers)

    # Step 2: LLM 补充 innovation / engineering / reason / relation
    llm_enriched_papers = enrich_with_llm_scores(
        papers=rule_scored_papers,
        profile=profile,
        limit=40,
    )

    # Step 3: Python 重新计算综合分
    final_scored_papers = finalize_scores(llm_enriched_papers)

    update_scores(final_scored_papers)

    # Step 4: 多样性重排，避免纯 Top20 信息茧房
    diversified_papers = diversify_papers(
        scored_papers=final_scored_papers,
        top_k=top_k,
    )

    topic_stats = get_recent_topic_stats(limit=10)

    report = generate_daily_report(
        scored_papers=diversified_papers,
        topic_stats=topic_stats,
        top_k=top_k,
    )

    push_feishu(report)

    mark_pushed(diversified_papers)


if __name__ == "__main__":
    main()