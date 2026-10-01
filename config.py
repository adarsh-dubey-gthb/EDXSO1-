"""
Configuration Module for Micro-Influencer Outreach System.
Defines filtering thresholds, target niches, file paths, and environment settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if available
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

# ==============================================================================
# NICHE & AUDIENCE CRITERIA
# ==============================================================================
DEFAULT_NICHE = "Technology"

TECH_KEYWORDS = [
    "python", "javascript", "react", "nextjs", "webdev", "devops", "cloud",
    "aws", "docker", "kubernetes", "machine learning", "artificial intelligence",
    "ai", "data science", "cybersecurity", "software engineer", "coding",
    "open source", "developer tools", "rust", "golang", "backend", "frontend",
    "linux", "bash", "saas", "security", "engineering", "code", "system", "database"
]

# ==============================================================================
# FILTERING & CLASSIFICATION THRESHOLDS
# ==============================================================================
# Micro-influencer standard range defined in the specification
MIN_FOLLOWERS: int = 5_000
MAX_FOLLOWERS: int = 100_000

# Minimum engagement rate (e.g. 2.0% average across recent uploads)
MIN_ENGAGEMENT_RATE: float = 2.0

# Maximum days since last published content to ensure active status
MAX_DAYS_INACTIVE: int = 120

# ==============================================================================
# PERSONALIZATION CONSTRAINTS
# ==============================================================================
EMAIL_MIN_WORDS: int = 60
EMAIL_MAX_WORDS: int = 90

DM_MIN_WORDS: int = 15
DM_MAX_WORDS: int = 30

# Supported collaboration angles for outreach
COLLABORATION_ANGLES = [
    "Developer Tool Sponsorship",
    "Early Beta Access & Product Review",
    "Affiliate Creator Program",
    "UGC / Technical Walkthrough Creation",
    "Community Ambassador Program"
]

# ==============================================================================
# STORAGE & DATABASE PATHS
# ==============================================================================
DB_PATH = DATA_DIR / "outreach_system.db"
DATASET_CSV_PATH = DATA_DIR / "influencer_dataset.csv"
TRACKER_CSV_PATH = DATA_DIR / "outreach_tracker.csv"

# ==============================================================================
# API KEYS & CREDENTIALS (Loaded from .env)
# ==============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Email sending configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SENDER_NAME = os.getenv("SENDER_NAME", "DevPulse Outreach Team")
DEFAULT_SIMULATION_MODE = os.getenv("SIMULATION_MODE", "true").lower() == "true"
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
