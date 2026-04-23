#!/usr/bin/env python3
import json
import os
import re
import sys
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.rss_fetcher import fetch_rss_feed
from tools.news_curator import filter_by_keywords, rank_by_relevance
import anthropic


def strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text).strip()


# Unicode sans-serif bold — the only bold that renders on LinkedIn
_BOLD = {
    **{chr(ord('a') + i): chr(0x1D5EE + i) for i in range(26)},
    **{chr(ord('A') + i): chr(0x1D5D4 + i) for i in range(26)},
    **{chr(ord('0') + i): chr(0x1D7EC + i) for i in range(10)},
}

def apply_bold(text: str) -> str:
    """Convert **word** markers to LinkedIn-renderable bold Unicode."""
    def make_bold(match):
        return ''.join(_BOLD.get(c, c) for c in match.group(1))
    return re.sub(r'\*\*(.+?)\*\*', make_bold, text)


def fetch_all_feeds() -> list:
    feeds_path = Path(__file__).parent.parent / "config" / "feeds.json"
    with open(feeds_path, "r") as f:
        feeds_config = json.load(f)

    all_articles = []
    print("Fetching RSS feeds...")
    for feed in feeds_config["feeds"]:
        print(f"  - {feed['name']}...")
        result = json.loads(fetch_rss_feed(feed["url"], feed["name"], hours_back=24))
        if result["status"] == "success":
            print(f"    Found {result['count']} articles")
            all_articles.extend(result["articles"])
        else:
            print(f"    Error: {result.get('error_message', 'Unknown')}")

    return all_articles


def curate_articles(articles: list) -> list:
    print(f"\nCurating {len(articles)} articles...")

    filtered_result = json.loads(filter_by_keywords(json.dumps(articles)))
    if filtered_result["status"] != "success":
        print(f"  Filter error: {filtered_result.get('error_message')}")
        return []
    print(f"  Filtered to {filtered_result['filtered_count']} AI-relevant articles")

    ranked_result = json.loads(rank_by_relevance(json.dumps(filtered_result)))
    if ranked_result["status"] != "success":
        print(f"  Ranking error: {ranked_result.get('error_message')}")
        return []
    print(f"  Ranked {ranked_result['count']} articles (excluding already posted)")

    return ranked_result.get("ranked_articles", [])


def generate_linkedin_draft(articles: list) -> str:
    if not articles:
        return "No new AI news articles found for today."

    top_articles = articles[:5]
    today = datetime.now().strftime('%B %d, %Y')

    articles_text = "\n".join([
        f"{i+1}. {strip_html(a['title'])}"
        for i, a in enumerate(top_articles)
    ])

    prompt = f"""You are the expert editor of "AI Daily Brief", a professional LinkedIn page for AI practitioners and business leaders.

Write today's LinkedIn post. Output ONLY the post text, nothing else.

EXACT FORMAT TO FOLLOW:

AI Daily Brief | {today}
[One sharp, thought-provoking hook sentence about today's AI landscape. Not generic.]
_______________

* [Story 1 headline — bold the company name and 1-2 key terms using **word** markers]
* [Story 2 headline — bold the company name and 1-2 key terms using **word** markers]
* [Story 3 headline — bold the company name and 1-2 key terms using **word** markers]
* [Story 4 headline — bold the company name and 1-2 key terms using **word** markers]
* [Story 5 headline — bold the company name and 1-2 key terms using **word** markers]

#AI #ArtificialIntelligence #AIDailyBrief [generate 4-6 hashtags derived ONLY from the companies, products, and technologies mentioned in today's stories — e.g. #OpenAI #Gemini #Robotics #LLM #AgenticAI]

RULES:
- No HTML. Use **word** to mark bold terms — do not use any other formatting
- Each * bullet is ONE line — the headline only, no extra sentences
- Bold the company/product name and the most important technical term in each headline
- The hook must feel original, not a cliche
- Every hashtag must be directly relevant to a story in the post — no generic filler tags

Today's stories:
{articles_text}

Write the post now:"""

    print("\nGenerating LinkedIn draft with Claude Opus...")
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        draft = apply_bold(response.content[0].text.strip())
    except Exception as e:
        print(f"  Error generating draft: {e}")
        traceback.print_exc()
        return create_fallback_draft(top_articles)

    sources_section = "\n\n---\nSources:\n" + "\n".join(
        f"- {a['title']}: {a['link']}" for a in top_articles
    )
    if "---\nSources:" in draft:
        draft = draft[:draft.index("---\nSources:")].rstrip()
    draft += sources_section

    print("  Draft generated successfully!")
    return draft


def create_fallback_draft(articles: list) -> str:
    today = datetime.now().strftime('%B %d, %Y')
    top = articles[:5]

    stories = "\n".join([f"* {strip_html(a['title'])}" for a in top])
    sources = "\n".join([f"- {strip_html(a['title'])}: {a['link']}" for a in top])

    return f"""AI Daily Brief | {today}
The AI space never sleeps — here's what you need to know today.
_______________

{stories}

#AI #ArtificialIntelligence #AIDailyBrief #MachineLearning #TechNews

---
Sources:
{sources}"""


def save_draft(draft: str, articles: list):
    drafts_dir = Path(__file__).parent.parent / "drafts"
    drafts_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')

    def write_file(path):
        with open(path, "w") as f:
            f.write(f"# AI Daily Brief - {today}\n\n## LinkedIn Post Draft\n\n```\n{draft}\n```\n\n## Source Articles\n\n")
            for i, a in enumerate(articles[:5], 1):
                f.write(f"{i}. [{a['title']}]({a['link']}) - {a['source']}\n")

    latest = drafts_dir / "latest_draft.md"
    dated = drafts_dir / f"draft_{today}.md"
    write_file(latest)
    write_file(dated)
    print(f"\nDraft saved to: {latest}")
    print(f"Dated draft saved to: {dated}")
    return latest


def main():
    print("=" * 60)
    print("AI DAILY BRIEF - DRAFT GENERATOR")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    articles = fetch_all_feeds()
    if not articles:
        print("\nNo articles fetched from any feed.")
        sys.exit(1)
    print(f"\nTotal articles fetched: {len(articles)}")

    curated = curate_articles(articles)
    if not curated:
        print("\nNo relevant articles after curation.")
        save_draft("No new AI news articles found for today.", [])
        sys.exit(0)

    draft = generate_linkedin_draft(curated)
    save_draft(draft, curated)

    print("\n" + "=" * 60)
    print("DRAFT GENERATION COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review the draft in the GitHub Issue")
    print("2. Go to https://www.linkedin.com/company/111211103/admin/")
    print("3. Paste and publish!")


if __name__ == "__main__":
    main()
