import os
import json
from datetime import datetime
from openai import OpenAI


client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url="https://api.deepinfra.com/v1/openai",
)

MODEL = "deepseek-ai/DeepSeek-V4-Flash"


def score_papers(papers, profile):
    paper_text = "\n\n".join([
        f"[{idx + 1}]\n"
        f"Title: {paper['title']}\n"
        f"Authors: {paper['authors']}\n"
        f"Published: {paper['published']}\n"
        f"Abstract: {paper['summary']}\n"
        f"Link: {paper['link']}"
        for idx, paper in enumerate(papers)
    ])

    prompt = f"""
你是我的 AI Research Scout。你不是论文审稿人，而是根据我的职业方向、长期技术兴趣、短期热点跟踪需求，筛选每日论文。

我的研究画像：

{profile}

候选论文：

{paper_text}

请为每篇论文打分。必须只根据标题和摘要判断，不要编造摘要中没有的信息。

评分字段：
- business_score：0-10，和 TikTok 业务算法 / 风控算法 / 大模型内容安全 / 多模态内容理解 / 推荐安全的相关性
- research_score：0-10，和长期技术积累的相关性
- trend_score：0-10，是否属于当前 AI 热点，例如 Agent、MCP、RAG、VLA、Skill、Loop、RLVR、Reasoning 等
- innovation_score：0-10，方法创新程度
- engineering_score：0-10，工程落地潜力

overall_score 计算原则：
0.40 * business_score
+ 0.25 * research_score
+ 0.15 * trend_score
+ 0.15 * innovation_score
+ 0.05 * engineering_score

请输出 JSON 数组，不要输出 markdown，不要输出解释性文字。

每个元素格式如下：

{{
  "index": 1,
  "title": "...",
  "link": "...",
  "topic": "Content Safety / Recommendation / LLM Agent / Multimodal / AI Safety / Other",
  "paper_type": "工作业务相关 / 长期主线 / 短期热点 / 新技术观察 / 低优先级",
  "priority": "高 / 中 / 低 / 跟踪即可",
  "business_score": 0,
  "research_score": 0,
  "trend_score": 0,
  "innovation_score": 0,
  "engineering_score": 0,
  "overall_score": 0,
  "reason": "推荐或不推荐的核心原因",
  "relation": "这篇论文和我的关系"
}}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你只输出合法 JSON。不要输出 markdown。不要输出额外解释。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )

    raw = response.choices[0].message.content
    return parse_json_array(raw, papers)


def parse_json_array(raw, original_papers):
    raw = raw.strip()

    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    data = json.loads(raw)

    results = []
    for item in data:
        idx = int(item.get("index", 0)) - 1
        if idx < 0 or idx >= len(original_papers):
            continue

        base = original_papers[idx].copy()
        base.update(item)

        # Python 重新计算一次 overall_score，避免模型乱算
        business = float(base.get("business_score", 0) or 0)
        research = float(base.get("research_score", 0) or 0)
        trend = float(base.get("trend_score", 0) or 0)
        innovation = float(base.get("innovation_score", 0) or 0)
        engineering = float(base.get("engineering_score", 0) or 0)

        base["overall_score"] = round(
            0.40 * business
            + 0.25 * research
            + 0.15 * trend
            + 0.15 * innovation
            + 0.05 * engineering,
            2,
        )

        results.append(base)

    results.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    return results


def generate_daily_report(scored_papers, topic_stats=None, top_k=20):
    today = datetime.now().strftime("%Y-%m-%d")
    top_papers = scored_papers[:top_k]

    topic_text = ""
    if topic_stats:
        topic_text = "\n".join([f"- {topic}: {count}" for topic, count in topic_stats])

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
- 再给出 Top {top_k}
- 每篇保持简洁
- 重点强调：工作业务相关、内容安全、推荐系统、AI热点
- 不要编造论文没有的信息

历史主题统计：
{topic_text}

论文列表：
{paper_text}

输出格式：

论文推送｜{today}

今日概览：
- 候选论文数：
- 推荐论文数：
- 今日最值得关注方向：

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
            {"role": "system", "content": "你是严谨的 AI 科研日报写作助手。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content
