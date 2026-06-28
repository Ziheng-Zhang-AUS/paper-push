def diversify_papers(scored_papers, top_k=20):
    """
    TopK = business + research + trend + exploration

    目标：
    - 保证工作业务相关论文占主导
    - 保留长期技术主线
    - 保留短期热点
    - 留少量探索位，避免信息茧房
    """

    business_quota = int(top_k * 0.60)
    research_quota = int(top_k * 0.20)
    trend_quota = int(top_k * 0.10)
    exploration_quota = top_k - business_quota - research_quota - trend_quota

    selected = []
    selected_links = set()

    def add_from_bucket(bucket, quota):
        added = 0
        for paper in bucket:
            if added >= quota:
                break

            link = paper.get("link")
            if link in selected_links:
                continue

            selected.append(paper)
            selected_links.add(link)
            added += 1

    business_bucket = [
        p for p in scored_papers
        if p.get("paper_type") == "工作业务相关"
    ]

    research_bucket = [
        p for p in scored_papers
        if p.get("paper_type") == "长期主线"
    ]

    trend_bucket = [
        p for p in scored_papers
        if p.get("paper_type") == "短期热点"
    ]

    exploration_bucket = [
        p for p in scored_papers
        if p.get("paper_type") in ["新技术观察", "低优先级"]
    ]

    business_bucket.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    research_bucket.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    trend_bucket.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    exploration_bucket.sort(key=lambda x: x.get("overall_score", 0), reverse=True)

    add_from_bucket(business_bucket, business_quota)
    add_from_bucket(research_bucket, research_quota)
    add_from_bucket(trend_bucket, trend_quota)
    add_from_bucket(exploration_bucket, exploration_quota)

    # 如果某些 bucket 不足，用剩余高分论文补满
    if len(selected) < top_k:
        fallback = sorted(
            scored_papers,
            key=lambda x: x.get("overall_score", 0),
            reverse=True,
        )

        add_from_bucket(fallback, top_k - len(selected))

    # 最后仍按 overall_score 排序，避免日报看起来混乱
    selected.sort(key=lambda x: x.get("overall_score", 0), reverse=True)

    return selected[:top_k]