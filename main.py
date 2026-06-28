import os
import json
import requests
import feedparser
from openai import OpenAI
from datetime import datetime, timedelta, timezone

FEISHU_WEBHOOK = os.environ["FEISHU_WEBHOOK"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url="https://api.deepinfra.com/v1/openai",
)

KEYWORDS = [
    "large language model",
    "llm agent",
    "multimodal alignment",
    "recommendation system",
    "video understanding",
    "content safety",
    "safety alignment",
    "retrieval augmented generation",
    "ai4science",
    "ai4materials",
]

CATEGORIES = ["cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.IR"]


def fetch_arxiv(max_results=30):
    query = " OR ".join([f"cat:{c}" for c in CATEGORIES])
    url = (
        "http://export.arxiv.org/api/query?"
        f"search_query={query}"
        f"&start=0&max_results={max_results}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )

    feed = feedparser.parse(url)
    papers = []

    for entry in feed.entries:
        papers.append({
            "title": entry.title.replace("\n", " ").strip(),
            "summary": entry.summary.replace("\n", " ").strip(),
            "link": entry.link,
            "published": entry.published,
            "authors": ", ".join(a.name for a in entry.authors[:5]),
        })

    return papers


def rough_filter(papers):
    selected = []
    for p in papers:
        text = (p["title"] + " " + p["summary"]).lower()
        if any(k.lower() in text for k in KEYWORDS):
            selected.append(p)
    return selected[:10]


def summarize_papers(papers):
    paper_text = "\n\n".join([
        f"Title: {p['title']}\nAuthors: {p['authors']}\nAbstract: {p['summary']}\nLink: {p['link']}"
        for p in papers
    ])

    prompt = f"""
你是一个 AI 科研论文助手。请从下面论文中选出最值得关注的 3-5 篇。

用户研究兴趣：
- LLM Agent
- 多模态对齐
- 长视频理解
- 推荐系统
- 内容安全 / safety alignment
- RAG
- AI4Science / AI4Materials

输出中文，格式如下：

论文推送｜{datetime.now().strftime('%Y-%m-%d')}

1. 标题
链接：
一句话总结：
核心方法：
为什么值得看：
与你方向的关系：
精读优先级：高/中/低

论文列表：
{paper_text}
"""

    resp = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V4-Flash",
        messages=[
            {"role": "system", "content": "你是严谨的 AI 论文筛选和总结助手。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return resp.choices[0].message.content


def push_feishu(text):
    payload = {
        "msg_type": "text",
        "content": {
            "text": "论文推送\n\n" + text
        }
    }

    r = requests.post(FEISHU_WEBHOOK, json=payload, timeout=20)
    r.raise_for_status()
    print(r.text)


def main():
    papers = fetch_arxiv()
    papers = rough_filter(papers)

    if not papers:
        push_feishu("论文推送\n\n今日未筛到明显相关论文。")
        return

    result = summarize_papers(papers)
    push_feishu(result)


if __name__ == "__main__":
    main()