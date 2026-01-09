"""Human approval workflow for social media posts."""

import json
from google.adk.tools.tool_context import ToolContext


def request_approval(
    tool_context: ToolContext,
    news_title: str,
    news_url: str,
    linkedin_draft: str,
    twitter_draft: str
) -> str:
    """
    Requests human approval before posting to social media.

    This tool implements the human-in-loop pattern. On first call, it pauses
    execution and requests confirmation. On resume (after human decision), it
    returns the approval status.

    Pattern based on: /kaggle-course/day2/humaninloop/agent.py

    Args:
        tool_context: ToolContext for pause/resume functionality
        news_title: Title of the AI news article
        news_url: URL to the source article
        linkedin_draft: Drafted LinkedIn post
        twitter_draft: Drafted Twitter post

    Returns:
        JSON string with:
        {
            "status": "pending" | "approved" | "rejected",
            "news_title": str,
            "linkedin_draft": str,
            "twitter_draft": str,
            "news_url": str
        }
    """
    # First call - pause for approval
    if not tool_context.tool_confirmation:
        # Create preview for human review
        preview = f"""
╔═══════════════════════════════════════════════════════════════════════╗
║                    AI NEWS POST FOR APPROVAL                          ║
╚═══════════════════════════════════════════════════════════════════════╝

📰 NEWS ARTICLE
  Title: {news_title}
  URL: {news_url}

┌───────────────────────────────────────────────────────────────────────┐
│ LINKEDIN POST                                                         │
└───────────────────────────────────────────────────────────────────────┘
{linkedin_draft}

┌───────────────────────────────────────────────────────────────────────┐
│ TWITTER POST                                                          │
└───────────────────────────────────────────────────────────────────────┘
{twitter_draft}

═══════════════════════════════════════════════════════════════════════

To approve:  python scripts/handle_approval.py --session <session_id> --approve
To reject:   python scripts/handle_approval.py --session <session_id> --reject

═══════════════════════════════════════════════════════════════════════
"""

        # Request confirmation with payload
        tool_context.request_confirmation(
            hint=preview,
            payload={
                "news_title": news_title,
                "news_url": news_url,
                "linkedin_draft": linkedin_draft,
                "twitter_draft": twitter_draft
            }
        )

        return json.dumps({
            "status": "pending",
            "message": "Awaiting human approval",
            "news_title": news_title,
            "news_url": news_url
        })

    # Resume after human decision - handle approval/rejection
    if tool_context.tool_confirmation.confirmed:
        # Approved - return drafts for publishing
        payload = tool_context.tool_confirmation.payload

        return json.dumps({
            "status": "approved",
            "message": "Posts approved for publishing",
            "news_title": payload.get("news_title", news_title),
            "news_url": payload.get("news_url", news_url),
            "linkedin_draft": payload.get("linkedin_draft", linkedin_draft),
            "twitter_draft": payload.get("twitter_draft", twitter_draft)
        })
    else:
        # Rejected - do not publish
        return json.dumps({
            "status": "rejected",
            "message": "Posts rejected by user",
            "news_title": news_title,
            "news_url": news_url
        })
