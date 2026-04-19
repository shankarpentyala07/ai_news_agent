#!/usr/bin/env python3
import json
import os
import sys
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.rss_fetcher import fetch_rss_feed
from tools.news_curator import filter_by_keywords, rank_by_relevance
import anthropic


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

    articles_text = "\n\n".join([
        f"{i+1}. {a['title']}\n"
        f"Source: {a['source']}\n"
        f"Summary: {a['summary'][:300]}...\n"
        f"Link: {a['link']}"
        for i, a in enumerate(top_articles)
    ])

    prompt = f"""You are the expert editor of "AI Daily Brief", a professional LinkedIn page followed by thousands of AI practitioners, researchers, and business leaders.

Your job: write today's LinkedIn post that feels like it was crafted by a senior tech journalist — insightful, punchy, and worth sharing.

EXACT OUTPUT FORMAT (copy this structure precisely, no deviations):

📰 AI Daily Brief | {today}

[One compelling hook sentence about today's AI landscape — make it thought-provoking, not generic]

━━━━━━━━━━━━━━━━━━━━━━

🔹 [Story headline in your own words]
[2-3 sentences: what happened → why it matters → what it signals for the industry. Be specific, not vague.]

🔹 [Story headline in your own words]
[2-3 sentences: what happened → why it matters → what it signals for the industry.]

🔹 [Story headline in your own words]
[2-3 sentences: what happened → why it matters → what it signals for the industry.]

🔹 [Story headline in your own words]
[2-3 sentences: what happened → why it matters → what it signals for the industry.]

━━━━━━━━━━━━━━━━━━━━━━

[One closing sentence that sparks curiosity or discussion — end with a question or bold observation]

Follow AI Daily Brief for your daily AI roundup! 🚀

#AI #ArtificialIntelligence #AIDailyBrief [add 4-6 specific hashtags matching today's topics]

STRICT RULES:
- NO asterisks, NO markdown, NO bullet dashes — use only the 🔹 emoji shown above
- The hook and closing lines must feel original and insightful, not templated
- Each story summary must explain the real-world impact, not just restate the headline
- Hashtags must reflect the specific companies/topics in today's stories (e.g. #OpenAI #Robotics #LLM)
- Keep the entire post under 1300 characters so it reads well on mobile

Today's top AI stories:

{articles_text}

Write the LinkedIn post now:"""

    print("\nGenerating LinkedIn draft with Claude Opus...")
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        draft = response.content[0].text.strip()
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

    stories = "\n\n".join([
        f"🔹 {a['title']}\n{a['summary'][:200].strip()}..."
        for a in top
    ])
    sources = "\n".join([f"- {a['title']}: {a['link']}" for a in top])

    return f"""📰 AI Daily Brief | {today}

The AI space never sleeps — here's what you need to know today.

━━━━━━━━━━━━━━━━━━━━━━

{stories}

━━━━━━━━━━━━━━━━━━━━━━

What story catches your eye today? Drop a comment below 👇

Follow AI Daily Brief for your daily AI roundup! 🚀

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
