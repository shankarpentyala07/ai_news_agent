"""Post drafting tools for creating LinkedIn and Twitter content."""

import json
from typing import Dict


def draft_linkedin_post(news_item_json: str) -> str:
    """
    Creates a professional LinkedIn post from a news article.

    The agent should call this tool with the selected news article to create
    a LinkedIn-appropriate post.

    Format:
    - Hook line (interesting question or insight)
    - 2-3 paragraphs explaining the news and its significance
    - Key takeaway or call to action
    - Relevant hashtags (#AI #MachineLearning #Technology)
    - Source link

    Args:
        news_item_json: JSON string with article data (title, link, summary, source)

    Returns:
        JSON string with:
        {
            "status": "success" | "error",
            "linkedin_draft": str,
            "character_count": int,
            "hashtags": [list of hashtags used]
        }
    """
    try:
        # Parse input
        news_item = json.loads(news_item_json)
        if isinstance(news_item, dict) and "top_article" in news_item:
            article = news_item["top_article"]
        else:
            article = news_item

        title = article.get("title", "Exciting AI Development")
        link = article.get("link", "")
        summary = article.get("summary", "")
        source = article.get("source", "")

        # Extract key hashtags from content
        hashtags = []
        title_lower = title.lower()

        # Common AI hashtags based on content
        if any(word in title_lower for word in ["gpt", "llm", "language model"]):
            hashtags.extend(["#LargeLanguageModels", "#NLP"])
        if any(word in title_lower for word in ["vision", "image", "visual"]):
            hashtags.append("#ComputerVision")
        if any(word in title_lower for word in ["robot", "autonomous"]):
            hashtags.append("#Robotics")
        if any(word in title_lower for word in ["generative", "diffusion", "generation"]):
            hashtags.append("#GenerativeAI")

        # Always include core hashtags
        core_hashtags = ["#ArtificialIntelligence", "#MachineLearning", "#Technology"]
        hashtags = list(set(core_hashtags + hashtags))  # Remove duplicates

        # Limit to 5 hashtags
        hashtags = hashtags[:5]

        # Build LinkedIn post (note: this is a template - the agent will customize)
        draft = f"""🔬 {title}

{summary[:300]}{'...' if len(summary) > 300 else ''}

This development represents an important step forward in the AI field. As these technologies continue to evolve, they're opening new possibilities for innovation and practical applications.

What are your thoughts on this advancement?

{' '.join(hashtags)}

Read more: {link}
Source: {source}"""

        return json.dumps({
            "status": "success",
            "linkedin_draft": draft,
            "character_count": len(draft),
            "hashtags": hashtags,
            "note": "This is a template. The agent should customize the content based on the specific article."
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": f"LinkedIn draft error: {str(e)}",
            "linkedin_draft": ""
        })


def draft_twitter_post(news_item_json: str) -> str:
    """
    Creates a concise Twitter/X post from a news article.

    The agent should call this tool with the selected news article to create
    a Twitter-appropriate post.

    Format:
    - Concise headline or key insight
    - Brief explanation (if space allows)
    - 2-3 relevant hashtags
    - Link to full article
    - Must be under 280 characters

    Args:
        news_item_json: JSON string with article data (title, link, summary, source)

    Returns:
        JSON string with:
        {
            "status": "success" | "error",
            "twitter_draft": str,
            "character_count": int,
            "hashtags": [list of hashtags used],
            "is_thread": bool,
            "thread_tweets": [list] (if thread needed)
        }
    """
    try:
        # Parse input
        news_item = json.loads(news_item_json)
        if isinstance(news_item, dict) and "top_article" in news_item:
            article = news_item["top_article"]
        else:
            article = news_item

        title = article.get("title", "Exciting AI Development")
        link = article.get("link", "")
        summary = article.get("summary", "")

        # Determine hashtags (max 3 for Twitter to save space)
        hashtags = []
        title_lower = title.lower()

        if any(word in title_lower for word in ["gpt", "llm", "language"]):
            hashtags.append("#AI")
        elif any(word in title_lower for word in ["vision", "image"]):
            hashtags.append("#ComputerVision")
        elif any(word in title_lower for word in ["robot", "autonomous"]):
            hashtags.append("#Robotics")
        else:
            hashtags.append("#AI")

        # Add generic hashtags
        if "#AI" not in hashtags:
            hashtags.insert(0, "#AI")
        hashtags.append("#MachineLearning")

        # Limit to 3 hashtags
        hashtags = hashtags[:3]

        # Build Twitter post (must be <280 chars)
        hashtag_str = " ".join(hashtags)

        # Try to fit: title + hashtags + link
        # Typical t.co link is ~23 chars
        link_space = 25
        available_space = 280 - len(hashtag_str) - link_space - 3  # 3 for spaces

        # Truncate title if needed
        if len(title) > available_space:
            title = title[:available_space-3] + "..."

        draft = f"{title}\n\n{hashtag_str}\n{link}"

        # Check if we need a thread
        is_thread = len(draft) > 280
        thread_tweets = []

        if is_thread:
            # Create a thread: tweet 1 with title, tweet 2 with summary
            tweet1 = f"{title[:230]}... (1/2)\n\n{hashtag_str}"
            tweet2 = f"{summary[:230]}...\n\n{link} (2/2)"
            thread_tweets = [tweet1, tweet2]
            draft = tweet1  # Main tweet is the first one

        return json.dumps({
            "status": "success",
            "twitter_draft": draft,
            "character_count": len(draft),
            "hashtags": hashtags,
            "is_thread": is_thread,
            "thread_tweets": thread_tweets,
            "note": "This is a template. The agent should customize the content."
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": f"Twitter draft error: {str(e)}",
            "twitter_draft": ""
        })
