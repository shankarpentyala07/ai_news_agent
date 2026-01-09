"""News curation tools for filtering and ranking AI news."""

import sqlite3
import json
from typing import Dict, List
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import Config


# AI/ML keywords for relevance filtering
AI_KEYWORDS = [
    "artificial intelligence", "ai", "machine learning", "ml", "deep learning",
    "neural network", "llm", "large language model", "generative ai", "genai",
    "chatgpt", "gpt", "claude", "gemini", "openai", "anthropic", "google ai",
    "natural language processing", "nlp", "computer vision", "cv",
    "reinforcement learning", "transformer", "attention mechanism",
    "diffusion model", "stable diffusion", "midjourney", "dalle",
    "autonomous", "robotics", "ml ops", "model training", "fine-tuning",
    "prompt engineering", "rag", "retrieval augmented generation",
    "agent", "ai agent", "multimodal", "embedding", "vector database"
]


def check_already_posted(article_url: str, db_path: str = "") -> str:
    """
    Checks if an article URL has already been posted.

    Queries the posted_articles database to prevent duplicate posts.

    Args:
        article_url: The URL of the article to check
        db_path: Path to the database file (optional, uses Config.ARTICLES_DB if not provided)

    Returns:
        JSON string with:
        {
            "status": "success" | "error",
            "already_posted": bool,
            "posted_date": str | null,
            "article_url": str
        }
    """
    if not db_path:
        db_path = Config.ARTICLES_DB

    try:
        # Create database and table if they don't exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create table if it doesn't exist (using schema.sql logic)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posted_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_url TEXT UNIQUE NOT NULL,
                article_title TEXT NOT NULL,
                posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                linkedin_post_url TEXT,
                twitter_post_url TEXT,
                source_feed TEXT
            )
        """)

        # Check if URL exists
        cursor.execute(
            "SELECT posted_date FROM posted_articles WHERE article_url = ?",
            (article_url,)
        )
        result = cursor.fetchone()

        conn.close()

        if result:
            return json.dumps({
                "status": "success",
                "already_posted": True,
                "posted_date": result[0],
                "article_url": article_url
            })
        else:
            return json.dumps({
                "status": "success",
                "already_posted": False,
                "posted_date": None,
                "article_url": article_url
            })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": f"Database error: {str(e)}",
            "already_posted": False,
            "article_url": article_url
        })


def filter_by_keywords(articles_json: str) -> str:
    """
    Filters articles for AI/ML relevance based on keywords.

    Checks article title and summary for AI/ML related keywords.

    Args:
        articles_json: JSON string containing list of articles

    Returns:
        JSON string with filtered articles:
        {
            "status": "success" | "error",
            "filtered_articles": [article list],
            "original_count": int,
            "filtered_count": int,
            "keywords_matched": {article_url: [keywords]}
        }
    """
    try:
        # Parse input
        articles_data = json.loads(articles_json)
        if isinstance(articles_data, dict) and "articles" in articles_data:
            articles = articles_data["articles"]
        else:
            articles = articles_data

        original_count = len(articles)
        filtered_articles = []
        keywords_matched = {}

        for article in articles:
            title = article.get("title", "").lower()
            summary = article.get("summary", "").lower()
            combined_text = f"{title} {summary}"

            # Check for keyword matches
            matched_keywords = [
                keyword for keyword in AI_KEYWORDS
                if keyword in combined_text
            ]

            # If at least one keyword matches, include the article
            if matched_keywords:
                article["relevance_score"] = len(matched_keywords)
                filtered_articles.append(article)
                keywords_matched[article.get("link", "")] = matched_keywords

        return json.dumps({
            "status": "success",
            "filtered_articles": filtered_articles,
            "original_count": original_count,
            "filtered_count": len(filtered_articles),
            "keywords_matched": keywords_matched
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": f"Filtering error: {str(e)}",
            "filtered_articles": [],
            "original_count": 0,
            "filtered_count": 0
        })


def rank_by_relevance(articles_json: str, db_path: str = "") -> str:
    """
    Ranks articles by relevance, recency, and source credibility.

    Scoring criteria:
    - Keyword density (more AI/ML keywords = higher score)
    - Recency (newer = higher score)
    - Source credibility (ArXiv, MIT Tech Review ranked higher)
    - Not already posted (filters out duplicates)

    Args:
        articles_json: JSON string containing list of articles
        db_path: Path to database for duplicate checking (optional)

    Returns:
        JSON string with ranked articles:
        {
            "status": "success" | "error",
            "ranked_articles": [sorted by score, highest first],
            "scores": {article_url: score},
            "top_article": article_dict | null
        }
    """
    if not db_path:
        db_path = Config.ARTICLES_DB

    try:
        # Parse input
        articles_data = json.loads(articles_json)
        if isinstance(articles_data, dict) and "filtered_articles" in articles_data:
            articles = articles_data["filtered_articles"]
        elif isinstance(articles_data, dict) and "articles" in articles_data:
            articles = articles_data["articles"]
        else:
            articles = articles_data

        # Source credibility scores
        source_scores = {
            "arxiv": 10,
            "mit tech": 9,
            "mit technology review": 9,
            "nature": 9,
            "science": 9,
            "techcrunch": 7,
            "venturebeat": 7,
            "wired": 7,
            "ai news": 6,
            "default": 5
        }

        ranked_articles = []
        scores = {}

        for article in articles:
            # Check if already posted
            check_result = json.loads(check_already_posted(article.get("link", ""), db_path))
            if check_result.get("already_posted"):
                continue  # Skip already posted articles

            score = 0

            # 1. Keyword relevance (from previous filtering)
            relevance_score = article.get("relevance_score", 1)
            score += relevance_score * 5  # 5 points per matched keyword

            # 2. Source credibility
            source = article.get("source", "").lower()
            source_score = source_scores.get("default")
            for key, value in source_scores.items():
                if key in source:
                    source_score = value
                    break
            score += source_score

            # 3. Recency (articles already filtered to last 24h, so minimal impact)
            # This is a tie-breaker score
            from datetime import datetime
            try:
                published = datetime.fromisoformat(article.get("published", ""))
                hours_old = (datetime.now() - published).total_seconds() / 3600
                recency_score = max(0, 10 - hours_old/2.4)  # 10 points for 0h old, 0 points for 24h old
                score += recency_score
            except:
                pass

            article["final_score"] = round(score, 2)
            ranked_articles.append(article)
            scores[article.get("link", "")] = round(score, 2)

        # Sort by score (highest first)
        ranked_articles.sort(key=lambda x: x["final_score"], reverse=True)

        top_article = ranked_articles[0] if ranked_articles else None

        return json.dumps({
            "status": "success",
            "ranked_articles": ranked_articles,
            "scores": scores,
            "top_article": top_article,
            "count": len(ranked_articles)
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": f"Ranking error: {str(e)}",
            "ranked_articles": [],
            "scores": {},
            "top_article": None
        })
