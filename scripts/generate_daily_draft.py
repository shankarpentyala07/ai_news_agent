#!/usr/bin/env python3
"""
GitHub Actions script for generating daily AI news drafts.

Uses the existing agent tools (rss_fetcher, news_curator) and Gemini model
to generate a LinkedIn post draft for manual review and posting.

This is a non-interactive version of the agent pipeline designed for CI/CD.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.rss_fetcher import fetch_rss_feed
from tools.news_curator import filter_by_keywords, rank_by_relevance
from config.settings import Config

# Import Gemini for draft generation
from google import genai
from google.genai import types


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
    """Generate LinkedIn post draft using Gemini model."""
    if not articles:
        return "No new AI news articles found for today."

    # Take top 5 articles for the summary
    top_articles = articles[:5]

    # Format articles for the prompt
    articles_text = "\n\n".join([
        f"**{i+1}. {a['title']}**\n"
        f"Source: {a['source']}\n"
        f"Published: {a['published']}\n"
        f"Summary: {a['summary'][:300]}...\n"
        f"Link: {a['link']}"
        for i, a in enumerate(top_articles)
    ])

    prompt = f"""You are a social media content creator for "AI Daily Brief", a LinkedIn page that provides daily summaries of AI news.

Create an engaging LinkedIn post summarizing today's top AI news. Follow this EXACT format:

📰 AI Daily Brief - {datetime.now().strftime('%B %d, %Y')}

🔹 [Story Title] - [2-3 sentence summary explaining what happened and why it matters]

🔹 [Story Title] - [2-3 sentence summary explaining what happened and why it matters]

🔹 [Story Title] - [2-3 sentence summary explaining what happened and why it matters]

🔹 [Story Title] - [2-3 sentence summary explaining what happened and why it matters]

🔹 [Story Title] - [2-3 sentence summary explaining what happened and why it matters]

Follow AI Daily Brief for your daily AI roundup!

#AI #ArtificialIntelligence #TechNews #AINews #AIDailyBrief

---
Sources:
- [source URLs]

REQUIREMENTS:
1. Use the 📰 header with date
2. Use 🔹 emoji for EVERY bullet point (consistent formatting)
3. Each story gets a bold/clear title followed by dash and 2-3 sentence explanation
4. Include 4-5 stories from the articles provided
5. End with "Follow AI Daily Brief for your daily AI roundup!"
6. Include hashtags: #AI #ArtificialIntelligence #TechNews #AINews #AIDailyBrief
7. Add Sources section at the bottom with article links
8. Keep professional but engaging tone

Top AI news articles from the last 24 hours:

{articles_text}

Generate the LinkedIn post now:"""

    print("\nGenerating LinkedIn draft with Gemini...")

    try:
        # Create Gemini client
        client = genai.Client(
            vertexai=Config.GOOGLE_GENAI_USE_VERTEXAI,
            project=Config.GOOGLE_CLOUD_PROJECT,
            location=Config.GOOGLE_CLOUD_LOCATION
        )

        # Generate content
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=1000
            )
        )

        draft = response.text
        print("  Draft generated successfully!")
        return draft

    except Exception as e:
        print(f"  Error generating draft: {e}")
        # Fallback to a simple template
        return create_fallback_draft(top_articles)


def create_fallback_draft(articles: list) -> str:
    """Create a simple draft if Gemini fails."""
    today = datetime.now().strftime('%B %d, %Y')

    headlines = "\n".join([
        f"- {a['title']} ({a['source']})"
        for a in articles[:5]
    ])

    return f"""AI Daily Brief - {today}

Here are today's top AI stories:

{headlines}

What AI development are you most excited about?

#AIDailyBrief #AI #ArtificialIntelligence #TechNews"""


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
