#!/usr/bin/env python3
"""
Approval handling script for the AI News Agent.

Usage:
    python scripts/handle_approval.py --session news_run_20260104 --approve
    python scripts/handle_approval.py --session news_run_20260104 --reject

This script resumes the agent after human approval/rejection decision.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.adk.runners import Runner
from google.genai import types
from agent import app, session_service


async def resume_with_approval(session_id: str, approved: bool):
    """
    Resumes the agent after human approval decision.

    Args:
        session_id: The session ID to resume (e.g., "news_run_20260104")
        approved: True to approve and publish, False to reject
    """
    print("=" * 80)
    print("AI NEWS AGENT - APPROVAL HANDLER")
    print("=" * 80)
    print(f"Session: {session_id}")
    print(f"Decision: {'APPROVED ✅' if approved else 'REJECTED ❌'}")
    print("=" * 80)
    print()

    # Create runner
    runner = Runner(
        app=app,
        session_service=session_service
    )

    # Create resume message
    decision = "approve" if approved else "reject"
    resume_message = types.Content(
        role="user",
        parts=[types.Part(text=f"I {decision} the posts.")]
    )

    print(f"📤 Resuming agent with decision: {decision}")
    print("-" * 80)

    try:
        # Resume the agent session
        async for event in runner.run_async(
            user_id="system",
            session_id=session_id,
            new_message=resume_message
        ):
            # Print agent responses
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        print(f"\n{part.text}")
                        print("-" * 80)

        print()
        if approved:
            print("✅ Posts have been published to LinkedIn and Twitter!")
            print("   Check the output above for post URLs.")
        else:
            print("❌ Posts were rejected and NOT published.")
        print()

    except Exception as e:
        print(f"\n❌ Error during resume: {e}")
        print(f"   Make sure the session_id is correct")
        sys.exit(1)


def main():
    """Parse arguments and run approval handler."""
    parser = argparse.ArgumentParser(
        description="Handle approval for AI News Agent posts"
    )
    parser.add_argument(
        "--session",
        required=True,
        help="Session ID to resume (e.g., news_run_20260104)"
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Approve the posts and publish"
    )
    parser.add_argument(
        "--reject",
        action="store_true",
        help="Reject the posts and do not publish"
    )

    args = parser.parse_args()

    # Validate that exactly one action is specified
    if not (args.approve or args.reject):
        print("Error: Must specify either --approve or --reject")
        parser.print_help()
        sys.exit(1)

    if args.approve and args.reject:
        print("Error: Cannot specify both --approve and --reject")
        parser.print_help()
        sys.exit(1)

    # Run approval handler
    asyncio.run(resume_with_approval(args.session, args.approve))


if __name__ == "__main__":
    main()
