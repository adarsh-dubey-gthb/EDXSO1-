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
    "linux", "bash", "saas", "security", "engineering", "code", "system", "database",
    "tech", "developer", "programming", "tutorial", "software", "web", "dev", "api", "git"
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
DATASET_JSON_PATH = DATA_DIR / "influencer_dataset.json"
DATASET_EXCEL_PATH = DATA_DIR / "influencer_dataset.xlsx"
TRACKER_CSV_PATH = DATA_DIR / "outreach_tracker.csv"
TRACKER_JSON_PATH = DATA_DIR / "outreach_tracker.json"
TRACKER_EXCEL_PATH = DATA_DIR / "outreach_tracker.xlsx"

def get_env_or_secret(key: str, default: str = "") -> str:
    """Retrieve secret from environment variable or streamlit secrets."""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return default

# Sync Streamlit cloud secrets into os.environ so submodules can access them
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for _k, _v in st.secrets.items():
            if _k not in os.environ and isinstance(_v, (str, int, float, bool)):
                os.environ[_k] = str(_v)
except Exception:
    pass

# ==============================================================================
# API KEYS & CREDENTIALS (Loaded from .env or Streamlit Secrets)
# ==============================================================================
OPENAI_API_KEY = get_env_or_secret("OPENAI_API_KEY", "")
GROQ_API_KEY = get_env_or_secret("GROQ_API_KEY", "")
GEMINI_API_KEY = get_env_or_secret("GEMINI_API_KEY", "")
YOUTUBE_API_KEY = get_env_or_secret("YOUTUBE_API_KEY", "")

# Email sending configuration
SMTP_HOST = get_env_or_secret("SMTP_HOST", "smtp.gmail.com")
try:
    SMTP_PORT = int(get_env_or_secret("SMTP_PORT", "587"))
except ValueError:
    SMTP_PORT = 587
SMTP_USER = get_env_or_secret("SMTP_USER", "")
SMTP_PASS = get_env_or_secret("SMTP_PASS", "")
SENDER_NAME = get_env_or_secret("SENDER_NAME", "DevPulse Outreach Team")
DEFAULT_SIMULATION_MODE = get_env_or_secret("SIMULATION_MODE", "true").lower() == "true"
N8N_WEBHOOK_URL = get_env_or_secret("N8N_WEBHOOK_URL", "")

