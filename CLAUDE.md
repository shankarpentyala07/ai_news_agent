# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Daily Brief is an automated pipeline that fetches AI news from RSS feeds, curates content, and generates LinkedIn posts using Gemini AI. The system runs daily via GitHub Actions and creates GitHub Issues with draft posts for manual publishing to LinkedIn.

**LinkedIn Page**: [AI Daily Brief](https://www.linkedin.com/company/111211103/)

## Commands

**Note**: Always use `python3` for this project (not `python`).

```bash
# Activate virtual environment first
source venv/bin/activate

# Install dependencies
pip3 install -r requirements.txt

# Run the GitHub Actions draft generator locally
python3 scripts/generate_daily_draft.py

# Run the full agent manually (with approval flow)
python3 scripts/run_agent.py

# Test RSS feed fetching
python3 -c "from tools.rss_fetcher import fetch_rss_feed; print(fetch_rss_feed('https://techcrunch.com/category/artificial-intelligence/feed/', 'TechCrunch AI'))"
```

## Daily Workflow

The project uses **GitHub Actions** for automation:

1. **Trigger**: Runs daily at 12:01 AM PST (cron: `1 8 * * *` UTC)
2. **Fetch**: Pulls articles from 6 RSS feeds (TechCrunch, VentureBeat, The Verge, Wired, AI News, Google AI Blog)
3. **Curate**: Filters for AI relevance, ranks by importance, excludes already-posted articles
4. **Generate**: Uses Gemini 2.0 Flash to create engaging LinkedIn post draft
5. **Issue**: Creates GitHub Issue with the draft for review
6. **Publish**: Manual copy/paste to LinkedIn (Community Management API requires business email)

## Architecture

### GitHub Actions Flow (Primary)

The daily workflow uses `generate_daily_draft.py` which **directly calls tool functions** (no agents):

```
.github/workflows/daily_news.yml
        ↓
scripts/generate_daily_draft.py
        ↓
tools/rss_fetcher.py + tools/news_curator.py (direct function calls)
        ↓
Gemini 2.0 Flash (draft generation via google.genai)
        ↓
GitHub Issue with draft
```

### Full Agent Flow (Alternative)

The ADK-based agent pipeline in `agent.py` uses **SequentialAgent and ParallelAgent** for a more sophisticated flow with human-in-the-loop approval:

```
ai_news_pipeline (SequentialAgent)
├── rss_fetcher_team (ParallelAgent)
│   ├── arxiv_fetcher (Agent)
│   ├── techcrunch_fetcher (Agent)
│   └── venturebeat_fetcher (Agent)
├── news_curator (Agent)
├── post_drafter (Agent)
├── approval_agent (Agent) ← Human-in-Loop pause point
└── publisher_agent (Agent)
```

Run with: `python scripts/run_agent.py`

## Key Files

| File | Purpose |
|------|---------|
| `scripts/generate_daily_draft.py` | Main script for GitHub Actions - fetches, curates, generates draft |
| `.github/workflows/daily_news.yml` | GitHub Actions workflow configuration |
| `config/feeds.json` | RSS feed URLs and categories |
| `tools/rss_fetcher.py` | RSS feed fetching with feedparser |
| `tools/news_curator.py` | AI keyword filtering and relevance ranking |
| `agent.py` | Full ADK agent definition (for interactive mode) |

## RSS Feeds

Current sources in `config/feeds.json`:
- TechCrunch AI
- VentureBeat (via FeedBurner)
- The Verge AI
- Wired AI
- AI News
- Google AI Blog

To add a feed, edit `config/feeds.json`:
```json
{"name": "Feed Name", "url": "https://example.com/feed/", "category": "news"}
```

## Configuration

### Environment Variables

Required for GitHub Actions (set as repository secrets):
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `GOOGLE_CLOUD_LOCATION`: GCP region (e.g., `us-west1`)
- `GOOGLE_GENAI_USE_VERTEXAI`: Set to `1`
- `GOOGLE_CLOUD_CREDENTIALS`: Full JSON of GCP service account key

### Local Development

Create `.env` file:
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-west1
GOOGLE_GENAI_USE_VERTEXAI=1
LINKEDIN_ORGANIZATION_ID=111211103
```

## Tool Functions

Tools return JSON strings (not dicts) for ADK compatibility:
- Returns `{"status": "success"|"error", ...}`
- Handles own database connections
- Uses `Config` class from `config/settings.py`

## Data Storage

- `drafts/`: Generated LinkedIn post drafts
- `data/posted_articles.db`: Tracks posted articles (prevents duplicates)
- `data/sessions.db`: ADK session state (for full agent mode)

## GitHub Notifications

To get notified when new drafts are ready:
1. Go to repo → Watch → Custom → Check "Issues"
2. Or configure email notifications in GitHub Settings

## Future Work

- LinkedIn Community Management API integration (requires business email)
- Twitter/X integration
- Multi-platform support (Mastodon, Bluesky)
