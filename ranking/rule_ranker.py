def keyword_hit_score(text, keywords, max_score=10):
    text = text.lower()
    hits = []

    for keyword in keywords:
        if keyword.lower() in text:
            hits.append(keyword)

    if not keywords:
        return 0, hits

    score = min(max_score, len(hits) * 2)
    return score, hits


BUSINESS_KEYWORDS = [
    "content safety",
    "ai safety",
    "safety classification",
    "moderation",
    "trust and safety",
    "risk control",
    "toxicity",
    "hate speech",
    "misinformation",
    "harmful content",
    "policy violation",
    "jailbreak",
    "prompt injection",
    "guardrail",
    "red teaming",
    "video understanding",
    "short video",
    "recommendation",
    "recommender",
    "recommendation safety",
    "tiktok",
    "social media",
    "user generated content",
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


def infer_topic(text):
    text = text.lower()

    if any(k in text for k in ["content safety", "harmful", "toxicity", "hate speech", "misinformation", "moderation", "jailbreak", "prompt injection", "guardrail"]):
        return "Content Safety"

    if any(k in text for k in ["recommendation", "recommender", "personalization"]):
        return "Recommendation"

    if any(k in text for k in ["agent", "tool use", "multi-agent", "mcp", "model context protocol"]):
        return "LLM Agent"

    if any(k in text for k in ["multimodal", "vision-language", "vlm", "video understanding", "long video"]):
        return "Multimodal"

    if any(k in text for k in ["reasoning", "rlvr", "rlhf", "rlaif", "test-time scaling"]):
        return "LLM Training / Reasoning"

    return "Other"


def infer_paper_type(business_score, research_score, trend_score):
    if business_score >= 7:
        return "工作业务相关"
    if research_score >= 7:
        return "长期主线"
    if trend_score >= 7:
        return "短期热点"
    return "新技术观察"


def infer_priority(overall_score):
    if overall_score >= 8.5:
        return "高"
    if overall_score >= 7.0:
        return "中"
    if overall_score >= 5.5:
        return "低"
    return "跟踪即可"


def rule_score_papers(papers):
    scored = []

    for paper in papers:
        text = f"{paper.get('title', '')} {paper.get('summary', '')}"

        business_score, business_hits = keyword_hit_score(text, BUSINESS_KEYWORDS)
        research_score, research_hits = keyword_hit_score(text, RESEARCH_KEYWORDS)
        trend_score, trend_hits = keyword_hit_score(text, TREND_KEYWORDS)

        topic = infer_topic(text)

        # 暂时只用规则分数。innovation / engineering 之后交给 LLM 补。
        innovation_score = 0
        engineering_score = 0

        overall_score = round(
            0.40 * business_score
            + 0.25 * research_score
            + 0.15 * trend_score
            + 0.15 * innovation_score
            + 0.05 * engineering_score,
            2,
        )

        enriched = paper.copy()
        enriched.update({
            "topic": topic,
            "paper_type": infer_paper_type(business_score, research_score, trend_score),
            "business_score": business_score,
            "research_score": research_score,
            "trend_score": trend_score,
            "innovation_score": innovation_score,
            "engineering_score": engineering_score,
            "overall_score": overall_score,
            "priority": infer_priority(overall_score),
            "business_hits": business_hits,
            "research_hits": research_hits,
            "trend_hits": trend_hits,
        })

        scored.append(enriched)

    scored.sort(key=lambda x: x["overall_score"], reverse=True)
    return scored
