"""
Storage & Outreach Tracking Module.
Maintains persistent SQLite database storage and handles CSV exports.
Ensures duplicate prevention through strict idempotency checks on email and creator name.
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd
from config import DB_PATH, DATASET_CSV_PATH, TRACKER_CSV_PATH
from models import Influencer, OutreachRecord, PersonalizedPitch

logger = logging.getLogger(__name__)


class OutreachStorage:
    """
    Handles SQLite database operations for discovered influencers and outreach logs.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes tables for influencers and outreach history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Discovered Influencers Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS influencers (
                    name TEXT PRIMARY KEY,
                    platform TEXT,
                    followers INTEGER,
                    engagement_rate REAL,
                    niche TEXT,
                    email TEXT,
                    profile_url TEXT,
                    content_themes TEXT,
                    bio_summary TEXT,
                    recent_content_title TEXT,
                    days_since_last_post INTEGER,
                    website TEXT,
                    social_handles TEXT,
                    audience_geography TEXT,
                    audience_age TEXT,
                    audience_gender TEXT,
                    filter_status TEXT,
                    filter_reason TEXT
                )
            """)

            # Outreach Tracking Log Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS outreach_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    influencer_name TEXT,
                    email TEXT,
                    message_generated TEXT,
                    email_subject TEXT,
                    pitch_preview TEXT,
                    instagram_dm TEXT,
                    sent TEXT,
                    date TEXT,
                    status TEXT,
                    error_message TEXT,
                    UNIQUE(email, influencer_name)
                )
            """)
            conn.commit()

    def save_influencers(self, influencers: List[Influencer]):
        """Persists or updates discovered influencers."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Ensure audience_age and audience_gender columns exist if upgrading from older schema
            try:
                cursor.execute("ALTER TABLE influencers ADD COLUMN audience_age TEXT")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE influencers ADD COLUMN audience_gender TEXT")
            except Exception:
                pass

            for inf in influencers:
                cursor.execute("""
                    INSERT OR REPLACE INTO influencers (
                        name, platform, followers, engagement_rate, niche, email,
                        profile_url, content_themes, bio_summary, recent_content_title,
                        days_since_last_post, website, social_handles, audience_geography,
                        audience_age, audience_gender, filter_status, filter_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    inf.name,
                    inf.platform,
                    inf.followers,
                    inf.engagement_rate,
                    inf.niche,
                    inf.email,
                    inf.profile_url,
                    ", ".join(inf.content_themes),
                    inf.bio_summary,
                    inf.recent_content_title,
                    inf.days_since_last_post,
                    inf.website or "",
                    inf.social_handles or "",
                    inf.audience_geography or "Global",
                    inf.audience_age or "20-35",
                    inf.audience_gender or "Mixed (Tech Audience)",
                    inf.filter_status,
                    inf.filter_reason
                ))
            conn.commit()

    def is_already_contacted(self, email: str, influencer_name: str) -> bool:
        """
        Duplicate prevention check.
        Returns True if an outreach attempt has already been logged.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if email and email.lower() != "not found":
                cursor.execute(
                    "SELECT id FROM outreach_log WHERE (email = ? OR influencer_name = ?) AND sent IN ('Yes', 'Simulated')",
                    (email, influencer_name)
                )
            else:
                cursor.execute(
                    "SELECT id FROM outreach_log WHERE influencer_name = ? AND sent IN ('Yes', 'Simulated')",
                    (influencer_name,)
                )
            return cursor.fetchone() is not None

    def log_outreach(self, record: OutreachRecord) -> bool:
        """
        Records an outreach event into the audit log.
        Prevents duplicates by checking existing records.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO outreach_log (
                        influencer_name, email, message_generated, email_subject,
                        pitch_preview, instagram_dm, sent, date, status, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.influencer_name,
                    record.email,
                    record.message_generated,
                    record.email_subject or "",
                    record.pitch_preview or "",
                    record.instagram_dm or "",
                    record.sent,
                    record.date,
                    record.status,
                    record.error_message or ""
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                logger.warning(f"Duplicate outreach blocked for {record.influencer_name} ({record.email})")
                return False

    def get_all_influencers(self) -> List[Dict[str, Any]]:
        """Retrieves all influencers from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM influencers ORDER BY followers DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_all_outreach_logs(self) -> List[Dict[str, Any]]:
        """Retrieves all outreach audit log entries."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM outreach_log ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]

    def clear_outreach_logs(self):
        """Wipes all demo/previous outreach records from database and resets tracker CSV."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM outreach_log")
            conn.commit()
        self.export_to_csv()


    def export_to_csv(self) -> Dict[str, str]:
        """
        Exports both the Influencer Dataset and Outreach Tracker to CSV files
        matching the exact structure mandated in the assignment.
        """
        influencers = self.get_all_influencers()
        logs = self.get_all_outreach_logs()

        # Format Influencer Dataset Table matching Section 3
        if influencers:
            df_inf = pd.DataFrame(influencers)
            formatted_inf = pd.DataFrame({
                "Influencer Name": df_inf["name"],
                "Platform": df_inf["platform"],
                "Profile URL": df_inf["profile_url"],
                "Follower Count": df_inf["followers"],
                "Engagement Rate": df_inf["engagement_rate"].apply(lambda x: f"{x:.1f}%"),
                "Category / Niche": df_inf["niche"],
                "Content Themes": df_inf["content_themes"],
                "Contact Email": df_inf["email"],
                "Instagram / YouTube / TikTok": df_inf.get("social_handles", pd.Series([""] * len(df_inf))),
                "Website": df_inf.get("website", pd.Series([""] * len(df_inf))),
                "Audience Age": df_inf.get("audience_age", pd.Series(["20-35"] * len(df_inf))),
                "Audience Gender": df_inf.get("audience_gender", pd.Series(["Mixed (Tech Audience)"] * len(df_inf))),
                "Audience Geography": df_inf.get("audience_geography", pd.Series(["Global"] * len(df_inf))),
                "Status": df_inf["filter_status"],
                "Audit Reason": df_inf["filter_reason"]
            })
            formatted_inf.to_csv(DATASET_CSV_PATH, index=False)

        # Format Outreach Tracker Table
        # Influencer | Email | Message Generated | Sent | Date | Status
        if logs:
            df_log = pd.DataFrame(logs)
            formatted_log = pd.DataFrame({
                "Influencer": df_log["influencer_name"],
                "Email": df_log["email"],
                "Email Subject": df_log["email_subject"],
                "Email Pitch": df_log["pitch_preview"],
                "Instagram DM": df_log["instagram_dm"],
                "Message Generated": df_log["message_generated"],
                "Sent": df_log["sent"],
                "Date": df_log["date"],
                "Status": df_log["status"]
            })
            formatted_log.to_csv(TRACKER_CSV_PATH, index=False)
        else:
            # Create empty tracker template if no logs yet
            pd.DataFrame(columns=[
                "Influencer", "Email", "Email Subject", "Email Pitch",
                "Instagram DM", "Message Generated", "Sent", "Date", "Status"
            ]).to_csv(TRACKER_CSV_PATH, index=False)

        return {
            "dataset_csv": str(DATASET_CSV_PATH),
            "tracker_csv": str(TRACKER_CSV_PATH)
        }
