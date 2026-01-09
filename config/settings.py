"""Configuration management for AI News Agent."""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List

# Load environment variables
load_dotenv()

class Config:
    """Central configuration for the AI News Agent."""

    # Project paths
    BASE_DIR = Path(__file__).parent.parent
    CONFIG_DIR = BASE_DIR / "config"
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"

    # Google Cloud (for Gemini API)
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
    GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-west1")
    GOOGLE_GENAI_USE_VERTEXAI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "1")

    # LinkedIn API
    LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
    LINKEDIN_ORGANIZATION_ID = os.getenv("LINKEDIN_ORGANIZATION_ID", "")  # Optional for org pages

    # Twitter API (X API v2)
    TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
    TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

    # Database paths
    SESSIONS_DB = str(DATA_DIR / "sessions.db")
    ARTICLES_DB = str(DATA_DIR / "posted_articles.db")

    # Scheduling
    POSTING_HOUR = int(os.getenv("POSTING_HOUR", "6"))  # 6am default
    TIMEZONE = os.getenv("TIMEZONE", "America/Los_Angeles")

    @staticmethod
    def load_rss_feeds() -> List[Dict]:
        """Load RSS feed URLs from feeds.json."""
        feeds_path = Config.CONFIG_DIR / "feeds.json"
        with open(feeds_path, "r") as f:
            data = json.load(f)
            return data.get("feeds", [])

    @staticmethod
    def validate() -> bool:
        """Validate that required configuration is present."""
        errors = []

        if not Config.GOOGLE_CLOUD_PROJECT:
            errors.append("GOOGLE_CLOUD_PROJECT not set")

        # LinkedIn validation (optional for now, will fail at runtime if posting)
        if not Config.LINKEDIN_ACCESS_TOKEN:
            print("Warning: LINKEDIN_ACCESS_TOKEN not set. LinkedIn posting will fail.")

        # Twitter validation (optional for now)
        if not Config.TWITTER_API_KEY or not Config.TWITTER_API_SECRET:
            print("Warning: Twitter API credentials not set. Twitter posting will fail.")

        if errors:
            for error in errors:
                print(f"Configuration Error: {error}")
            return False

        return True

    @staticmethod
    def get_linkedin_credentials() -> Dict:
        """Get LinkedIn API credentials."""
        return {
            "access_token": Config.LINKEDIN_ACCESS_TOKEN,
            "organization_id": Config.LINKEDIN_ORGANIZATION_ID
        }

    @staticmethod
    def get_twitter_credentials() -> Dict:
        """Get Twitter API credentials."""
        return {
            "api_key": Config.TWITTER_API_KEY,
            "api_secret": Config.TWITTER_API_SECRET,
            "access_token": Config.TWITTER_ACCESS_TOKEN,
            "access_token_secret": Config.TWITTER_ACCESS_TOKEN_SECRET,
            "bearer_token": Config.TWITTER_BEARER_TOKEN
        }
