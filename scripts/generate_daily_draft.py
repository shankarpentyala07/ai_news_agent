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


# ── Helpers ───────────────────────────────────────────────────────────────────

def strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text).strip()


# Unicode sans-serif bold — the only bold that renders on LinkedIn
_BOLD = {
    **{chr(ord('a') + i): chr(0x1D5EE + i) for i in range(26)},
    **{chr(ord('A') + i): chr(0x1D5D4 + i) for i in range(26)},
    **{chr(ord('0') + i): chr(0x1D7EC + i) for i in range(10)},
}

def apply_bold(text: str) -> str:
    def make_bold(match):
        return ''.join(_BOLD.get(c, c) for c in match.group(1))
    return re.sub(r'\*\*(.+?)\*\*', make_bold, text)


# Rotating daily hooks so the post never feels templated
_HOOKS = [
    "The gap between AI hype and AI deployment is closing — fast.",
    "Every frontier AI lab is racing to own the enterprise stack — here's today's proof.",
    "AI isn't coming for jobs — it's coming for entire workflows. Today's evidence:",
    "The real AI arms race isn't about models. It's about who controls the infrastructure.",
    "Agent-to-agent communication is becoming the new API. Here's what's moving:",
    "Open source just landed another punch at closed AI. Today's biggest moves:",
    "The line between AI research and AI product is disappearing. Today's headlines:",
    "Whoever controls the AI tooling layer controls the future. Here's what shifted today:",
    "AI is moving from co-pilot to autonomous operator. Today's stories show how:",
    "Foundation models are becoming commodities. The battle is now above and below them.",
    "Enterprise AI adoption just hit another inflection point. Here's what happened:",
    "The multimodal era is fully here. Today's AI landscape in five stories:",
    "Regulation, funding, and breakthroughs all moved today. Here's your briefing:",
    "AI agents are getting memory, tools, and autonomy. Today's proof points:",
    "The compute war, the model war, and the distribution war — all in today's news:",
]

def daily_hook() -> str:
    return _HOOKS[datetime.now().timetuple().tm_yday % len(_HOOKS)]


# Known AI companies and their display names for LinkedIn tagging
KNOWN_COMPANIES = {
    'openai': 'OpenAI', 'google': 'Google', 'anthropic': 'Anthropic',
    'meta': 'Meta', 'microsoft': 'Microsoft', 'apple': 'Apple',
    'amazon': 'Amazon', 'nvidia': 'NVIDIA', 'hugging face': 'Hugging Face',
    'mistral': 'Mistral AI', 'cohere': 'Cohere', 'deepmind': 'DeepMind',
    'stability ai': 'Stability AI', 'midjourney': 'Midjourney',
    'perplexity': 'Perplexity AI', 'xai': 'xAI', 'salesforce': 'Salesforce',
    'ibm': 'IBM', 'intel': 'Intel', 'amd': 'AMD', 'aws': 'AWS',
    'tesla': 'Tesla', 'github': 'GitHub', 'vercel': 'Vercel',
    'databricks': 'Databricks', 'together ai': 'Together AI',
}


# ── Pipeline steps ─────────────────────────────────────────────────────────────

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


def deduplicate_articles(articles: list) -> list:
    """Remove near-duplicate stories, keeping the highest-priority source."""
    stop = {'a','an','the','is','it','in','on','at','to','for','of','and','or','but','with','its','by','as','that'}
    priority = {'mit':5,'arxiv':5,'techcrunch':4,'venturebeat':4,'hugging face':4,'google':4,'wired':3,'verge':3}

    def words(title):
        return set(w for w in re.sub(r'[^\w\s]', '', title.lower()).split() if w not in stop and len(w) > 2)

    def rank(a):
        src = a.get('source', '').lower()
        return next((v for k, v in priority.items() if k in src), 2)

    kept = []
    for article in articles:
        w = words(strip_html(article.get('title', '')))
        dup_idx = None
        for i, existing in enumerate(kept):
            ew = words(strip_html(existing.get('title', '')))
            if w and ew and len(w | ew) > 0:
                if len(w & ew) / len(w | ew) > 0.5:
                    dup_idx = i
                    break
        if dup_idx is not None:
            if rank(article) > rank(kept[dup_idx]):
                kept[dup_idx] = article
        else:
            kept.append(article)

    removed = len(articles) - len(kept)
    if removed:
        print(f"  Removed {removed} duplicate stories")
    return kept


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

    articles = ranked_result.get("ranked_articles", [])
    articles = deduplicate_articles(articles)
    print(f"  Final pool: {len(articles)} articles")
    return articles


def extract_companies(articles: list) -> list:
    """Return display names of known companies mentioned in article titles."""
    found = set()
    for article in articles:
        title = strip_html(article.get('title', '')).lower()
        for key, name in KNOWN_COMPANIES.items():
            if key in title:
                found.add(name)
    return sorted(found)


def generate_post_image(articles: list, output_path: Path) -> Path:
    """Generate a 1200x627 LinkedIn post image card."""
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1200, 627
    BG, ACCENT, WHITE, GRAY, DIM = '#0D1117', '#58A6FF', '#E6EDF3', '#8B949E', '#21262D'

    img = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)

    def load_font(path, size):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()

    base = '/usr/share/fonts/truetype/dejavu/DejaVuSans'
    f_title = load_font(f'{base}-Bold.ttf', 48)
    f_date  = load_font(f'{base}.ttf', 26)
    f_story = load_font(f'{base}.ttf', 23)
    f_small = load_font(f'{base}.ttf', 18)

    # Left accent stripe
    draw.rectangle([0, 0, 8, H], fill=ACCENT)

    # Header
    draw.text((56, 44), 'AI Daily Brief', font=f_title, fill=ACCENT)
    draw.text((56, 108), datetime.now().strftime('%B %d, %Y'), font=f_date, fill=GRAY)
    draw.line([(56, 152), (W - 56, 152)], fill=DIM, width=2)

    # Stories
    y = 172
    for article in articles[:5]:
        title = strip_html(article.get('title', ''))
        if len(title) > 74:
            title = title[:71] + '...'
        draw.text((56, y), f'›  {title}', font=f_story, fill=WHITE)
        y += 48

    # Footer
    draw.line([(56, y + 8), (W - 56, y + 8)], fill=DIM, width=2)
    draw.text((56, y + 22), 'Follow AI Daily Brief for your daily AI roundup', font=f_small, fill=GRAY)
    draw.text((W - 310, y + 22), 'linkedin.com/company/111211103', font=f_small, fill=GRAY)

    img.save(output_path, 'PNG')
    return output_path


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

EXACT FORMAT TO FOLLOW (copy structure exactly, no blank lines around the ___ separator):

AI Daily Brief | {today}
[hook sentence]
_______________
* [Story 1 headline — bold the company name and 1-2 key terms using **word** markers]
* [Story 2 headline — bold the company name and 1-2 key terms using **word** markers]
* [Story 3 headline — bold the company name and 1-2 key terms using **word** markers]
* [Story 4 headline — bold the company name and 1-2 key terms using **word** markers]
* [Story 5 headline — bold the company name and 1-2 key terms using **word** markers]

#AI #ArtificialIntelligence #AIDailyBrief [4-6 hashtags from the companies, products, and technologies in today's stories]

RULES:
- Output ONLY the post — no explanations, no meta-commentary, no "instead of..." phrases
- No HTML. Use **word** to mark bold terms — do not use any other formatting
- Each * bullet is ONE line — the rewritten headline only, nothing else
- Bold the company/product name and the most important technical term in each headline
- Hook: one sharp sentence about today's AI landscape. Specific to today's news, not generic
- Every hashtag must match a company or technology actually in the post

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
        f"- {strip_html(a['title'])}: {a['link']}" for a in top_articles
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
{daily_hook()}
_______________
{stories}

#AI #ArtificialIntelligence #AIDailyBrief #MachineLearning #TechNews

---
Sources:
{sources}"""


def save_draft(draft: str, articles: list, image_path: Path = None):
    drafts_dir = Path(__file__).parent.parent / "drafts"
    drafts_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')

    companies = extract_companies(articles[:5])
    tag_note = ""
    if companies:
        tag_note = f"\n\n## 📌 Tag These Companies on LinkedIn\n\nWhen posting, manually tag: **{', '.join(companies)}**\n(Type @ before each name in the LinkedIn composer)\n"

    image_note = ""
    if image_path:
        image_note = f"\n\n## 🖼️ Post Image\n\nDownload `post_image.png` from the workflow **Artifacts** tab and attach it to the LinkedIn post.\n"

    def write_file(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# AI Daily Brief - {today}\n\n")
            f.write("## LinkedIn Post Draft\n\n```\n")
            f.write(draft)
            f.write("\n```\n")
            f.write(tag_note)
            f.write(image_note)
            f.write("\n## Source Articles\n\n")
            for i, a in enumerate(articles[:5], 1):
                f.write(f"{i}. [{strip_html(a['title'])}]({a['link']}) - {a['source']}\n")

    latest = drafts_dir / "latest_draft.md"
    dated  = drafts_dir / f"draft_{today}.md"
    write_file(latest)
    write_file(dated)
    print(f"\nDraft saved to: {latest}")
    return latest


# ── Main ───────────────────────────────────────────────────────────────────────

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

    # Generate post image
    image_path = None
    drafts_dir = Path(__file__).parent.parent / "drafts"
    drafts_dir.mkdir(exist_ok=True)
    try:
        image_path = drafts_dir / "post_image.png"
        generate_post_image(curated[:5], image_path)
        print(f"Post image saved to: {image_path}")
    except Exception as e:
        print(f"Image generation skipped: {e}")
        image_path = None

    save_draft(draft, curated, image_path)

    print("\n" + "=" * 60)
    print("DRAFT GENERATION COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review the draft in the GitHub Issue")
    print("2. Download post_image.png from workflow Artifacts")
    print("3. Go to https://www.linkedin.com/company/111211103/admin/")
    print("4. Paste post, attach image, tag companies, and publish!")


if __name__ == "__main__":
    main()
