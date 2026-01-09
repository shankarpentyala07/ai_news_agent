-- Database schema for AI News Agent

-- Table to track posted articles and prevent duplicates
CREATE TABLE IF NOT EXISTS posted_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_url TEXT UNIQUE NOT NULL,
    article_title TEXT NOT NULL,
    article_summary TEXT,
    posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    linkedin_post_url TEXT,
    twitter_post_url TEXT,
    linkedin_draft TEXT,
    twitter_draft TEXT,
    source_feed TEXT,
    UNIQUE(article_url)
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_posted_date ON posted_articles(posted_date);
CREATE INDEX IF NOT EXISTS idx_article_url ON posted_articles(article_url);
CREATE INDEX IF NOT EXISTS idx_source_feed ON posted_articles(source_feed);

-- Table to track pending approvals
CREATE TABLE IF NOT EXISTS pending_approvals (
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

CREATE INDEX IF NOT EXISTS idx_session_id ON pending_approvals(session_id);
CREATE INDEX IF NOT EXISTS idx_approval_status ON pending_approvals(status);
