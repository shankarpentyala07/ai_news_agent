#!/usr/bin/env python3
"""
GitHub Actions script for generating daily AI news drafts.

Uses the existing agent tools (rss_fetcher, news_curator) and Claude Opus
to generate a LinkedIn post draft for manual review and posting.

This is a non-interactive version of the agent pipeline designed for CI/CD.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.rss_fetcher import fetch_rss_feed
from tools.news_curator import filter_by_keywords, rank_by_relevance

import anthropic


def fetch_all_feeds() -> list:
    """Fetch articles from all configured RSS feeds."""
    # Load feeds config
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
    """Filter and rank articles using existing curator tools."""
    print(f"\nCurating {len(articles)} articles...")

    # Filter by AI keywords
    filtered_result = json.loads(filter_by_keywords(json.dumps(articles)))
    if filtered_result["status"] != "success":
        print(f"  Filter error: {filtered_result.get('error_message')}")
        return []

    print(f"  Filtered to {filtered_result['filtered_count']} AI-relevant articles")

    # Rank by relevance
    ranked_result = json.loads(rank_by_relevance(json.dumps(filtered_result)))
    if ranked_result["status"] != "success":
        print(f"  Ranking error: {ranked_result.get('error_message')}")
        return []

    print(f"  Ranked {ranked_result['count']} articles (excluding already posted)")

    return ranked_result.get("ranked_articles", [])


def generate_linkedin_draft(articles: list) -> str:
    """Generate LinkedIn post draft using Claude Opus."""
    if not articles:
        return "No new AI news articles found for today."

    # Take top 5 articles for the summary
    top_articles = articles[:5]

    # Format articles for the prompt
    articles_text = "\n\n".join([
        f"{i+1}. {a['title']}\n"
        f"Source: {a['source']}\n"
        f"Published: {a['published']}\n"
        f"Summary: {a['summary'][:300]}...\n"
        f"Link: {a['link']}"
        for i, a in enumerate(top_articles)
    ])

    today = datetime.now().strftime('%B %d, %Y')
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
        # Always append sources programmatically so they're never missing
        sources_section = "\n\n---\nSources:\n" + "\n".join(
            f"- {a['title']}: {a['link']}" for a in top_articles
        )
        if "---\nSources:" in draft:
            draft = draft[:draft.index("---\nSources:")].rstrip()
        draft += sources_section
        print("  Draft generated successfully!")
        return draft

    except Exception as e:
        import traceback
        print(f"  Error generating draft: {e}")
        traceback.print_exc()
        return create_fallback_draft(top_articles)


def create_fallback_draft(articles: list) -> str:
    """Create a styled draft if Claude fails."""
    today = datetime.now().strftime('%B %d, %Y')
    top = articles[:5]

    stories = "\n\n".join([
        f"🔹 {a['title']}\n{a['summary'][:200].strip()}..."
        for a in top
    ])

    sources = "\n".join([
        f"- {a['title']}: {a['link']}"
        for a in top
    ])

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
    """Save the draft to the drafts directory."""
    drafts_dir = Path(__file__).parent.parent / "drafts"
    drafts_dir.mkdir(exist_ok=True)

    today = datetime.now().strftime('%Y-%m-%d')

    # Save the LinkedIn draft
    draft_path = drafts_dir / "latest_draft.md"
    with open(draft_path, "w") as f:
        f.write(f"# AI Daily Brief - {today}\n\n")
        f.write("## LinkedIn Post Draft\n\n")
        f.write("```\n")
        f.write(draft)
        f.write("\n```\n\n")
        f.write("## Source Articles\n\n")
        for i, a in enumerate(articles[:5], 1):
            f.write(f"{i}. [{a['title']}]({a['link']}) - {a['source']}\n")

    print(f"\nDraft saved to: {draft_path}")

    # Also save dated version
    dated_path = drafts_dir / f"draft_{today}.md"
    with open(dated_path, "w") as f:
        f.write(f"# AI Daily Brief - {today}\n\n")
        f.write("## LinkedIn Post Draft\n\n")
        f.write("```\n")
        f.write(draft)
        f.write("\n```\n\n")
        f.write("## Source Articles\n\n")
        for i, a in enumerate(articles[:5], 1):
            f.write(f"{i}. [{a['title']}]({a['link']}) - {a['source']}\n")

    print(f"Dated draft saved to: {dated_path}")

    return draft_path


def main():
    """Main execution flow."""
    print("=" * 60)
    print("AI DAILY BRIEF - DRAFT GENERATOR")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Step 1: Fetch all RSS feeds
    articles = fetch_all_feeds()

    if not articles:
        print("\nNo articles fetched from any feed.")
        sys.exit(1)

    print(f"\nTotal articles fetched: {len(articles)}")

    # Step 2: Curate articles
    curated = curate_articles(articles)

    if not curated:
        print("\nNo relevant articles after curation.")
        # Still save a "no news" draft
        save_draft("No new AI news articles found for today.", [])
        sys.exit(0)

    # Step 3: Generate LinkedIn draft
    draft = generate_linkedin_draft(curated)

    # Step 4: Save draft
    save_draft(draft, curated)

    print()
    print("=" * 60)
    print("DRAFT GENERATION COMPLETE")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Review the draft in the GitHub Issue")
    print("2. Copy the LinkedIn post content")
    print("3. Go to https://www.linkedin.com/company/111211103/admin/")
    print("4. Click '+ Create' -> 'Start a post'")
    print("5. Paste and publish!")


if __name__ == "__main__":
    main()
