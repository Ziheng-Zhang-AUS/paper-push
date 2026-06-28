import os
import requests
import feedparser
from openai import OpenAI
from datetime import datetime
from urllib.parse import quote


FEISHU_WEBHOOK = os.environ["FEISHU_WEBHOOK"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api.deepinfra.com/v1/openai",
)

KEYWORDS = [
    "large language model",
    "llm",
    "llm agent",
    "agent",
    "multimodal",
    "multimodal alignment",
    "vision-language",
    "recommendation system",
    "recommender system",
    "video understanding",
    "long video",
    "content safety",
    "safety alignment",
    "retrieval augmented generation",
    "rag",
    "ai4science",
    "ai4materials",
]

CATEGORIES = ["cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.IR"]


def fetch_arxiv(max_results=50):
    query = " OR ".join([f"cat:{c}" for c in CATEGORIES])
    encoded_query = quote(query)

    url = (
        "https://export.arxiv.org/api/query?"
        f"search_query={encoded_query}"
        f"&start=0"
        f"&max_results={max_results}"
        f"&sortBy=submittedDate"
        f"&sortOrder=descending"
    )

    feed = feedparser.parse(url)

    if getattr(feed, "bozo", False):
        raise RuntimeError(f"Failed to parse arXiv feed: {feed.bozo_exception}")

    papers = []

    for entry in feed.entries:
        authors = []
        if hasattr(entry, "authors"):
            authors = [a.name for a in entry.authors[:5]]

        papers.append({
            "title": entry.title.replace("\n", " ").strip(),
            "summary": entry.summary.replace("\n", " ").strip(),
            "link": entry.link,
            "published": getattr(entry, "published", ""),
            "authors": ", ".join(authors),
        })

    return papers


def rough_filter(papers, limit=12):
    selected = []

    for paper in papers:
        text = (paper["title"] + " " + paper["summary"]).lower()
        if any(keyword.lower() in text for keyword in KEYWORDS):
            selected.append(paper)

    return selected[:limit]


def fallback_select(papers, limit=10):
    return papers[:limit]


def summarize_papers(papers):
    paper_text = "\n\n".join([
        f"Title: {p['title']}\n"
        f"Authors: {p['authors']}\n"
        f"Published: {p['published']}\n"
        f"Abstract: {p['summary']}\n"
        f"Link: {p['link']}"
        for p in papers
    ])

    today = datetime.now().strftime("%Y-%m-%d")

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

筛选原则：
- 优先选择方法上有实质创新的论文
- 优先选择和大模型、多模态、推荐、内容安全、视频理解相关的论文
- 降低纯应用包装、纯 benchmark、纯 prompt trick 的优先级
- 如果论文列表整体质量一般，也要如实说明

输出中文，严格使用下面格式：

论文推送｜{today}

1. 标题：
链接：
一句话总结：
核心方法：
为什么值得看：
与你方向的关系：
精读优先级：高/中/低

2. 标题：
链接：
一句话总结：
核心方法：
为什么值得看：
与你方向的关系：
精读优先级：高/中/低

论文列表：
{paper_text}
"""

    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V4-Flash",
        messages=[
            {
                "role": "system",
                "content": "你是严谨的 AI 论文筛选和总结助手，只根据给定论文标题和摘要判断，不编造不存在的信息。",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content


def push_feishu(text):
    payload = {
        "msg_type": "text",
        "content": {
            "text": "论文推送\n\n" + text
        }
    }

    response = requests.post(FEISHU_WEBHOOK, json=payload, timeout=30)
    response.raise_for_status()
    print(response.text)


def main():
    papers = fetch_arxiv()

    if not papers:
        push_feishu("论文推送\n\n今日 arXiv 没有抓取到论文。")
        return

    selected_papers = rough_filter(papers)

    if not selected_papers:
        selected_papers = fallback_select(papers)

    result = summarize_papers(selected_papers)
    push_feishu(result)


if __name__ == "__main__":
    main()
