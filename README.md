# AI News Posting Agent

Automated agent that fetches AI news from RSS feeds, curates content, drafts social media posts, gets human approval, and publishes to LinkedIn and Twitter daily.

## Features

- **Automated News Fetching**: Pulls from ArXiv, TechCrunch, VentureBeat, and other AI news sources
- **Smart Curation**: Filters for AI/ML relevance and ranks by importance
- **Multi-Platform Posting**: Creates platform-specific content for LinkedIn and Twitter
- **Human-in-Loop Approval**: Requires manual approval before publishing (safety first!)
- **Duplicate Prevention**: Tracks posted articles to avoid repeats
- **Scheduled Execution**: Runs daily at 6am via cron job
- **Retry Logic**: Handles API rate limits and temporary failures gracefully

## Architecture

```
RSSFetcherTeam (ParallelAgent)
  ├─ ArXiv Fetcher
  ├─ TechCrunch Fetcher
  └─ VentureBeat Fetcher
      ↓
NewsCuratorAgent (filters & ranks)
      ↓
PostDrafterAgent (creates LinkedIn/Twitter drafts)
      ↓
ApprovalAgent (human-in-loop - pauses here)
      ↓
PublisherAgent (posts to social media)
```

## Prerequisites

1. **Python 3.11+**
2. **Google Cloud Project** with Vertex AI enabled
3. **LinkedIn Developer Account** (for API access)
4. **Twitter Developer Account** (for API access)

## Installation

### 1. Install Dependencies

```bash
cd /Users/shankarpentyala/Desktop/agents-repo/kaggle-course/ai_news_agent
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-west1
GOOGLE_GENAI_USE_VERTEXAI=1

# LinkedIn API
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token

# Twitter API
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
```

### 3. Set Up Social Media APIs

#### LinkedIn API Setup

1. Go to https://www.linkedin.com/developers/
2. Create a new app
3. Request access to "Share on LinkedIn" API product
4. Complete OAuth 2.0 flow to get access token
5. Required scopes: `w_member_social`, `r_liteprofile`
6. Add token to `.env`

**Note**: LinkedIn access tokens expire. You'll need to implement token refresh logic for production use.

#### Twitter API Setup

1. Go to https://developer.twitter.com/
2. Apply for developer account
3. Create a new app
4. Set app permissions to "Read and Write"
5. Generate API keys and access tokens
6. Add all tokens to `.env`

**Rate Limits**: Twitter allows 50 tweets per 24 hours (well within our 1/day requirement).

### 4. Initialize Database

The database will be created automatically on first run, but you can initialize it manually:

```bash
sqlite3 data/posted_articles.db < data/schema.sql
```

## Usage

### Manual Execution

Run the agent manually to test:

```bash
python scripts/run_agent.py
```

This will:
1. Fetch RSS feeds from multiple sources
2. Filter and rank AI news
3. Draft LinkedIn and Twitter posts
4. Pause and display posts for your approval
5. Wait for you to approve or reject

### Approve/Reject Posts

After reviewing the drafts, approve or reject:

```bash
# To approve and publish
python scripts/handle_approval.py --session news_run_20260104 --approve

# To reject (do not publish)
python scripts/handle_approval.py --session news_run_20260104 --reject
```

Replace `news_run_20260104` with the session ID shown in the output.

### Set Up Daily Automation

Install the cron job for daily 6am execution:

```bash
bash scripts/setup_cron.sh
```

This will:
- Add a cron job to run at 6:00 AM daily
- Log output to `logs/cron.log`
- Keep your computer running or use a cloud VM

### Monitor Cron Execution

View the cron log:

```bash
tail -f logs/cron.log
```

List cron jobs:

```bash
crontab -l
```

Remove cron job:

```bash
crontab -e  # Delete the line containing 'ai_news_agent'
```

## Configuration

### RSS Feeds

Edit `config/feeds.json` to add/remove news sources:

```json
{
  "feeds": [
    {
      "name": "ArXiv AI",
      "url": "http://arxiv.org/rss/cs.AI",
      "category": "research"
    },
    {
      "name": "Your Custom Feed",
      "url": "https://example.com/feed",
      "category": "news"
    }
  ]
}
```

### AI Keywords

Edit `tools/news_curator.py` to customize the AI/ML keywords used for filtering:

```python
AI_KEYWORDS = [
    "artificial intelligence", "ai", "machine learning",
    # Add your custom keywords...
]
```

### Posting Time

Change the posting time in `scripts/setup_cron.sh`:

```bash
# Current: 0 6 * * * (6:00 AM)
# For 9:00 AM: 0 9 * * *
# For 5:30 PM: 30 17 * * *
```

Or set in `.env`:

```bash
POSTING_HOUR=9  # 9am
```

## Project Structure

```
ai_news_agent/
├── agent.py                    # Main agent definition
├── config/
│   ├── feeds.json             # RSS feed URLs
│   └── settings.py            # Configuration management
├── tools/
│   ├── rss_fetcher.py         # RSS feed fetching
│   ├── news_curator.py        # AI news filtering & ranking
│   ├── post_drafter.py        # Social media post creation
│   ├── approval_handler.py    # Human approval workflow
│   └── social_publisher.py    # LinkedIn/Twitter posting
├── data/
│   ├── posted_articles.db     # SQLite database
│   ├── sessions.db            # Session state
│   └── schema.sql             # Database schema
├── scripts/
│   ├── run_agent.py           # Manual execution
│   ├── handle_approval.py     # Approval CLI
│   └── setup_cron.sh          # Cron installation
├── logs/
│   └── cron.log               # Cron execution logs
├── .env                       # API credentials (gitignored)
├── .env.example               # Template
└── requirements.txt           # Python dependencies
```

## Workflow

### Daily Execution Flow

1. **6:00 AM**: Cron triggers `run_agent.py`
2. **Fetch**: Agent retrieves RSS feeds (parallel)
3. **Curate**: Filters for AI/ML relevance, ranks by importance
4. **Draft**: Creates LinkedIn and Twitter posts
5. **Pause**: Agent waits for human approval
6. **Email/Notification**: You receive notification (optional)
7. **Review**: You review drafts and approve/reject
8. **Publish**: If approved, posts go live on LinkedIn and Twitter
9. **Record**: Article saved to database to prevent duplicates

### Approval Workflow

```bash
# Morning notification (set up email/SMS alerts separately)
# Review the draft posts

# Approve good posts
python scripts/handle_approval.py --session news_run_20260104 --approve

# Or reject if not suitable
python scripts/handle_approval.py --session news_run_20260104 --reject
```

## Troubleshooting

### Agent Not Running

**Check cron job**:
```bash
crontab -l | grep ai_news_agent
```

**Check logs**:
```bash
tail -50 logs/cron.log
```

**Test manually**:
```bash
python scripts/run_agent.py
```

### LinkedIn Posting Fails

**Common issues**:
- Access token expired (tokens expire after ~60 days)
- Missing person URN (see `tools/social_publisher.py`)
- Insufficient permissions

**Solution**: Refresh OAuth token or check LinkedIn Developer Console.

### Twitter Posting Fails

**Common issues**:
- Rate limit exceeded (50 tweets/24h)
- Invalid credentials
- App permissions not set to "Read and Write"

**Solution**: Check Twitter Developer Portal, verify credentials.

### Database Errors

**Reset database**:
```bash
rm data/posted_articles.db data/sessions.db
sqlite3 data/posted_articles.db < data/schema.sql
```

### No News Found

**Possible causes**:
- RSS feeds are down
- No AI news in last 24 hours
- Articles already posted

**Check**:
```bash
# Test RSS fetching manually
python -c "from tools.rss_fetcher import fetch_rss_feed; print(fetch_rss_feed('http://arxiv.org/rss/cs.AI', 'ArXiv AI'))"
```

## Security Best Practices

1. **Never commit `.env` file** (already in `.gitignore`)
2. **Set file permissions**: `chmod 600 .env`
3. **Rotate API tokens regularly**
4. **Use dedicated social media accounts for testing**
5. **Monitor API usage to avoid unexpected charges**
6. **Enable 2FA on LinkedIn and Twitter accounts**

## Rate Limits

- **LinkedIn**: No official limit, but avoid >20 posts/day
- **Twitter**: 50 tweets per 24 hours (free tier)
- **Gemini API**: 15 requests per minute (Vertex AI)
- **RSS Feeds**: Generally no limits, but respect robots.txt

## Future Enhancements

- [ ] Email/SMS notifications for approval requests
- [ ] Analytics dashboard (track engagement, best posting times)
- [ ] Multi-platform support (Mastodon, Bluesky, Threads)
- [ ] A/B testing for post formats
- [ ] Automatic hashtag optimization
- [ ] Image generation from news articles
- [ ] Sentiment analysis for topic selection
- [ ] LinkedIn organization page support
- [ ] Twitter thread generation for complex topics
- [ ] Integration with Buffer/Hootsuite for scheduling

## Contributing

This is a personal project. Feel free to fork and customize for your needs.

## License

MIT License - Use freely, no warranties provided.

## Support

For issues with:
- **Google ADK**: https://github.com/google/adk-python
- **LinkedIn API**: https://www.linkedin.com/developers/
- **Twitter API**: https://developer.twitter.com/en/support

## Acknowledgments

Built with:
- Google Agent Development Kit (ADK)
- Gemini 2.5 Flash (via Vertex AI)
- Tweepy (Twitter API library)
- Feedparser (RSS parsing)

Based on patterns from the Google ADK Kaggle Course.
