"""RSS feed fetching tools for AI News Agent."""

import feedparser
from datetime import datetime, timedelta
from typing import Dict, List
import json


def fetch_rss_feed(feed_url: str, feed_name: str, hours_back: int = 24) -> str:
    """
    Fetches and parses RSS feed entries from the specified time window.

    This tool fetches RSS/Atom feeds and filters entries published within
    the last N hours (default 24 hours).

    Args:
        feed_url: The URL of the RSS/Atom feed
        feed_name: Human-readable name of the feed (e.g., "ArXiv AI", "TechCrunch AI")
        hours_back: Number of hours to look back for articles (default: 24)

    Returns:
        JSON string with status and list of articles:
        {
            "status": "success" | "error",
            "feed_name": str,
            "articles": [
                {
                    "title": str,
                    "link": str,
                    "published": str (ISO format),
                    "summary": str,
                    "source": str
                }
            ],
            "count": int
        }
    """
    try:
        # Parse the feed
        feed = feedparser.parse(feed_url)

        # Check if feed was successfully parsed
        if feed.bozo and not feed.entries:
            return json.dumps({
                "status": "error",
                "feed_name": feed_name,
                "error_message": f"Failed to parse feed: {getattr(feed, 'bozo_exception', 'Unknown error')}",
                "articles": [],
                "count": 0
            })

        # Calculate cutoff time
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        # Filter and process entries
        articles = []
        for entry in feed.entries:
            # Parse published date
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    published_date = datetime(*entry.published_parsed[:6])
                except:
                    pass

            # If no published date or older than cutoff, skip
            if not published_date or published_date < cutoff_time:
                continue

            # Extract article data
            article = {
                "title": entry.get('title', 'No title'),
                "link": entry.get('link', ''),
                "published": published_date.isoformat(),
                "summary": entry.get('summary', entry.get('description', 'No summary available')),
                "source": feed_name
            }

            articles.append(article)

        # Sort by published date (newest first)
        articles.sort(key=lambda x: x['published'], reverse=True)

        return json.dumps({
            "status": "success",
            "feed_name": feed_name,
            "articles": articles,
            "count": len(articles)
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "feed_name": feed_name,
            "error_message": f"Exception while fetching feed: {str(e)}",
            "articles": [],
            "count": 0
        })
