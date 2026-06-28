import feedparser
from urllib.parse import quote


def fetch_arxiv(categories, max_results=200):
    query = " OR ".join([f"cat:{category}" for category in categories])
    encoded_query = quote(query, safe="")

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
            authors = [author.name for author in entry.authors[:5]]

        papers.append({
            "title": entry.title.replace("\n", " ").strip(),
            "summary": entry.summary.replace("\n", " ").strip(),
            "link": entry.link,
            "published": getattr(entry, "published", ""),
            "authors": ", ".join(authors),
        })

    return papers


def rough_filter(papers, positive_keywords, negative_keywords=None, limit=80):
    negative_keywords = negative_keywords or []
    selected = []

    for paper in papers:
        text = (paper["title"] + " " + paper["summary"]).lower()

        positive_hit = any(keyword.lower() in text for keyword in positive_keywords)
        negative_hit = any(keyword.lower() in text for keyword in negative_keywords)

        if positive_hit and not negative_hit:
            selected.append(paper)

    if not selected:
        return papers[:min(limit, len(papers))]

    return selected[:limit]
