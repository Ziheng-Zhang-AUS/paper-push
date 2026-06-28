def keyword_hit_score(text, keywords, max_score=10):
    text = text.lower()
    hits = []

    for keyword in keywords:
        if keyword.lower() in text:
            hits.append(keyword)

    score = min(max_score, len(hits) * 2)
    return score, hits


BUSINESS_KEYWORDS = [
    "content safety",
    "ai safety",
    "safety classification",
    "safety classifier",
    "moderation",
    "trust and safety",
    "risk control",
    "toxicity",
    "hate speech",
    "misinformation",
    "harmful content",
    "harmful video",
    "unsafe content",
    "policy violation",
    "jailbreak",
    "prompt injection",
    "guardrail",
    "red teaming",
    "coded language",
    "indirect linguistic encoding",
    "intent-aware",
    "adversarial text",
    "evasion",
    "video understanding",
    "short video",
    "recommendation",
    "recommender",
    "recommendation safety",
    "tiktok",
    "social media",
    "user generated content",
    "ugc",
]

RESEARCH_KEYWORDS = [
    "large language model",
    "llm",
    "foundation model",
    "multimodal",
    "vision-language",
    "vlm",
    "agent",
    "reasoning",
    "alignment",
    "long context",
    "evaluation",
    "benchmark",
    "recommendation",
    "recommender",
    "content safety",
    "ai safety",
]

TREND_KEYWORDS = [
    "mcp",
    "model context protocol",
    "agentic rag",
    "rag",
    "agent",
    "multi-agent",
    "tool use",
    "function calling",
    "skill",
    "skill learning",
    "loop",
    "vla",
    "vision-language-action",
    "world model",
    "reasoning model",
    "test-time scaling",
    "rlvr",
    "rlhf",
    "rlaif",
    "synthetic data",
    "long context",
    "moe",
]

LOW_PRIORITY_KEYWORDS = [
    "medical",
    "clinical",
    "nuclear",
    "robotic manipulation",
    "traffic scenario",
    "autonomous driving",
    "protein",
    "molecule",
    "drug",
    "diffusion image generation",
    "text-to-image",
]


def infer_topic(text):
    text = text.lower()

    if any(k in text for k in [
        "content safety", "harmful", "toxicity", "hate speech",
        "misinformation", "moderation", "jailbreak", "prompt injection",
        "guardrail", "coded language", "indirect linguistic encoding",
        "safety classification", "adversarial text", "evasion"
    ]):
        return "Content Safety"

    if any(k in text for k in [
        "recommendation", "recommender", "personalization",
        "session-based recommendation", "industrial recommendation"
    ]):
        return "Recommendation"

    if any(k in text for k in [
        "agent", "tool use", "multi-agent", "mcp",
        "model context protocol", "gui agent"
    ]):
        return "LLM Agent"

    if any(k in text for k in [
        "multimodal", "vision-language", "vlm",
        "video understanding", "long video", "visual token", "mllm"
    ]):
        return "Multimodal"

    if any(k in text for k in [
        "reasoning", "rlvr", "rlhf", "rlaif",
        "test-time scaling", "reward"
    ]):
        return "LLM Training / Reasoning"

    return "Other"


def infer_paper_type(business_score, research_score, trend_score):
    if business_score >= 4:
        return "工作业务相关"
    if trend_score >= 6:
        return "短期热点"
    if research_score >= 7:
        return "长期主线"
    return "新技术观察"


def infer_priority(overall_score, business_score=0):
    if business_score >= 6 or overall_score >= 8.0:
        return "高"
    if business_score >= 4 or overall_score >= 6.5:
        return "中"
    if overall_score >= 5.0:
        return "低"
    return "跟踪即可"


def compute_overall_score(paper):
    business = float(paper.get("business_score", 0) or 0)
    research = float(paper.get("research_score", 0) or 0)
    trend = float(paper.get("trend_score", 0) or 0)
    innovation = float(paper.get("innovation_score", 0) or 0)
    engineering = float(paper.get("engineering_score", 0) or 0)

    return round(
        0.40 * business
        + 0.25 * research
        + 0.15 * trend
        + 0.15 * innovation
        + 0.05 * engineering,
        2,
    )


def rule_score_papers(papers):
    scored = []

    for paper in papers:
        text = f"{paper.get('title', '')} {paper.get('summary', '')}"
        lower_text = text.lower()

        business_score, business_hits = keyword_hit_score(lower_text, BUSINESS_KEYWORDS)
        research_score, research_hits = keyword_hit_score(lower_text, RESEARCH_KEYWORDS)
        trend_score, trend_hits = keyword_hit_score(lower_text, TREND_KEYWORDS)

        topic = infer_topic(lower_text)

        enriched = paper.copy()
        enriched.update({
            "topic": topic,
            "paper_type": infer_paper_type(business_score, research_score, trend_score),
            "business_score": business_score,
            "research_score": research_score,
            "trend_score": trend_score,
            "innovation_score": 0,
            "engineering_score": 0,
            "business_hits": business_hits,
            "research_hits": research_hits,
            "trend_hits": trend_hits,
            "low_priority_hit": any(keyword in lower_text for keyword in LOW_PRIORITY_KEYWORDS),
        })

        overall_score = compute_overall_score(enriched)

        if enriched["low_priority_hit"]:
            overall_score = round(overall_score * 0.5, 2)

        enriched["overall_score"] = overall_score
        enriched["priority"] = infer_priority(overall_score, business_score)

        scored.append(enriched)

    scored.sort(key=lambda x: x["overall_score"], reverse=True)
    return scored


def finalize_scores(papers):
    finalized = []

    for paper in papers:
        overall_score = compute_overall_score(paper)

        if paper.get("low_priority_hit"):
            overall_score = round(overall_score * 0.5, 2)

        paper["overall_score"] = overall_score
        paper["priority"] = infer_priority(overall_score, paper.get("business_score", 0))
        paper["paper_type"] = infer_paper_type(
            paper.get("business_score", 0),
            paper.get("research_score", 0),
            paper.get("trend_score", 0),
        )

        finalized.append(paper)

    finalized.sort(key=lambda x: x["overall_score"], reverse=True)
    return finalized