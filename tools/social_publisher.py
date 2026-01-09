"""Social media publishing tools for LinkedIn and Twitter."""

import json
import sqlite3
from datetime import datetime
from typing import Dict
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import Config

# Import retry decorator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError))
)
def post_to_linkedin(post_text: str, credentials_json: str = "") -> str:
    """
    Posts content to LinkedIn using the LinkedIn API.

    Uses retry logic to handle rate limiting and temporary failures.

    API Documentation: https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin

    Args:
        post_text: The text content to post
        credentials_json: JSON string with credentials (optional, uses Config if not provided)

    Returns:
        JSON string with:
        {
            "status": "success" | "error",
            "post_url": str (LinkedIn post URL),
            "post_id": str,
            "message": str
        }
    """
    try:
        import requests

        # Get credentials
        if credentials_json:
            credentials = json.loads(credentials_json)
        else:
            credentials = Config.get_linkedin_credentials()

        access_token = credentials.get("access_token")
        if not access_token:
            return json.dumps({
                "status": "error",
                "error_message": "LinkedIn access token not configured",
                "post_url": "",
                "post_id": ""
            })

        # LinkedIn API endpoint for creating a post (UGC API)
        url = "https://api.linkedin.com/v2/ugcPosts"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        # Get person URN (requires a separate API call in production)
        # For now, this is a placeholder - in production, you'd need to:
        # 1. Call /v2/me to get the person URN
        # 2. Store it or retrieve it dynamically

        # Simplified payload (note: in production, you'd need proper person/organization URN)
        payload = {
            "author": "urn:li:person:YOUR_PERSON_ID",  # Replace with actual person ID
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post_text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        # Make API request
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 201:
            post_id = response.json().get("id", "")
            # LinkedIn post URL format
            post_url = f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else ""

            return json.dumps({
                "status": "success",
                "post_url": post_url,
                "post_id": post_id,
                "message": "Successfully posted to LinkedIn"
            })
        elif response.status_code == 429:
            # Rate limited
            raise Exception(f"LinkedIn rate limit exceeded: {response.text}")
        else:
            return json.dumps({
                "status": "error",
                "error_message": f"LinkedIn API error ({response.status_code}): {response.text}",
                "post_url": "",
                "post_id": ""
            })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": f"LinkedIn posting failed: {str(e)}",
            "post_url": "",
            "post_id": "",
            "note": "Check API credentials and permissions. Set up LinkedIn API at https://www.linkedin.com/developers/"
        })


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError))
)
def post_to_twitter(tweet_text: str, credentials_json: str = "", is_thread: bool = False, thread_tweets: list = []) -> str:
    """
    Posts content to Twitter/X using the Twitter API v2.

    Uses Tweepy library with retry logic for rate limiting.

    API Documentation: https://developer.twitter.com/en/docs/twitter-api

    Args:
        tweet_text: The tweet text (or first tweet if thread)
        credentials_json: JSON string with credentials (optional, uses Config if not provided)
        is_thread: Whether this is a thread (multiple tweets)
        thread_tweets: List of tweet texts for thread (if is_thread=True)

    Returns:
        JSON string with:
        {
            "status": "success" | "error",
            "post_url": str (Twitter post URL),
            "post_id": str,
            "thread_ids": [list] (if thread),
            "message": str
        }
    """
    try:
        import tweepy

        # Get credentials
        if credentials_json:
            credentials = json.loads(credentials_json)
        else:
            credentials = Config.get_twitter_credentials()

        # Validate credentials
        required_keys = ["api_key", "api_secret", "access_token", "access_token_secret"]
        for key in required_keys:
            if not credentials.get(key):
                return json.dumps({
                    "status": "error",
                    "error_message": f"Twitter credential missing: {key}",
                    "post_url": "",
                    "post_id": ""
                })

        # Create Tweepy client
        client = tweepy.Client(
            consumer_key=credentials["api_key"],
            consumer_secret=credentials["api_secret"],
            access_token=credentials["access_token"],
            access_token_secret=credentials["access_token_secret"],
            wait_on_rate_limit=True
        )

        # Post tweet(s)
        if is_thread and thread_tweets:
            # Post thread
            thread_ids = []
            previous_tweet_id = None

            for i, tweet in enumerate(thread_tweets):
                if previous_tweet_id:
                    # Reply to previous tweet
                    response = client.create_tweet(
                        text=tweet,
                        in_reply_to_tweet_id=previous_tweet_id
                    )
                else:
                    # First tweet in thread
                    response = client.create_tweet(text=tweet)

                tweet_id = response.data["id"]
                thread_ids.append(tweet_id)
                previous_tweet_id = tweet_id

            # URL to first tweet in thread
            post_url = f"https://twitter.com/user/status/{thread_ids[0]}"
            post_id = thread_ids[0]

            return json.dumps({
                "status": "success",
                "post_url": post_url,
                "post_id": post_id,
                "thread_ids": thread_ids,
                "message": f"Successfully posted thread with {len(thread_ids)} tweets"
            })
        else:
            # Single tweet
            response = client.create_tweet(text=tweet_text)
            tweet_id = response.data["id"]
            post_url = f"https://twitter.com/user/status/{tweet_id}"

            return json.dumps({
                "status": "success",
                "post_url": post_url,
                "post_id": tweet_id,
                "message": "Successfully posted to Twitter"
            })

    except tweepy.errors.TooManyRequests as e:
        # Rate limited
        raise Exception(f"Twitter rate limit exceeded: {str(e)}")
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": f"Twitter posting failed: {str(e)}",
            "post_url": "",
            "post_id": "",
            "note": "Check API credentials and permissions. Set up Twitter API at https://developer.twitter.com/"
        })


def record_posted_article(
    article_url: str,
    article_title: str,
    linkedin_post_url: str = "",
    twitter_post_url: str = "",
    linkedin_draft: str = "",
    twitter_draft: str = "",
    source_feed: str = "",
    db_path: str = ""
) -> str:
    """
    Records a posted article in the database to prevent duplicate posting.

    Args:
        article_url: URL of the source article
        article_title: Title of the article
        linkedin_post_url: URL of the LinkedIn post (if posted)
        twitter_post_url: URL of the Twitter post (if posted)
        linkedin_draft: The LinkedIn post text
        twitter_draft: The Twitter post text
        source_feed: Name of the RSS feed source
        db_path: Path to database (optional, uses Config if not provided)

    Returns:
        JSON string with:
        {
            "status": "success" | "error",
            "message": str,
            "article_url": str
        }
    """
    if not db_path:
        db_path = Config.ARTICLES_DB

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posted_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_url TEXT UNIQUE NOT NULL,
                article_title TEXT NOT NULL,
                posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                linkedin_post_url TEXT,
                twitter_post_url TEXT,
                linkedin_draft TEXT,
                twitter_draft TEXT,
                source_feed TEXT
            )
        """)

        # Insert article record
        cursor.execute("""
            INSERT OR REPLACE INTO posted_articles
            (article_url, article_title, linkedin_post_url, twitter_post_url,
             linkedin_draft, twitter_draft, source_feed, posted_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            article_url,
            article_title,
            linkedin_post_url,
            twitter_post_url,
            linkedin_draft,
            twitter_draft,
            source_feed,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        return json.dumps({
            "status": "success",
            "message": "Article recorded in database",
            "article_url": article_url
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": f"Database error: {str(e)}",
            "article_url": article_url
        })
