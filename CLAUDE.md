# CLAUDE.md

This file provides comprehensive guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI News Agent is an automated pipeline that fetches AI news from RSS feeds, curates content, drafts social media posts, gets human approval, and publishes to LinkedIn and Twitter. Built using **Google Agent Development Kit (ADK)** with **Gemini 2.5 Flash**.

### Key Features
- **Parallel RSS Fetching**: Concurrent fetching from multiple sources (ArXiv, TechCrunch, VentureBeat)
- **Smart Curation**: AI-powered filtering and ranking by relevance, recency, and source credibility
- **Multi-Platform Drafting**: Platform-specific content for LinkedIn and Twitter
- **Human-in-Loop Approval**: Pauses execution for manual review before publishing
- **Duplicate Prevention**: SQLite database tracks posted articles
- **Retry Logic**: Handles API rate limits and failures with exponential backoff
- **Session Resumability**: Persists state for pause/resume workflow

---

## Architecture

### Agent Pipeline (agent.py)

```
RSSFetcherTeam (ParallelAgent)
├── ArXivFetcher (Agent)
├── TechCrunchFetcher (Agent)
└── VentureBeatFetcher (Agent)
    ↓
NewsCuratorAgent (Agent)
    ↓
PostDrafterAgent (Agent)
    ↓
ApprovalAgent (Agent) ← Human-in-loop: PAUSES HERE
    ↓
PublisherAgent (Agent)
```

### Stage Details

1. **RSSFetcherTeam** (ParallelAgent at agent.py:132)
   - Contains 3 sub-agents running concurrently
   - Each uses `output_key` to store results (e.g., `arxiv_results`)
   - Tool: `fetch_rss_feed()` from tools/rss_fetcher.py
   - Fetches articles from last 24 hours

2. **NewsCuratorAgent** (Agent at agent.py:141)
   - Consumes: `{arxiv_results}`, `{techcrunch_results}`, `{venturebeat_results}`
   - Tools: `filter_by_keywords()`, `rank_by_relevance()`, `check_already_posted()`
   - Filters for AI/ML keywords (50+ keywords in tools/news_curator.py:15-25)
   - Ranks by: keyword density (5pts/keyword), source credibility (5-10pts), recency (0-10pts)
   - Excludes articles already in posted_articles database
   - Outputs: `curated_news` (top 1 article)

3. **PostDrafterAgent** (Agent at agent.py:175)
   - Consumes: `{curated_news}`
   - Tools: `draft_linkedin_post()`, `draft_twitter_post()`
   - LinkedIn: Max 3000 chars, professional tone, hashtags
   - Twitter: Max 280 chars, supports threads if needed
   - Outputs: `post_drafts` (both LinkedIn and Twitter drafts)

4. **ApprovalAgent** (Agent at agent.py:215)
   - Consumes: `{post_drafts}`
   - Tool: `request_approval()` (uses `ToolContext.request_confirmation()`)
   - **PAUSES EXECUTION** until human approval/rejection
   - Displays formatted preview with both drafts
   - Outputs: `approval_result` (status: approved/rejected)

5. **PublisherAgent** (Agent at agent.py:248)
   - Consumes: `{approval_result}`
   - Tools: `post_to_linkedin()`, `post_to_twitter()`, `record_posted_article()`
   - Only publishes if status is "approved"
   - Records article in database with post URLs
   - Uses `@retry` decorator for API resilience

### Key ADK Patterns

- **Data Flow**: Agents pass data via `output_key` attributes and `{variable}` template substitution in instructions
- **Resumability**: `ResumabilityConfig(is_resumable=True)` enables pause/resume (agent.py:308)
- **Session Persistence**: `DatabaseSessionService` with SQLite stores session state (agent.py:320)
- **Retry Options**: `types.HttpRetryOptions` on Gemini model (agent.py:54) + `tenacity` decorators on tool functions
- **Parallel Execution**: `ParallelAgent` executes sub-agents concurrently
- **Sequential Execution**: `SequentialAgent` executes sub-agents in order

---

## Directory Structure

```
ai_news_agent/
├── agent.py                    # Main agent definition (340 lines)
├── config/
│   ├── __init__.py
│   ├── settings.py            # Config class with all environment variables
│   └── feeds.json             # RSS feed URLs and metadata
├── tools/                      # Tool functions (must return JSON strings)
│   ├── __init__.py
│   ├── rss_fetcher.py         # fetch_rss_feed()
│   ├── news_curator.py        # filter_by_keywords(), rank_by_relevance(), check_already_posted()
│   ├── post_drafter.py        # draft_linkedin_post(), draft_twitter_post()
│   ├── approval_handler.py    # request_approval() (uses ToolContext)
│   └── social_publisher.py    # post_to_linkedin(), post_to_twitter(), record_posted_article()
├── scripts/                    # Execution scripts
│   ├── run_agent.py           # Manual execution (creates session, runs pipeline)
│   ├── handle_approval.py     # CLI for approval/rejection (resumes session)
│   └── setup_cron.sh          # Installs daily cron job
├── data/                       # SQLite databases
│   ├── sessions.db            # ADK session state (managed by DatabaseSessionService)
│   ├── posted_articles.db     # Tracks posted articles (prevents duplicates)
│   └── schema.sql             # Database schema
├── logs/
│   └── cron.log               # Cron execution logs
├── .env                        # API credentials (gitignored)
├── .env.example                # Template for .env
├── .gitignore
├── requirements.txt            # Python dependencies
├── README.md                   # User documentation
└── CLAUDE.md                   # This file (AI assistant guidance)
```

---

## Tool Function Conventions

**CRITICAL CONVENTION**: All tool functions MUST return JSON strings, not Python dicts. ADK serializes tool results as JSON.

### Standard Return Format

```python
def tool_function(arg: str) -> str:
    """Tool description."""
    try:
        # ... logic ...
        return json.dumps({
            "status": "success",
            "data": result,
            # ... other fields ...
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e)
        })
```

### Tool Categories

1. **Data Fetching Tools** (tools/rss_fetcher.py)
   - `fetch_rss_feed(feed_url, feed_name, hours_back=24)` → JSON with articles list
   - Returns: `{status, feed_name, articles: [{title, link, published, summary, source}], count}`

2. **Curation Tools** (tools/news_curator.py)
   - `check_already_posted(article_url, db_path="")` → JSON with boolean
   - `filter_by_keywords(articles_json)` → JSON with filtered articles
   - `rank_by_relevance(articles_json, db_path="")` → JSON with ranked articles
   - All tools handle their own database connections (no shared connections)

3. **Drafting Tools** (tools/post_drafter.py)
   - `draft_linkedin_post(news_item_json)` → JSON with draft text
   - `draft_twitter_post(news_item_json)` → JSON with draft text and thread info

4. **Approval Tools** (tools/approval_handler.py)
   - `request_approval(tool_context, news_title, news_url, linkedin_draft, twitter_draft)` → JSON
   - Uses `ToolContext.request_confirmation()` for pause/resume pattern
   - First call: pauses execution, returns status: "pending"
   - Resume call: returns status: "approved" or "rejected"

5. **Publishing Tools** (tools/social_publisher.py)
   - `post_to_linkedin(post_text, credentials_json="")` → JSON with post_url
   - `post_to_twitter(tweet_text, credentials_json="", is_thread=False, thread_tweets=[])` → JSON
   - `record_posted_article(article_url, article_title, ...)` → JSON
   - All use `@retry` decorator for API resilience

### Database Access Pattern

- **Each tool creates its own database connection** (no shared connections)
- Tools use `Config.ARTICLES_DB` or `Config.SESSIONS_DB` for paths
- Tables are created if they don't exist (idempotent)
- Always use `conn.close()` in try/finally blocks
- SQLite is synchronous (not aiosqlite in tools)

---

## Configuration and Environment

### Environment Variables (.env)

```bash
# Google Cloud (required for Gemini API)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-west1
GOOGLE_GENAI_USE_VERTEXAI=1

# LinkedIn API (optional, required for publishing)
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token
LINKEDIN_ORGANIZATION_ID=your_org_id  # Optional for org pages

# Twitter API (optional, required for publishing)
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# Scheduling
POSTING_HOUR=6  # 6am default
TIMEZONE=America/Los_Angeles
```

### Config Class (config/settings.py)

Centralized configuration management:
- `Config.GOOGLE_CLOUD_PROJECT` - Google Cloud project ID
- `Config.SESSIONS_DB` - Path to sessions.db
- `Config.ARTICLES_DB` - Path to posted_articles.db
- `Config.load_rss_feeds()` - Loads feeds from config/feeds.json
- `Config.validate()` - Validates required credentials (called in agent.py:50)
- `Config.get_linkedin_credentials()` - Returns dict with LinkedIn creds
- `Config.get_twitter_credentials()` - Returns dict with Twitter creds

### RSS Feeds (config/feeds.json)

Add/remove feeds here. Each feed has:
- `name`: Display name (e.g., "ArXiv AI")
- `url`: RSS/Atom feed URL
- `category`: "research", "news", or "analysis"

Current feeds: ArXiv, TechCrunch, VentureBeat, MIT Tech Review, AI News

---

## Database Schema

### posted_articles table (data/schema.sql:4-16)

```sql
CREATE TABLE posted_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_url TEXT UNIQUE NOT NULL,  -- Prevents duplicates
    article_title TEXT NOT NULL,
    article_summary TEXT,
    posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    linkedin_post_url TEXT,            -- Published post URL
    twitter_post_url TEXT,             -- Published tweet URL
    linkedin_draft TEXT,               -- Draft content
    twitter_draft TEXT,                -- Draft content
    source_feed TEXT                   -- Feed name (e.g., "ArXiv AI")
);
```

Indexes: `posted_date`, `article_url`, `source_feed`

### pending_approvals table (data/schema.sql:24-34)

```sql
CREATE TABLE pending_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    article_url TEXT NOT NULL,
    article_title TEXT,
    linkedin_draft TEXT,
    twitter_draft TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',  -- pending, approved, rejected
    CHECK(status IN ('pending', 'approved', 'rejected'))
);
```

**Note**: This table is defined in schema.sql but not currently used by the code. Session state is managed by ADK's DatabaseSessionService.

---

## Commands and Usage

### Manual Execution

```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent (fetches news, drafts posts, waits for approval)
python scripts/run_agent.py

# This creates a session ID like: news_run_20260110
```

### Approve/Reject Posts

```bash
# Approve and publish
python scripts/handle_approval.py --session news_run_20260110 --approve

# Reject (do not publish)
python scripts/handle_approval.py --session news_run_20260110 --reject
```

### Testing Individual Tools

```bash
# Test RSS fetching
python -c "from tools.rss_fetcher import fetch_rss_feed; print(fetch_rss_feed('http://arxiv.org/rss/cs.AI', 'ArXiv AI'))"

# Test keyword filtering
python -c "from tools.news_curator import filter_by_keywords; import json; print(filter_by_keywords(json.dumps({'articles': [{'title': 'AI breakthrough', 'summary': 'New AI model'}]})))"

# Test database check
python -c "from tools.news_curator import check_already_posted; print(check_already_posted('https://example.com/article'))"
```

### Daily Automation (Cron)

```bash
# Install cron job (runs daily at 6am)
bash scripts/setup_cron.sh

# View cron log
tail -f logs/cron.log

# List cron jobs
crontab -l | grep ai_news_agent

# Remove cron job
crontab -e  # Delete the line containing 'ai_news_agent'
```

---

## Development Workflows

### Adding a New RSS Feed

1. **Edit config/feeds.json**:
   ```json
   {
     "name": "AI Weekly",
     "url": "https://aiweekly.com/feed",
     "category": "news"
   }
   ```

2. **Add a new fetcher agent in agent.py** (after line 129):
   ```python
   aiweekly_fetcher = Agent(
       name="AIWeeklyFetcher",
       model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
       description="Fetches AI news from AI Weekly.",
       instruction="""
       Task: Call fetch_rss_feed with:
       - feed_url: "https://aiweekly.com/feed"
       - feed_name: "AI Weekly"
       - hours_back: 24
       Return results directly.
       """,
       tools=[fetch_rss_feed],
       output_key="aiweekly_results"
   )
   ```

3. **Add to ParallelAgent** (agent.py:132):
   ```python
   rss_fetcher_team = ParallelAgent(
       name="RSSFetcherTeam",
       sub_agents=[arxiv_fetcher, techcrunch_fetcher, venturebeat_fetcher, aiweekly_fetcher]
   )
   ```

4. **Update NewsCuratorAgent instruction** (agent.py:150):
   ```python
   instruction="""
   Process:
   1. Combine all articles from: {arxiv_results}, {techcrunch_results}, {venturebeat_results}, {aiweekly_results}
   ...
   """
   ```

### Modifying Curation Logic

**Keywords** (tools/news_curator.py:15-25):
- Add/remove keywords in `AI_KEYWORDS` list
- Keywords are case-insensitive
- More matches = higher relevance score (5 points per keyword)

**Source Credibility** (tools/news_curator.py:203-215):
- Modify `source_scores` dict in `rank_by_relevance()`
- ArXiv/MIT Tech Review: 10 points
- TechCrunch/VentureBeat: 7 points
- Default: 5 points

**Recency Score** (tools/news_curator.py:242-250):
- 10 points for 0 hours old, 0 points for 24 hours old
- Linear decay: `10 - hours_old/2.4`

### Adding a New Tool Function

1. **Create tool in appropriate file** (e.g., tools/my_tool.py):
   ```python
   import json

   def my_tool_function(arg: str) -> str:
       """
       Tool description for LLM.

       Args:
           arg: Description

       Returns:
           JSON string with:
           {
               "status": "success" | "error",
               "result": ...
           }
       """
       try:
           # ... logic ...
           return json.dumps({
               "status": "success",
               "result": result
           })
       except Exception as e:
           return json.dumps({
               "status": "error",
               "error_message": str(e)
           })
   ```

2. **Import in agent.py**:
   ```python
   from tools.my_tool import my_tool_function
   ```

3. **Add to appropriate agent's tools list**:
   ```python
   my_agent = Agent(
       name="MyAgent",
       model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
       tools=[my_tool_function],
       # ...
   )
   ```

4. **Update agent instruction** to guide LLM on when/how to use the tool

### Debugging Agent Execution

1. **Check session database**:
   ```bash
   sqlite3 data/sessions.db
   .tables
   SELECT * FROM sessions;
   ```

2. **Check posted articles**:
   ```bash
   sqlite3 data/posted_articles.db
   SELECT article_title, posted_date, linkedin_post_url FROM posted_articles ORDER BY posted_date DESC LIMIT 10;
   ```

3. **Add debug prints** (agent.py uses print statements):
   ```python
   print(f"DEBUG: {variable_name}")
   ```

4. **Test individual agent stages**:
   - Comment out later stages in `SequentialAgent` (agent.py:290)
   - Run with `python scripts/run_agent.py`
   - Inspect intermediate outputs

---

## Error Handling Patterns

### Retry Logic

**Model-level retries** (agent.py:54-59):
```python
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)
```

**Tool-level retries** (tools/social_publisher.py:18-22):
```python
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError))
)
def post_to_linkedin(post_text: str, credentials_json: str = "") -> str:
    # ... implementation ...
```

### Exception Handling in Tools

All tools follow this pattern:
```python
try:
    # Main logic
    return json.dumps({"status": "success", ...})
except Exception as e:
    return json.dumps({
        "status": "error",
        "error_message": str(e)
    })
```

### Common Issues and Solutions

1. **LinkedIn/Twitter API Failures**:
   - Tools return `{"status": "error", "error_message": "..."}"`
   - Agent should handle gracefully (PublisherAgent checks approval status first)
   - Retry logic handles rate limits (429 status codes)

2. **RSS Feed Parsing Errors**:
   - `feedparser` handles malformed feeds gracefully (bozo mode)
   - Tool returns empty articles list with error message
   - Curator agent should handle empty feed results

3. **Database Lock Errors** (SQLite):
   - Each tool creates its own connection (no shared connections)
   - Use short transactions
   - Close connections promptly

4. **Session Not Found** (handle_approval.py):
   - Ensure correct session_id (format: `news_run_YYYYMMDD`)
   - Check `data/sessions.db` for existing sessions

---

## API Integration Details

### LinkedIn API (tools/social_publisher.py:23-126)

**Endpoint**: `https://api.linkedin.com/v2/ugcPosts`
**Authentication**: Bearer token (OAuth 2.0)
**Required Scopes**: `w_member_social`, `r_liteprofile`

**Current Limitation** (line 78):
```python
"author": "urn:li:person:YOUR_PERSON_ID",  # Replace with actual person ID
```

**To fix for production**:
1. Call `/v2/me` to get person URN
2. Store in Config or retrieve dynamically
3. Update payload with actual URN

**Rate Limits**: No official limit, but avoid >20 posts/day

### Twitter API (tools/social_publisher.py:133-242)

**Library**: Tweepy (Twitter API v2)
**Authentication**: OAuth 1.0a (consumer key/secret + access token/secret)
**Required Permissions**: "Read and Write"

**Thread Support**:
- If `is_thread=True` and `thread_tweets` provided, posts as thread
- Uses `in_reply_to_tweet_id` to chain tweets
- Returns `thread_ids` list in response

**Rate Limits**: 50 tweets per 24 hours (free tier)

### Gemini API (agent.py:44-47)

**Via Vertex AI**:
```python
vertexai.init(
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-west1")
)
```

**Model**: `gemini-2.5-flash` (fast, cost-effective)
**Rate Limits**: 15 requests per minute (Vertex AI)

---

## Session Management and Resumability

### How Resumability Works

1. **Initial Execution** (scripts/run_agent.py:30-109):
   - Creates unique session ID: `news_run_{YYYYMMDD}`
   - Calls `session_service.create_session()`
   - Runs agent with `runner.run_async()`
   - Agent pauses at `ApprovalAgent` when `request_approval()` is called

2. **Pause Point** (tools/approval_handler.py:40-86):
   - First call to `request_approval()`: `tool_context.tool_confirmation` is None
   - Calls `tool_context.request_confirmation(hint=preview, payload={...})`
   - Returns `{"status": "pending"}`
   - ADK saves session state to `data/sessions.db`

3. **Resume Execution** (scripts/handle_approval.py:25-83):
   - User runs `handle_approval.py --session <id> --approve`
   - Sends new message: "I approve the posts."
   - ADK loads session state from database
   - Continues from pause point

4. **Resume Point** (tools/approval_handler.py:88-108):
   - Second call to `request_approval()`: `tool_context.tool_confirmation` is populated
   - If `confirmed=True`: returns `{"status": "approved", ...}` with drafts
   - If `confirmed=False`: returns `{"status": "rejected", ...}`
   - Agent proceeds to `PublisherAgent`

### Session Database (data/sessions.db)

Managed by `DatabaseSessionService` (agent.py:320):
```python
session_db_url = f"sqlite:///{session_db_path}"
session_service = DatabaseSessionService(db_url=session_db_url)
```

**Do not manually modify this database** - it contains serialized ADK state.

---

## Testing and Debugging

### Unit Testing Individual Tools

```bash
# Create a test script
cat > test_tools.py <<EOF
from tools.rss_fetcher import fetch_rss_feed
import json

result = fetch_rss_feed('http://arxiv.org/rss/cs.AI', 'ArXiv AI', hours_back=24)
data = json.loads(result)
print(f"Status: {data['status']}")
print(f"Articles: {data['count']}")
EOF

python test_tools.py
```

### Debugging Agent Instructions

If agent doesn't call tools correctly:
1. Check agent instruction clarity (agent.py)
2. Ensure `{variable}` templates match previous agent's `output_key`
3. Add explicit step-by-step instructions
4. Provide examples in instruction if needed

### Viewing Agent Reasoning

ADK doesn't expose internal reasoning, but you can:
1. Add print statements in tool functions
2. Check returned JSON structures
3. Review session state in database (advanced)

### Common Debugging Commands

```bash
# Check if .env is loaded correctly
python -c "from config.settings import Config; print(Config.GOOGLE_CLOUD_PROJECT)"

# Validate configuration
python -c "from config.settings import Config; Config.validate()"

# Test agent initialization
python agent.py  # Should print initialization info

# Check database contents
sqlite3 data/posted_articles.db "SELECT COUNT(*) FROM posted_articles;"
```

---

## Best Practices for AI Assistants

### When Modifying Agent Instructions

1. **Be explicit**: LLMs need clear step-by-step instructions
2. **Use numbered lists**: "1. Do X, 2. Do Y, 3. Do Z"
3. **Specify tool arguments**: "Call tool_name with arg1=value1, arg2=value2"
4. **Handle errors**: "If status is 'error', report and continue"
5. **Define success criteria**: "Select the TOP 1 article from ranked_articles"

### When Adding New Tools

1. **Always return JSON strings** (not dicts)
2. **Include status field**: "success" or "error"
3. **Validate inputs**: Check types and required fields
4. **Handle exceptions**: Use try/except with error JSON
5. **Document return format**: Clear docstring with JSON structure
6. **Use Config for paths**: `Config.ARTICLES_DB`, not hardcoded paths
7. **Close database connections**: Use try/finally if needed

### When Debugging Issues

1. **Test tools in isolation** before testing full pipeline
2. **Check database state** after each run
3. **Verify environment variables** are loaded correctly
4. **Review cron logs** for scheduled runs
5. **Validate API credentials** separately before integration

### Security Considerations

1. **Never commit .env file** (already in .gitignore)
2. **Use environment variables** for all secrets
3. **Validate external inputs** (RSS feed data, API responses)
4. **Sanitize database inputs** (use parameterized queries)
5. **Check file permissions** on .env (chmod 600)

---

## Common Development Tasks

### Task: Change Posting Time

1. Edit `.env`:
   ```bash
   POSTING_HOUR=9  # 9am instead of 6am
   ```

2. Or edit cron schedule in `scripts/setup_cron.sh`:
   ```bash
   # Change from: 0 6 * * *
   # To: 0 9 * * *
   ```

3. Reinstall cron:
   ```bash
   bash scripts/setup_cron.sh
   ```

### Task: Add Email Notifications

1. Create notification tool in `tools/notifications.py`:
   ```python
   import smtplib
   import json

   def send_approval_email(session_id: str, preview: str) -> str:
       """Sends email with approval link."""
       # SMTP configuration from Config
       # Send email with preview
       # Return {"status": "success", "sent_to": email}
   ```

2. Import in agent.py and add to `ApprovalAgent.tools`

3. Update `ApprovalAgent.instruction` to call tool after `request_approval()`

### Task: Support Multiple Languages

1. Add language parameter to drafting tools:
   ```python
   def draft_linkedin_post(news_item_json: str, language: str = "en") -> str:
   ```

2. Update agent instructions to specify language:
   ```python
   instruction="""
   Call draft_linkedin_post with language="es" for Spanish posts.
   """
   ```

3. Add translation logic in drafting tools (use Google Translate API)

### Task: Add Analytics Dashboard

1. Extend `posted_articles` table with engagement metrics:
   ```sql
   ALTER TABLE posted_articles ADD COLUMN linkedin_likes INTEGER DEFAULT 0;
   ALTER TABLE posted_articles ADD COLUMN twitter_retweets INTEGER DEFAULT 0;
   ```

2. Create analytics tool to fetch post stats:
   ```python
   def fetch_post_analytics(post_url: str) -> str:
       """Fetches likes, shares, retweets from APIs."""
   ```

3. Create separate script to populate analytics:
   ```bash
   python scripts/fetch_analytics.py
   ```

4. Generate reports or visualizations from database

---

## Troubleshooting Guide

### Issue: "Configuration validation failed"

**Cause**: Missing required environment variables
**Solution**:
1. Check `.env` file exists: `ls -la .env`
2. Verify `GOOGLE_CLOUD_PROJECT` is set: `cat .env | grep GOOGLE_CLOUD_PROJECT`
3. Run validation: `python -c "from config.settings import Config; Config.validate()"`

### Issue: "Session not found"

**Cause**: Incorrect session_id or session expired
**Solution**:
1. Check session ID format: `news_run_YYYYMMDD` (e.g., `news_run_20260110`)
2. List sessions: `sqlite3 data/sessions.db "SELECT * FROM sessions;"`
3. Ensure you're using the correct session ID from `run_agent.py` output

### Issue: LinkedIn posting returns 401 Unauthorized

**Cause**: Access token expired or invalid
**Solution**:
1. LinkedIn tokens expire after ~60 days
2. Re-authenticate through LinkedIn OAuth flow
3. Update `LINKEDIN_ACCESS_TOKEN` in `.env`
4. For production, implement token refresh logic

### Issue: No articles found

**Cause**: All recent articles already posted or no AI news in last 24 hours
**Solution**:
1. Check database: `sqlite3 data/posted_articles.db "SELECT * FROM posted_articles WHERE posted_date > datetime('now', '-1 day');"`
2. Clear database for testing: `rm data/posted_articles.db`
3. Test RSS feeds manually: See "Commands and Usage" section

### Issue: Twitter thread not posting

**Cause**: Character limit exceeded or API error
**Solution**:
1. Check `twitter_draft` character count in output
2. Verify `is_thread` is set to `True` in tool call
3. Ensure `thread_tweets` is provided as list
4. Check Twitter API status: https://api.twitterstat.us/

---

## Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| agent.py | 340 | Main agent pipeline definition |
| config/settings.py | 94 | Configuration management |
| tools/rss_fetcher.py | 99 | RSS feed fetching |
| tools/news_curator.py | 277 | Filtering, ranking, duplicate checking |
| tools/post_drafter.py | 199 | LinkedIn and Twitter drafting |
| tools/approval_handler.py | 109 | Human-in-loop approval |
| tools/social_publisher.py | 329 | LinkedIn/Twitter posting, database recording |
| scripts/run_agent.py | 115 | Manual execution script |
| scripts/handle_approval.py | 125 | Approval CLI |
| data/schema.sql | 38 | Database schema |

---

## Additional Resources

- **Google ADK Documentation**: https://github.com/google/adk-python
- **Gemini API Docs**: https://ai.google.dev/docs
- **LinkedIn API**: https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin
- **Twitter API**: https://developer.twitter.com/en/docs/twitter-api
- **Feedparser**: https://feedparser.readthedocs.io/
- **Tenacity (Retry)**: https://tenacity.readthedocs.io/

---

## Summary for AI Assistants

When working with this codebase:

1. **Understand the pipeline**: 5 sequential stages with 1 parallel stage
2. **Follow tool conventions**: Always return JSON strings, include status field
3. **Respect data flow**: Use `output_key` and `{variable}` templates
4. **Test incrementally**: Test tools individually before full pipeline
5. **Check databases**: Sessions and posted articles are in SQLite
6. **Handle errors gracefully**: Use try/except and retry decorators
7. **Document changes**: Update this file when adding new features
8. **Validate configs**: Run `Config.validate()` after environment changes
9. **Use Config class**: Never hardcode paths or credentials
10. **Review agent instructions**: They guide LLM behavior - be explicit

This codebase follows ADK patterns from the Google Agent Development Kit. When in doubt, refer to ADK documentation or examples.
