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
    "safety classifiers",
    "moderation",
    "trust and safety",
    "risk control",
    "toxicity",
    "hate speech",
    "misinformation",
    "harmful content",
    "harmful video",
    "harmful video understanding",
    "unsafe content",
    "unsafe prompt",
    "policy violation",
    "policy",
    "jailbreak",
    "prompt injection",
    "guardrail",
    "guardrails",
    "red teaming",
    "coded language",
    "coded language detection",
    "indirect linguistic encoding",
    "implicit hate",
    "intent-aware",
    "intent aware",
    "adversarial text",
    "evasion",
    "evasion vulnerability",
    "video understanding",
    "short video",
    "recommendation",
    "recommender",
    "recommendation safety",
    "tiktok",
    "social media",
    "user generated content",
    "ugc",
    "abuse detection",
    "trustworthy",
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
        "content safety",
        "harmful",
        "toxicity",
        "hate speech",
        "misinformation",
        "moderation",
        "jailbreak",
        "prompt injection",
        "guardrail",
        "coded language",
        "indirect linguistic encoding",
        "safety classification",
        "safety classifier",
        "adversarial text",
        "evasion",
    ]):
        return "Content Safety"

    if any(k in text for k in [
        "recommendation",
        "recommender",
        "personalization",
        "session-based recommendation",
        "industrial recommendation",
    ]):
        return "Recommendation"

    if any(k in text for k in [
        "agent",
        "tool use",
        "multi-agent",
        "mcp",
        "model context protocol",
        "gui agent",
    ]):
        return "LLM Agent"

    if any(k in text for k in [
        "multimodal",
        "vision-language",
        "vlm",
        "video understanding",
        "long video",
        "visual token",
        "mllm",
    ]):
        return "Multimodal"

    if any(k in text for k in [
        "reasoning",
        "rlvr",
        "rlhf",
        "rlaif",
        "test-time scaling",
        "reward",
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
    if business_score >= 6 or overall_score >= 5.0:
        return "高"
    if business_score >= 4 or overall_score >= 3.0:
        return "中"
    if overall_score >= 2.0:
        return "低"
    return "跟踪即可"


def rule_score_papers(papers):
    scored = []

    for paper in papers:
        text = f"{paper.get('title', '')} {paper.get('summary', '')}"
        lower_text = text.lower()

        business_score, business_hits = keyword_hit_score(lower_text, BUSINESS_KEYWORDS)
        research_score, research_hits = keyword_hit_score(lower_text, RESEARCH_KEYWORDS)
        trend_score, trend_hits = keyword_hit_score(lower_text, TREND_KEYWORDS)

        topic = infer_topic(lower_text)

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

        low_priority_hit = any(keyword in lower_text for keyword in LOW_PRIORITY_KEYWORDS)

        if low_priority_hit:
            overall_score = round(overall_score * 0.5, 2)

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
            "priority": infer_priority(overall_score, business_score),
            "business_hits": business_hits,
            "research_hits": research_hits,
            "trend_hits": trend_hits,
            "low_priority_hit": low_priority_hit,
            "reason": build_rule_reason(business_hits, research_hits, trend_hits, low_priority_hit),
            "relation": build_rule_relation(topic, business_score, research_score, trend_score),
        })

        scored.append(enriched)

    scored.sort(key=lambda x: x["overall_score"], reverse=True)
    return scored


def build_rule_reason(business_hits, research_hits, trend_hits, low_priority_hit):
    parts = []

    if business_hits:
        parts.append("命中业务关键词：" + ", ".join(business_hits[:5]))

    if research_hits:
        parts.append("命中长期研究关键词：" + ", ".join(research_hits[:5]))

    if trend_hits:
        parts.append("命中热点关键词：" + ", ".join(trend_hits[:5]))

    if low_priority_hit:
        parts.append("命中低优先级领域关键词，综合分已降权")

    if not parts:
        return "未命中明显高优先级关键词，暂作为低优先级观察。"

    return "；".join(parts)


def build_rule_relation(topic, business_score, research_score, trend_score):
    if business_score >= 4:
        return f"与当前 TikTok 内容安全、风控、推荐或多模态内容理解方向相关；主题为 {topic}。"

    if research_score >= 7:
        return f"与长期 AI 技术积累相关；主题为 {topic}。"

    if trend_score >= 6:
        return f"属于近期 AI 热点跟踪方向；主题为 {topic}。"

    return f"相关性一般，主题为 {topic}，可低频跟踪。"
