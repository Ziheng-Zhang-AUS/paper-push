import os
import json
from datetime import datetime
from openai import OpenAI


client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url="https://api.deepinfra.com/v1/openai",
)


def rank_and_summarize(papers, profile, top_k=20):
    paper_text = "\n\n".join([
        f"[{idx + 1}]\n"
        f"Title: {paper['title']}\n"
        f"Authors: {paper['authors']}\n"
        f"Published: {paper['published']}\n"
        f"Abstract: {paper['summary']}\n"
        f"Link: {paper['link']}"
        for idx, paper in enumerate(papers)
    ])

    today = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
你是一位 AI Research Scout，任务是帮我从每日 arXiv 论文中筛选值得关注的论文。

这是我的研究画像：

{profile}

今天候选论文如下：

{paper_text}

请根据我的研究画像，从候选论文中选出 Top {top_k}。

评分标准：
- 0-10 分
- 工作业务相关性：内容安全、风控、多模态内容理解、短视频理解、推荐安全优先
- 长期技术价值：LLM、Agent、多模态、推荐系统、AI Safety 优先
- 短期热点价值：RAG、Agentic RAG、MCP、Skill、Loop、VLA、Reasoning Model 等可加分
- 方法创新、实验质量、工程落地潜力可以加分
- 纯套壳应用、纯 prompt trick、摘要营销化但技术少应降分

必须只根据标题和摘要判断，不要编造论文没有的信息。

输出中文。严格按照以下格式输出，不要输出 JSON：

论文推送｜{today}

今日候选论文数：{len(papers)}
最终推荐论文数：{top_k}

1. 标题：
链接：
评分：
方向：
类型：工作业务相关 / 长期主线 / 短期热点 / 新技术观察
一句话总结：
核心方法：
推荐理由：
与你的关系：
精读优先级：高 / 中 / 低 / 跟踪即可

2. 标题：
链接：
评分：
方向：
类型：
一句话总结：
核心方法：
推荐理由：
与你的关系：
精读优先级：
"""

    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V4-Flash",
        messages=[
            {
                "role": "system",
                "content": "你是严谨的 AI 论文筛选助手，只根据给定标题和摘要筛选，不编造信息。",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content
