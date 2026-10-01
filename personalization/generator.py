"""
AI Personalization Engine.
Generates dynamically tailored outreach pitches:
- Email Collaboration Pitch (60–90 words)
- Instagram / Social DM (15–30 words)

Supports Gemini 2.5 Flash, Groq, and OpenAI LLM API integration.
Includes in-memory response caching and automatic contextual synthesizer fallback
to seamlessly handle free-tier rate limits (429 Resource Exhausted).
"""

import os
import random
import logging
import requests
from typing import Optional, Dict
from config import (
    OPENAI_API_KEY,
    GROQ_API_KEY,
    GEMINI_API_KEY,
    COLLABORATION_ANGLES,
    EMAIL_MIN_WORDS,
    EMAIL_MAX_WORDS,
    DM_MIN_WORDS,
    DM_MAX_WORDS,
)
from models import Influencer, PersonalizedPitch
from personalization.prompts import UNIFIED_PITCH_PROMPT

logger = logging.getLogger(__name__)


class MessagePersonalizer:
    """
    Orchestrates the generation of personalized outreach messages.
    Caches responses to prevent redundant API calls and rate-limiting.
    """

    _cache: Dict[str, PersonalizedPitch] = {}
    _rate_limited: bool = False

    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv(override=True)
        self.openai_key = os.getenv("OPENAI_API_KEY", "") or OPENAI_API_KEY
        self.groq_key = os.getenv("GROQ_API_KEY", "") or GROQ_API_KEY
        self.gemini_key = os.getenv("GEMINI_API_KEY", "") or GEMINI_API_KEY

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """Calls Google Gemini REST API (gemini-2.5-flash)."""
        if not self.gemini_key or MessagePersonalizer._rate_limited:
            return None
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code == 200:
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            elif resp.status_code == 429:
                MessagePersonalizer._rate_limited = True
                logger.info("Gemini rate limit reached (429). Using instant contextual synthesis fallback.")
            else:
                logger.debug(f"Gemini API returned status {resp.status_code}")
        except Exception as e:
            logger.debug(f"Gemini API call exception: {e}")
        return None

    def _call_groq(self, prompt: str) -> Optional[str]:
        """Calls Groq Cloud API for ultra-fast Llama 3 generation."""
        if not self.groq_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 300
            }
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.debug(f"Groq API call exception: {e}")
        return None

    def _call_openai(self, prompt: str) -> Optional[str]:
        """Calls OpenAI Chat Completion API."""
        if not self.openai_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 300
            }
            resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.debug(f"OpenAI API call exception: {e}")
        return None

    def _synthesize_contextual_email(self, influencer: Influencer, angle: str) -> tuple[str, str]:
        """
        Intelligent offline synthesizer creating customized 60-90 word pitch
        guaranteed to meet word constraints without external API dependencies.
        """
        first_name = influencer.name.split()[0]
        recent_topic = influencer.recent_content_title or "your recent tech breakdown"
        primary_theme = influencer.content_themes[0] if influencer.content_themes else "software engineering"

        subject = f"Collaboration on {primary_theme} with DevPulse"

        body = (
            f"Hi {first_name},\n\n"
            f"Loved your recent breakdown on \"{recent_topic}\". Your hands-on focus on {primary_theme} "
            f"resonates deeply with our engineering team at DevPulse.\n\n"
            f"We're launching an observability workspace built specifically for active developers. Given your "
            f"engaged community, we would love to sponsor an upcoming video or partner on a dedicated {angle.lower()}.\n\n"
            f"We provide full creative freedom and competitive rates. Would you be open to exploring a sponsorship or integration this month?\n\n"
            f"Best regards,\nAlex Vance | DevPulse Partnerships"
        )
        return subject, body

    def _synthesize_contextual_dm(self, influencer: Influencer, angle: str) -> str:
        """
        Synthesizes a short, natural social DM strictly within 15-30 words.
        """
        first_name = influencer.name.split()[0]
        short_angle = "sponsorship" if "sponsor" in angle.lower() else ("review" if "review" in angle.lower() else "collaboration")
        dm = (
            f"Hey {first_name}! Loved your recent breakdown on {influencer.content_themes[0] if influencer.content_themes else 'tech'}. "
            f"We're launching DevPulse and would love to partner on a {short_angle}. Open to a quick chat?"
        )
        return dm

    def generate_pitch(self, influencer: Influencer) -> PersonalizedPitch:
        """
        Generates personalized email and social DM for an influencer in 1 unified call.
        Uses in-memory cache to prevent repeated rate-limiting.
        """
        # Check cache first
        if influencer.name in self._cache:
            return self._cache[influencer.name]

        angle = random.choice(COLLABORATION_ANGLES)
        prompt = UNIFIED_PITCH_PROMPT.format(
            name=influencer.name,
            themes=", ".join(influencer.content_themes),
            recent_content=influencer.recent_content_title,
            followers=influencer.followers,
            angle=angle
        )

        subject = ""
        email_body = ""
        dm_body = ""

        # Make single unified API call
        raw_response = None
        if self.gemini_key:
            raw_response = self._call_gemini(prompt)
        elif self.groq_key:
            raw_response = self._call_groq(prompt)
        elif self.openai_key:
            raw_response = self._call_openai(prompt)

        # Parse unified output
        if raw_response and "BODY:" in raw_response:
            try:
                parts = raw_response.split("BODY:")
                subject = parts[0].replace("SUBJECT:", "").strip()
                body_and_dm = parts[1]
                if "DM:" in body_and_dm:
                    email_body = body_and_dm.split("DM:")[0].strip()
                    dm_body = body_and_dm.split("DM:")[1].strip()
                else:
                    email_body = body_and_dm.strip()
            except Exception:
                pass

        # Robust fallbacks if API was rate-limited (429) or parse issue
        if not email_body or len(email_body.split()) < 40:
            subject, email_body = self._synthesize_contextual_email(influencer, angle)

        if not dm_body or len(dm_body.split()) < DM_MIN_WORDS or len(dm_body.split()) > DM_MAX_WORDS:
            dm_body = self._synthesize_contextual_dm(influencer, angle)

        pitch = PersonalizedPitch(
            influencer_name=influencer.name,
            email=influencer.email,
            email_subject=subject,
            email_pitch=email_body,
            email_word_count=len(email_body.split()),
            instagram_dm=dm_body,
            dm_word_count=len(dm_body.split()),
            collaboration_angle=angle
        )

        # Store in cache
        self._cache[influencer.name] = pitch
        return pitch
