# AI Daily Brief

Automated AI news agent that fetches news from RSS feeds, curates content, generates LinkedIn posts using Gemini AI, and creates GitHub Issues for daily publishing.

**LinkedIn Page**: [AI Daily Brief](https://www.linkedin.com/company/111211103/)

## Features

- **Automated News Fetching**: Pulls from TechCrunch, VentureBeat, The Verge, Wired, and more
- **Smart Curation**: Filters for AI/ML relevance and ranks by importance
- **AI-Generated Posts**: Uses Gemini 2.0 Flash to create engaging LinkedIn content
- **GitHub Actions Automation**: Runs daily at 12:01 AM PST
- **GitHub Issues for Review**: Creates issues with draft posts for easy copy/paste
- **Duplicate Prevention**: Tracks posted articles to avoid repeats

## How It Works

```
Daily at 12:01 AM PST
        |
        v
+------------------+
| Fetch RSS Feeds  |  (TechCrunch, VentureBeat, The Verge, Wired, etc.)
+------------------+
        |
        v
+------------------+
| Filter & Rank    |  (AI keywords, recency, source credibility)
+------------------+
        |
        v
+------------------+
| Generate Draft   |  (Gemini 2.0 Flash creates LinkedIn post)
+------------------+
        |
        v
+------------------+
| Create GitHub    |  (Issue with draft + instructions)
| Issue            |
+------------------+
        |
        v
+------------------+
| Manual Publish   |  (Copy draft -> paste on LinkedIn)
+------------------+
```

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/shankarpentyala07/ai_news_agent.git
cd ai_news_agent
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```bash
# Google Cloud (for Gemini API)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-west1
GOOGLE_GENAI_USE_VERTEXAI=1

# LinkedIn (for reference - manual posting currently)
LINKEDIN_ORGANIZATION_ID=your-org-id
```

### 3. Set Up GitHub Secrets

Go to your repo **Settings** → **Secrets and variables** → **Actions** and add:

| Secret | Description |
|--------|-------------|
| `GOOGLE_CLOUD_PROJECT` | Your GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | GCP region (e.g., `us-west1`) |
| `GOOGLE_GENAI_USE_VERTEXAI` | Set to `1` |
| `GOOGLE_CLOUD_CREDENTIALS` | Full JSON of GCP service account key |

### 4. Enable GitHub Notifications

To get notified when new drafts are ready:
1. Go to repo → **Watch** → **Custom** → Check **Issues**
2. Or go to **Settings** → **Notifications** to configure email alerts

## Daily Workflow

1. **12:01 AM PST**: GitHub Actions runs automatically
2. **GitHub Issue Created**: Contains AI-generated LinkedIn post draft
3. **Review & Publish**: Copy the draft → paste on LinkedIn → publish

### Manual Trigger

You can also run the workflow manually:
1. Go to **Actions** tab
2. Select **Daily AI News Agent**
3. Click **Run workflow**

## RSS Feeds

Current sources in `config/feeds.json`:

| Source | Category |
|--------|----------|
| TechCrunch AI | News |
| VentureBeat | News |
| The Verge AI | News |
| Wired AI | News |
| AI News | News |
| Google AI Blog | Official |

### Add Custom Feeds

Edit `config/feeds.json`:

```json
{
  "feeds": [
    {
      "name": "Your Feed Name",
      "url": "https://example.com/feed/",
      "category": "news"
    }
  ]
}
```

## Project Structure

```
ai_news_agent/
├── .github/
│   └── workflows/
│       └── daily_news.yml      # GitHub Actions workflow
├── config/
│   ├── feeds.json              # RSS feed URLs
│   └── settings.py             # Configuration management
├── scripts/
│   ├── generate_daily_draft.py # Main draft generation script
│   ├── run_agent.py            # Manual agent execution
│   └── handle_approval.py      # Approval CLI (for full agent)
├── tools/
│   ├── rss_fetcher.py          # RSS feed fetching
│   ├── news_curator.py         # AI news filtering & ranking
│   └── social_publisher.py     # LinkedIn/Twitter posting
├── data/
│   └── schema.sql              # Database schema
├── agent.py                    # Full ADK agent definition
├── requirements.txt            # Python dependencies
└── .env                        # API credentials (gitignored)
```

## Local Development

### Test RSS Feeds

```bash
python -c "from tools.rss_fetcher import fetch_rss_feed; print(fetch_rss_feed('https://techcrunch.com/category/artificial-intelligence/feed/', 'TechCrunch AI'))"
```

### Run Draft Generation Locally

```bash
python scripts/generate_daily_draft.py
```

### Run Full Agent (with approval flow)

```bash
python scripts/run_agent.py
```

## Future Enhancements

- [ ] LinkedIn Community Management API (requires business email)
- [ ] Twitter/X integration
- [ ] Email notifications for new drafts
- [ ] Analytics dashboard
- [ ] Multi-platform support (Mastodon, Bluesky)

## Tech Stack

- **Google ADK**: Agent Development Kit for pipeline orchestration
- **Gemini 2.0 Flash**: AI model for post generation
- **GitHub Actions**: Daily automation
- **Feedparser**: RSS feed parsing
- **Python 3.11+**

## License

MIT License - Use freely, no warranties provided.

## Acknowledgments

Built with Google Agent Development Kit (ADK) and Gemini AI.
