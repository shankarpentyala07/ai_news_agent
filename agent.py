"""
AI News Posting Agent - Main Agent Definition

This agent automatically fetches AI news from RSS feeds, curates content,
drafts social media posts, gets human approval, and publishes to LinkedIn and Twitter.

Architecture:
    RSSFetcherTeam (ParallelAgent)
      ↓
    NewsCuratorAgent
      ↓
    PostDrafterAgent
      ↓
    ApprovalAgent (Human-in-Loop)
      ↓
    PublisherAgent
"""

import os
import vertexai
from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.models.google_llm import Gemini
from google.adk.apps import App, ResumabilityConfig
from google.adk.sessions import DatabaseSessionService
from google.genai import types

# Import tools
from tools.rss_fetcher import fetch_rss_feed
from tools.news_curator import (
    check_already_posted,
    filter_by_keywords,
    rank_by_relevance
)
from tools.post_drafter import draft_linkedin_post, draft_twitter_post
from tools.approval_handler import request_approval
from tools.social_publisher import (
    post_to_linkedin,
    post_to_twitter,
    record_posted_article
)
from config.settings import Config

# Initialize Vertex AI
vertexai.init(
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-west1")
)

# Validate configuration
if not Config.validate():
    print("Warning: Configuration validation failed. Some features may not work.")

# Retry configuration for API resilience
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

# ============================================================================
# 1. RSS FETCHER AGENTS (Parallel)
# ============================================================================

# Fetch from ArXiv AI research papers
arxiv_fetcher = Agent(
    name="ArXivFetcher",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    description="Fetches latest AI research papers from ArXiv RSS feed.",
    instruction="""
    You are an RSS feed fetcher for ArXiv AI research papers.

    Task:
    1. Call the fetch_rss_feed tool with:
       - feed_url: "http://arxiv.org/rss/cs.AI"
       - feed_name: "ArXiv AI"
       - hours_back: 24

    2. Return the results directly.

    Be concise and just fetch the feed.
    """,
    tools=[fetch_rss_feed],
    output_key="arxiv_results"
)

# Fetch from TechCrunch AI news
techcrunch_fetcher = Agent(
    name="TechCrunchFetcher",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    description="Fetches latest AI news from TechCrunch RSS feed.",
    instruction="""
    You are an RSS feed fetcher for TechCrunch AI news.

    Task:
    1. Call the fetch_rss_feed tool with:
       - feed_url: "https://techcrunch.com/tag/artificial-intelligence/feed/"
       - feed_name: "TechCrunch AI"
       - hours_back: 24

    2. Return the results directly.

    Be concise and just fetch the feed.
    """,
    tools=[fetch_rss_feed],
    output_key="techcrunch_results"
)

# Fetch from VentureBeat AI
venturebeat_fetcher = Agent(
    name="VentureBeatFetcher",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    description="Fetches latest AI news from VentureBeat RSS feed.",
    instruction="""
    You are an RSS feed fetcher for VentureBeat AI news.

    Task:
    1. Call the fetch_rss_feed tool with:
       - feed_url: "https://venturebeat.com/category/ai/feed/"
       - feed_name: "VentureBeat AI"
       - hours_back: 24

    2. Return the results directly.

    Be concise and just fetch the feed.
    """,
    tools=[fetch_rss_feed],
    output_key="venturebeat_results"
)

# Parallel team for concurrent RSS fetching
rss_fetcher_team = ParallelAgent(
    name="RSSFetcherTeam",
    sub_agents=[arxiv_fetcher, techcrunch_fetcher, venturebeat_fetcher]
)

# ============================================================================
# 2. NEWS CURATOR AGENT
# ============================================================================

news_curator = Agent(
    name="NewsCuratorAgent",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    description="Filters and ranks AI news articles, selects the top story.",
    instruction="""
    You are an AI news curator. You receive RSS feed results from multiple sources
    and select the BEST single story for today's social media post.

    Process:
    1. Combine all articles from: {arxiv_results}, {techcrunch_results}, {venturebeat_results}

    2. Filter for AI/ML relevance:
       - Call filter_by_keywords with the combined articles
       - This removes non-AI content

    3. Rank by importance:
       - Call rank_by_relevance with the filtered articles
       - This scores articles by relevance, recency, and source credibility
       - Automatically excludes already-posted articles

    4. Select the TOP 1 article from ranked_articles

    5. Return the selected article with clear explanation of why it was chosen

    Be analytical and choose the most impactful story.
    """,
    tools=[check_already_posted, filter_by_keywords, rank_by_relevance],
    output_key="curated_news"
)

# ============================================================================
# 3. POST DRAFTER AGENT
# ============================================================================

post_drafter = Agent(
    name="PostDrafterAgent",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    description="Creates engaging LinkedIn and Twitter posts from AI news.",
    instruction="""
    You are a social media content creator specializing in AI/tech news.

    Task: Create posts from the curated news: {curated_news}

    Requirements:
    1. LINKEDIN POST:
       - Call draft_linkedin_post with the top article
       - Customize the template to make it engaging:
         * Start with a hook question or interesting insight
         * Explain WHY this news matters (2-3 paragraphs)
         * Include practical implications
         * End with a thought-provoking question
         * Use relevant hashtags (#AI, #MachineLearning, etc.)
       - Professional, informative tone
       - Max 3000 characters

    2. TWITTER POST:
       - Call draft_twitter_post with the top article
       - Customize the template to be concise and punchy
       - Must be under 280 characters
       - Include link and 2-3 hashtags
       - If thread is needed, make it engaging

    3. Return BOTH drafts with their metadata

    Be creative and make the posts engaging while staying factual.
    """,
    tools=[draft_linkedin_post, draft_twitter_post],
    output_key="post_drafts"
)

# ============================================================================
# 4. APPROVAL AGENT (Human-in-Loop)
# ============================================================================

approval_agent = Agent(
    name="ApprovalAgent",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    description="Presents posts for human approval before publishing.",
    instruction="""
    You are the approval coordinator. You MUST get human confirmation before posts go live.

    Task:
    1. Extract the news article info and post drafts from: {post_drafts}

    2. Call request_approval with:
       - news_title: The article title
       - news_url: The article link
       - linkedin_draft: The LinkedIn post text
       - twitter_draft: The Twitter post text (or first tweet if thread)

    3. WAIT for human response:
       - If status is "pending": Execution will pause here
       - If status is "approved": Proceed to publishing
       - If status is "rejected": Stop and report rejection

    4. Return the approval result

    CRITICAL: Always call request_approval. Never skip this step.
    """,
    tools=[request_approval],
    output_key="approval_result"
)

# ============================================================================
# 5. PUBLISHER AGENT
# ============================================================================

publisher_agent = Agent(
    name="PublisherAgent",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    description="Posts to LinkedIn and Twitter, records in database.",
    instruction="""
    You are the publishing agent. You post approved content to social media.

    Check approval status from: {approval_result}

    IF APPROVED:
    1. POST TO LINKEDIN:
       - Call post_to_linkedin with the linkedin_draft text
       - Save the returned post_url

    2. POST TO TWITTER:
       - Call post_to_twitter with the twitter_draft text
       - If it's a thread (check is_thread and thread_tweets), include those
       - Save the returned post_url

    3. RECORD IN DATABASE:
       - Call record_posted_article with:
         * article_url
         * article_title
         * linkedin_post_url
         * twitter_post_url
         * drafts and source info

    4. Return success summary with both post URLs

    IF REJECTED:
    - Report that posting was cancelled
    - Do NOT call any publishing tools

    Be thorough and report all results.
    """,
    tools=[post_to_linkedin, post_to_twitter, record_posted_article]
)

# ============================================================================
# MAIN PIPELINE (Sequential)
# ============================================================================

ai_news_pipeline = SequentialAgent(
    name="AINewsPipeline",
    sub_agents=[
        rss_fetcher_team,    # Fetch feeds in parallel
        news_curator,         # Filter and rank
        post_drafter,         # Create social media posts
        approval_agent,       # Get human approval (pauses here)
        publisher_agent       # Post to social media
    ]
)

# ============================================================================
# APP WITH RESUMABILITY (for Human-in-Loop)
# ============================================================================

app = App(
    name="ai_news_agent",
    root_agent=ai_news_pipeline,
    resumability_config=ResumabilityConfig(is_resumable=True)  # Enables pause/resume
)

# ============================================================================
# SESSION SERVICE (for State Persistence)
# ============================================================================

# Create session database URL (use sync sqlite instead of aiosqlite)
session_db_path = os.path.abspath(Config.SESSIONS_DB)
session_db_url = f"sqlite:///{session_db_path}"

# Initialize session service
session_service = DatabaseSessionService(db_url=session_db_url)

# ============================================================================
# EXPORTS
# ============================================================================

# Export for scripts to use
root_agent = ai_news_pipeline

if __name__ == "__main__":
    print("AI News Agent Initialized")
    print(f"Configuration: {Config.GOOGLE_CLOUD_PROJECT} @ {Config.GOOGLE_CLOUD_LOCATION}")
    print(f"Session DB: {session_db_path}")
    print(f"Articles DB: {Config.ARTICLES_DB}")
    print("\nAgent Pipeline:")
    print("  1. RSS Fetcher Team (Parallel)")
    print("  2. News Curator")
    print("  3. Post Drafter")
    print("  4. Approval Agent (Human-in-Loop)")
    print("  5. Publisher Agent")
    print("\nTo run: python scripts/run_agent.py")
