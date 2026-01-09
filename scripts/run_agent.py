#!/usr/bin/env python3
"""
Manual execution script for the AI News Agent.

Usage:
    python scripts/run_agent.py

This script:
1. Creates a unique session for today's run
2. Triggers the AI News Agent pipeline
3. Fetches RSS feeds, curates news, drafts posts
4. Pauses for human approval
5. (After approval) Posts to LinkedIn and Twitter
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.adk.runners import Runner
from google.genai import types
from agent import app, session_service
from config.settings import Config


async def run_daily_news_agent():
    """
    Executes the AI news agent pipeline.

    This function can be called manually or via cron for daily execution.
    """
    print("=" * 80)
    print("AI NEWS AGENT - DAILY EXECUTION")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Project: {Config.GOOGLE_CLOUD_PROJECT}")
    print(f"Session DB: {Config.SESSIONS_DB}")
    print(f"Articles DB: {Config.ARTICLES_DB}")
    print("=" * 80)
    print()

    # Create runner
    runner = Runner(
        app=app,
        session_service=session_service
    )

    # Create unique session ID for today
    session_id = f"news_run_{datetime.now().strftime('%Y%m%d')}"
    user_id = "system"
    app_name = "ai_news_agent"

    print(f"📝 Creating session: {session_id}")

    # Create session first
    try:
        await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        print(f"✅ Session created successfully")
    except Exception as e:
        print(f"Note: {e} (may already exist)")

    print()

    # Initial trigger message
    trigger_message = types.Content(
        role="user",
        parts=[types.Part(text="Fetch today's AI news and prepare social media posts for approval.")]
    )

    # Run agent
    print("🤖 Starting AI News Agent Pipeline...")
    print("-" * 80)

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=trigger_message
        ):
            # Print agent responses
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        print(f"\n{part.text}")
                        print("-" * 80)

        print()
        print("✅ AI News Agent execution completed!")
        print()
        print("📋 Next Steps:")
        print(f"   1. Review the drafted posts above")
        print(f"   2. To APPROVE and publish:")
        print(f"      python scripts/handle_approval.py --session {session_id} --approve")
        print(f"   3. To REJECT:")
        print(f"      python scripts/handle_approval.py --session {session_id} --reject")
        print()

    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        print(f"   Check logs and configuration")
        sys.exit(1)


if __name__ == "__main__":
    print()
    asyncio.run(run_daily_news_agent())
