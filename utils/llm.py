import os
import json
from datetime import datetime
from openai import OpenAI


client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url="https://api.deepinfra.com/v1/openai",
)

MODEL = "deepseek-ai/DeepSeek-V4-Flash"


def enrich_with_llm_scores(papers, profile, limit=40):
    candidates = papers[:limit]

    paper_text = "\n\n".join([
        f"[{idx + 1}]\n"
        f"Title: {paper['title']}\n"
        f"Authors: {paper.get('authors', '')}\n"
        f"Published: {paper.get('published', '')}\n"
        f"Abstract: {paper.get('summary', '')}\n"
        f"Link: {paper['link']}\n"
        f"Rule Topic: {paper.get('topic')}\n"
        f"Rule Business Score: {paper.get('business_score')}\n"
        f"Rule Research Score: {paper.get('research_score')}\n"
        f"Rule Trend Score: {paper.get('trend_score')}\n"
        f"Rule Keyword Hits: business={paper.get('business_hits', [])}, "
        f"research={paper.get('research_hits', [])}, trend={paper.get('trend_hits', [])}"
        for idx, paper in enumerate(candidates)
    ])

    prompt = f"""
你是我的 AI Research Scout。

你的任务不是重新决定 business_score、research_score、trend_score。
这些分数已经由规则引擎根据关键词和我的兴趣画像初步计算。

你只需要补充两个更主观、需要理解摘要的分数：

1. innovation_score
2. engineering_score

并补充：
- reason
- relation

我的研究画像如下：

{profile}

候选论文如下：

{paper_text}

innovation_score：方法创新程度，0-10 分
- 0-2：几乎没有方法创新，只是应用已有方法、普通 benchmark、普通实验对比。
- 3-4：有小幅改进，但主要是组合已有模块，技术新意有限。
- 5-6：有清晰方法设计，解决了一个具体问题，但不是明显新范式。
- 7-8：方法设计有较强新意，有可能被同方向后续工作复用。
- 9-10：提出明显新范式、新训练框架、新评估体系或新系统架构，可能影响一个方向。

engineering_score：工程落地潜力，0-10 分
- 0-2：主要是理论、概念、数据分析，短期难落地。
- 3-4：有一定工程参考价值，但缺乏系统验证或部署可行性。
- 5-6：方法可复现，可能在实验系统或内部工具中尝试。
- 7-8：工程可用性较强，有清晰系统设计、评测结果或可迁移模块。
- 9-10：高度工程化，有真实线上实验、工业系统验证、开源实现，或可直接启发业务系统。

注意：
- 只根据标题和摘要判断，不要编造摘要中没有的信息。
- 如果摘要没有说明线上实验、开源代码、真实系统部署，不要给 engineering_score 9-10。
- 如果只是把已有方法套到新场景，不要给 innovation_score 8 以上。
- 输出必须是合法 JSON 数组。
- 不要输出 markdown。
- 不要输出额外解释。

每个元素格式：

{{
  "index": 1,
  "innovation_score": 0,
  "engineering_score": 0,
  "reason": "为什么推荐或为什么只需跟踪",
  "relation": "它和我的工作业务、长期研究兴趣或短期热点跟踪的关系"
}}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你只输出合法 JSON 数组，不输出 markdown，不输出额外解释。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )

    raw = response.choices[0].message.content
    additions = parse_json_array(raw)

    enriched = []
    for idx, paper in enumerate(candidates):
        item = additions.get(idx + 1, {})

        updated = paper.copy()
        updated["innovation_score"] = clamp_score(item.get("innovation_score", 0))
        updated["engineering_score"] = clamp_score(item.get("engineering_score", 0))
        updated["reason"] = item.get("reason", "")
        updated["relation"] = item.get("relation", "")

        enriched.append(updated)

    return enriched


def parse_json_array(raw):
    raw = raw.strip()

    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    data = json.loads(raw)

    result = {}
    for item in data:
        try:
            idx = int(item.get("index"))
            result[idx] = item
        except Exception:
            continue

    return result


def clamp_score(value):
    try:
        value = float(value)
    except Exception:
        return 0

    if value < 0:
        return 0
    if value > 10:
        return 10

    return value


def format_trends(topic_trends):
    if not topic_trends:
        return "暂无足够历史数据。"

    lines = []
    for trend in topic_trends:
        lines.append(
            f"- {trend['topic']}：{trend['status']}，"
            f"7天 {trend['count_7d']} 篇，"
            f"30天 {trend['count_30d']} 篇，"
            f"增长率 {trend['growth_rate']}"
        )

    return "\n".join(lines)


def generate_daily_report(scored_papers, topic_stats=None, topic_trends=None, top_k=20):
    today = datetime.now().strftime("%Y-%m-%d")
    top_papers = scored_papers[:top_k]

    topic_text = ""
    if topic_stats:
        topic_text = "\n".join([f"- {topic}: {count}" for topic, count in topic_stats])

    trend_text = format_trends(topic_trends)

    paper_text = "\n\n".join([
        f"{idx + 1}. {paper['title']}\n"
        f"Link: {paper['link']}\n"
        f"Overall Score: {paper.get('overall_score')}\n"
        f"Business: {paper.get('business_score')} | Research: {paper.get('research_score')} | "
        f"Trend: {paper.get('trend_score')} | Innovation: {paper.get('innovation_score')} | "
        f"Engineering: {paper.get('engineering_score')}\n"
        f"Topic: {paper.get('topic')}\n"
        f"Type: {paper.get('paper_type')}\n"
        f"Priority: {paper.get('priority')}\n"
        f"Reason: {paper.get('reason')}\n"
        f"Relation: {paper.get('relation')}\n"
        f"Abstract: {paper.get('summary')}"
        for idx, paper in enumerate(top_papers)
    ])

    prompt = f"""
请根据下面已经打分和排序好的论文，生成中文飞书日报。

要求：
- 标题：论文推送｜{today}
- 先给出今日概览
- 加入“趋势观察”
- 再给出 Top {top_k}
- 每篇保持简洁
- 不要重新打分
- 不要改变排序
- 不要编造论文没有的信息
- 重点强调：工作业务相关、内容安全、推荐系统、AI热点
- 注意避免信息茧房：探索类论文可以标注为“探索观察”，不要强行说和业务直接相关

历史主题统计：
{topic_text}

趋势统计：
{trend_text}

论文列表：
{paper_text}

输出格式：

论文推送｜{today}

今日概览：
- 候选论文数：
- 推荐论文数：
- 今日最值得关注方向：

趋势观察：
...

近期主题统计：
...

Top论文：
1. 标题：
链接：
综合评分：
分项评分：
方向：
类型：
一句话总结：
推荐理由：
与你的关系：
精读优先级：
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你是严谨的 AI 科研日报写作助手。不要改变给定排序和分数。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content