# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI News Agent is an automated pipeline that fetches AI news from RSS feeds, curates content, drafts social media posts, gets human approval, and publishes to LinkedIn and Twitter. Built using Google Agent Development Kit (ADK) with Gemini 2.5 Flash.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent manually (fetches news, drafts posts, waits for approval)
python scripts/run_agent.py

# Approve drafted posts for publishing
python scripts/handle_approval.py --session <session_id> --approve

# Reject drafted posts
python scripts/handle_approval.py --session <session_id> --reject

# Test RSS feed fetching
python -c "from tools.rss_fetcher import fetch_rss_feed; print(fetch_rss_feed('http://arxiv.org/rss/cs.AI', 'ArXiv AI'))"
```

## Architecture

The agent uses a **sequential pipeline** with one parallel stage:

```
RSSFetcherTeam (ParallelAgent) → NewsCuratorAgent → PostDrafterAgent → ApprovalAgent → PublisherAgent
```

### Pipeline Stages (agent.py)

1. **RSSFetcherTeam**: ParallelAgent containing three sub-agents that fetch feeds concurrently (ArXiv, TechCrunch, VentureBeat). Each uses `output_key` to store results.

2. **NewsCuratorAgent**: Filters articles by AI keywords, ranks by relevance/recency/source credibility, excludes already-posted articles. Uses `{arxiv_results}`, `{techcrunch_results}`, `{venturebeat_results}` template variables.

3. **PostDrafterAgent**: Creates platform-specific drafts using `{curated_news}` from previous stage.

4. **ApprovalAgent**: Human-in-loop pattern using `ToolContext.request_confirmation()`. Pauses execution until user approves/rejects via CLI.

5. **PublisherAgent**: Posts to LinkedIn/Twitter APIs, records article in SQLite to prevent duplicates.

### Key Patterns

- **Data flow**: Agents pass data via `output_key` attributes and `{variable}` templates in instructions
- **Resumability**: `ResumabilityConfig(is_resumable=True)` enables pause/resume for human approval
- **Session persistence**: `DatabaseSessionService` with SQLite stores session state
- **Retry logic**: `types.HttpRetryOptions` on Gemini model + `tenacity` decorators on API calls

## Configuration

- **Environment**: `.env` file with Google Cloud, LinkedIn, and Twitter credentials
- **RSS feeds**: `config/feeds.json` - add/remove news sources here
- **AI keywords**: `tools/news_curator.py:AI_KEYWORDS` list for relevance filtering
- **Source credibility scores**: `tools/news_curator.py:rank_by_relevance()` function

## Data Storage

- `data/sessions.db`: ADK session state for pause/resume
- `data/posted_articles.db`: Tracks posted articles (prevents duplicates)

## Tool Functions

Tools return JSON strings (not dicts) for ADK compatibility. Each tool in `tools/` follows this pattern:
- Returns `{"status": "success"|"error", ...}`
- Handles own database connections
- Uses `Config` class for credentials/paths
