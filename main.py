from utils.config import load_interest, load_profile
from utils.arxiv import fetch_arxiv, rough_filter
from utils.llm import generate_daily_report

# 正常逻辑：之后会恢复 LLM 辅助打分
# from utils.llm import score_papers, generate_daily_report

# 临时测试逻辑：先测试规则评分引擎
from ranking.rule_ranker import rule_score_papers

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
        push_feishu("论文推送\n\n今日没有新的 arXiv 论文。")
        return

    selected_papers = rough_filter(
        papers=new_papers,
        positive_keywords=positive_keywords,
        negative_keywords=negative_keywords,
        limit=80,
    )

    # ============================================================
    # 临时测试逻辑：只用 Python 规则评分，不让 LLM 直接打分
    # 目的：
    # 1. 测试 business_score / research_score / trend_score 是否稳定
    # 2. 测试排序是否更偏向内容安全、推荐、Agent、多模态
    # 3. 降低 LLM 随机打分的影响
    # ============================================================
    scored_papers = rule_score_papers(selected_papers)

    # ============================================================
    # 正常逻辑：后续版本会改成：
    # 1. rule_score_papers() 先给 business/research/trend/topic
    # 2. LLM 只补充 innovation_score / engineering_score / reason / relation
    # 3. Python 重新计算 overall_score
    #
    # 暂时不要用下面这段：
    #
    # scored_papers = score_papers(
    #     papers=selected_papers,
    #     profile=profile,
    # )
    # ============================================================

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
