from utils.config import load_interest, load_profile
from utils.arxiv import fetch_arxiv, rough_filter
from utils.llm import rank_and_summarize
from utils.feishu import push_feishu


def main():
    interest = load_interest()
    profile = load_profile()

    top_k = interest.get("top_k", 20)
    fetch_max_results = interest.get("fetch_max_results", 250)
    categories = interest.get("categories", ["cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.IR"])
    positive_keywords = interest.get("positive_keywords", [])
    negative_keywords = interest.get("negative_keywords", [])

    papers = fetch_arxiv(
        categories=categories,
        max_results=fetch_max_results,
    )

    if not papers:
        push_feishu("论文推送\n\n今日 arXiv 没有抓取到论文。")
        return

    selected_papers = rough_filter(
        papers=papers,
        positive_keywords=positive_keywords,
        negative_keywords=negative_keywords,
        limit=80,
    )

    result = rank_and_summarize(
        papers=selected_papers,
        profile=profile,
        top_k=top_k,
    )

    push_feishu(result)


if __name__ == "__main__":
    main()
