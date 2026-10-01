"""
Data Models for Micro-Influencer Outreach System.
Defines Pydantic schemas for Discovered Influencers, Filter Evaluations, 
Personalized Pitches, and Outreach Logs.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator


class Influencer(BaseModel):
    """
    Represents an influencer discovered from social platforms or directories.
    Enforces mandatory fields specified in the assignment requirements.
    """
    name: str = Field(..., description="Full creator name or channel brand name")
    platform: str = Field(default="YouTube", description="Social platform (e.g., YouTube, Instagram, TikTok)")
    profile_url: str = Field(..., description="Direct link to profile/channel")
    followers: int = Field(..., ge=0, description="Follower count or subscriber count")
    engagement_rate: float = Field(..., ge=0.0, description="Engagement rate percentage (e.g. 4.2 for 4.2%)")
    niche: str = Field(default="Technology", description="Primary content category/niche")
    content_themes: List[str] = Field(default_factory=list, description="Specific topics covered (e.g., AI, Python, Web Dev)")
    
    # Contact information
    email: str = Field(default="Not Found", description="Contact email address or 'Not Found'")
    
    # Context for personalization
    bio_summary: Optional[str] = Field(default="", description="Creator bio, channel description or niche focus")
    recent_content_title: Optional[str] = Field(default="", description="Title of most recent video, reel, or post")
    days_since_last_post: Optional[int] = Field(default=0, description="Days elapsed since the creator's latest upload")
    
    # Optional enrichment metadata
    website: Optional[str] = Field(default=None, description="Personal website or portfolio link")
    social_handles: Optional[str] = Field(default=None, description="Secondary social handles (e.g., Twitter/X, GitHub)")
    audience_geography: Optional[str] = Field(default="Global", description="Primary geographic audience concentration")
    audience_age: Optional[str] = Field(default="18-34", description="Estimated audience age bracket")
    audience_gender: Optional[str] = Field(default="Mixed", description="Estimated gender breakdown")
    
    # Filtering evaluation results
    filter_status: str = Field(default="PENDING", description="Status: 'PASSED' or 'FAILED: <Reason>'")
    filter_reason: Optional[str] = Field(default="Awaiting evaluation", description="Audit trail rationale for filter result")

    @field_validator("content_themes", mode="before")
    @classmethod
    def parse_content_themes(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v or []

    @field_validator("email")
    @classmethod
    def clean_email(cls, v: str) -> str:
        if not v:
            return "Not Found"
        v = str(v).strip()
        if not v or v.lower() in ["none", "null", "n/a", "not available", "unknown", ""]:
            return "Not Found"
        return v


class FilterResult(BaseModel):
    """
    Audit result for filtering and classification of an influencer.
    Provides clear reasoning why an influencer passed or failed criteria.
    """
    influencer_name: str
    passed: bool
    reasons: List[str] = Field(default_factory=list)
    final_status: str  # "PASSED" or "FAILED"


class PersonalizedPitch(BaseModel):
    """
    Represents generated outreach messages for an influencer.
    Guarantees word count tracking and personalization angle.
    """
    influencer_name: str
    email: str
    email_subject: str
    email_pitch: str
    email_word_count: int
    instagram_dm: str
    dm_word_count: int
    collaboration_angle: str
    generated_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class OutreachRecord(BaseModel):
    """
    Tracking entity for the sending layer.
    Ensures duplicate prevention and audit logging.
    """
    influencer_name: str
    email: str
    message_generated: str = "Yes"  # "Yes" or "No"
    email_subject: Optional[str] = ""
    pitch_preview: Optional[str] = ""
    instagram_dm: Optional[str] = ""
    sent: str = "No"  # "Yes", "Simulated", or "No"
    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    status: str = "PENDING"  # "SENT", "SIMULATED", "SKIPPED_NO_EMAIL", "DUPLICATE", "FAILED"
    error_message: Optional[str] = None
