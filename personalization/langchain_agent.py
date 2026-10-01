"""
LangChain Mail Agent with LCEL Orchestration & Human-in-the-Loop (HITL) Support.

Workflow:
1. Filters creators based on criteria.
2. Selects the top 5 highest-ranking qualified creators (by engagement and followers).
3. Invokes a LangChain LCEL chain (PromptTemplate | RunnableLambda | JsonOutputParser)
   to draft targeted 60-90 word emails and 15-30 word DMs.
4. Holds drafts in a Human-in-the-Loop review stage for review, manual edit, approval, or rejection.
5. Dispatches approved pitches via the sending dispatcher and records to tracker.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import JsonOutputParser
from google import genai

from config import GEMINI_API_KEY, COLLABORATION_ANGLES
from models import Influencer, PersonalizedPitch
from personalization.generator import MessagePersonalizer

logger = logging.getLogger(__name__)


class OutreachDraft(BaseModel):
    """Structured Pydantic schema for LangChain JSON output."""
    email_subject: str = Field(description="Email subject line under 8 words")
    email_body: str = Field(description="Email body strictly 60 to 90 words referencing recent work")
    instagram_dm: str = Field(description="Instagram / Social DM strictly 15 to 30 words")
    collaboration_angle: str = Field(description="The chosen collaboration angle")


class LangChainMailAgent:
    """
    Automated Mail Agent powered by LangChain Expression Language (LCEL).
    Drafts tailored outreach for the top 5 qualified creators and prepares them for HITL.
    """

    _rate_limited: bool = False

    def __init__(self):
        from dotenv import load_dotenv
        # Ensure environment variables are loaded
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), override=True)
        self.api_key = os.getenv("GEMINI_API_KEY", "") or GEMINI_API_KEY
        self.fallback_personalizer = MessagePersonalizer()
        self.client = None

        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize GenAI client for LangChain agent: {e}")

        # LangChain JSON Output Parser
        self.parser = JsonOutputParser(pydantic_object=OutreachDraft)

        # LangChain Prompt Template with format instructions
        self.prompt = PromptTemplate(
            template=(
                "You are an expert Partnerships Lead reaching out to tech content creators on behalf of DevPulse "
                "(a modern developer observability platform).\n\n"
                "Creator Details:\n"
                "- Name: {name}\n"
                "- Primary Themes: {themes}\n"
                "- Recent Content: \"{recent_content}\"\n"
                "- Subscribers: {followers:,}\n"
                "- Proposed Angle: {angle}\n\n"
                "Strict Constraints:\n"
                "1. Email Body: strictly 60 to 90 words. Specifically mention their recent content and explain how DevPulse helps their developer audience.\n"
                "2. Instagram/Social DM: strictly 15 to 30 words. Casual, high-affinity direct message.\n"
                "3. Email Subject: max 7 words, punchy and personalized.\n\n"
                "{format_instructions}"
            ),
            input_variables=["name", "themes", "recent_content", "followers", "angle"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )

        # Build LCEL Runnable Sequence: Prompt | RunnableLambda(LLM) | JsonOutputParser
        if self.client:
            self.chain = self.prompt | RunnableLambda(self._call_gemini_llm) | self.parser
        else:
            self.chain = None

    def _call_gemini_llm(self, prompt_value) -> str:
        """LangChain runnable step invoking Gemini REST API with instant fallback on quota exhaustion."""
        if LangChainMailAgent._rate_limited:
            raise RuntimeError("Gemini quota cached as exhausted.")

        if hasattr(prompt_value, "to_string"):
            prompt_str = prompt_value.to_string()
        elif hasattr(prompt_value, "text"):
            prompt_str = prompt_value.text
        else:
            prompt_str = str(prompt_value)

        import requests
        # Direct REST call without tenacity retry blocking
        models_to_try = ["gemini-flash-latest", "gemini-2.5-flash"]
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            try:
                payload = {
                    "contents": [{"parts": [{"text": prompt_str}]}],
                    "generationConfig": {"responseMimeType": "application/json"}
                }
                resp = requests.post(url, json=payload, timeout=4)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"].strip()
                elif resp.status_code in [429, 503]:
                    LangChainMailAgent._rate_limited = True
                    logger.info(f"Gemini {model} returned {resp.status_code}. Cached rate limit and falling back instantly.")
                    break
            except Exception as e:
                logger.debug(f"REST call to {model} failed: {e}")
                continue

        raise RuntimeError("LLM rate-limited or unavailable. Triggering deterministic synthesizer.")

    def generate_for_creator(self, influencer: Influencer, angle: str = "Developer Tool Sponsorship") -> PersonalizedPitch:
        """
        Executes the LangChain LCEL chain to generate structured pitch.
        Falls back to offline deterministic synthesizer if rate-limited or offline.
        """
        if self.chain and self.api_key:
            try:
                result = self.chain.invoke({
                    "name": influencer.name,
                    "themes": ", ".join(influencer.content_themes) if influencer.content_themes else influencer.niche,
                    "recent_content": influencer.recent_content_title or "latest engineering deep dive",
                    "followers": influencer.followers,
                    "angle": angle
                })

                email_body = result.get("email_body", "").strip()
                dm_body = result.get("instagram_dm", "").strip()
                subject = result.get("email_subject", f"DevPulse x {influencer.name.split()[0]}").strip()

                email_words = len(email_body.split())
                dm_words = len(dm_body.split())

                return PersonalizedPitch(
                    influencer_name=influencer.name,
                    email=influencer.email,
                    email_subject=subject,
                    email_pitch=email_body,
                    email_word_count=email_words,
                    instagram_dm=dm_body,
                    dm_word_count=dm_words,
                    collaboration_angle=angle
                )
            except Exception as e:
                logger.warning(f"LangChain LLM invocation note: {e}. Using intelligent fallback synthesizer.")

        # Reliable contextual synthesis fallback
        return self.fallback_personalizer.generate_pitch(influencer)

    def select_top_creators(self, passed_influencers: List[Influencer], top_n: int = 5) -> List[Influencer]:
        """
        Sorts passed creators by engagement rate and followers, selecting top N.
        """
        sorted_creators = sorted(
            passed_influencers,
            key=lambda x: (x.engagement_rate, x.followers),
            reverse=True
        )
        return sorted_creators[:top_n]

    def run_mail_agent_for_top_5(
        self, passed_influencers: List[Influencer]
    ) -> List[Tuple[Influencer, PersonalizedPitch]]:
        """
        Main LangChain Mail Agent Workflow:
        1. Takes all passed creators.
        2. Filters for top 5 creators with highest engagement/fit.
        3. Generates tailored email pitches and DMs using LangChain LCEL.
        4. Returns the batch ready for Human-in-the-Loop approval.
        """
        top_5 = self.select_top_creators(passed_influencers, top_n=5)
        drafts: List[Tuple[Influencer, PersonalizedPitch]] = []

        angles = [
            "Developer Tool Sponsorship",
            "Early Beta Access",
            "Affiliate Program",
            "UGC Walkthrough",
            "Product Review"
        ]

        for i, creator in enumerate(top_5):
            angle = angles[i % len(angles)]
            pitch = self.generate_for_creator(creator, angle=angle)
            drafts.append((creator, pitch))

        return drafts
