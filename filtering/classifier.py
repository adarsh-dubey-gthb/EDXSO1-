"""
Filtering and Classification Engine.
Evaluates discovered influencer profiles against predefined criteria:
- Follower count bounds (5,000 - 100,000)
- Category / Niche alignment (Technology)
- Engagement rate minimum threshold
- Channel recency & active status
- Brand-fit & topic keyword relevance

Generates a clear audit trail documenting why each influencer passed or failed.
"""

from typing import List, Tuple
from config import (
    MIN_FOLLOWERS,
    MAX_FOLLOWERS,
    MIN_ENGAGEMENT_RATE,
    MAX_DAYS_INACTIVE,
    TECH_KEYWORDS,
    DEFAULT_NICHE
)
from models import Influencer, FilterResult


class InfluencerClassifier:
    """
    Evaluator that classifies influencers into PASSED or FAILED categories
    with clear, verifiable reasoning for every candidate.
    """

    def __init__(
        self,
        min_followers: int = MIN_FOLLOWERS,
        max_followers: int = MAX_FOLLOWERS,
        min_engagement: float = MIN_ENGAGEMENT_RATE,
        max_days_inactive: int = MAX_DAYS_INACTIVE,
        target_niche: str = DEFAULT_NICHE
    ):
        self.min_followers = min_followers
        self.max_followers = max_followers
        self.min_engagement = min_engagement
        self.max_days_inactive = max_days_inactive
        self.target_niche = target_niche.lower()

    def evaluate(self, influencer: Influencer) -> FilterResult:
        """
        Evaluates a single influencer profile and updates its status and reason.
        Returns a FilterResult containing the pass/fail verdict and specific reasons.
        """
        fail_reasons: List[str] = []

        # Criterion 1: Niche / Category match
        if influencer.niche.lower() != self.target_niche:
            fail_reasons.append(
                f"Niche mismatch: '{influencer.niche}' does not match target category '{self.target_niche.capitalize()}'"
            )

        # Criterion 2: Micro-influencer follower boundaries (5,000 to 100,000)
        if influencer.followers < self.min_followers:
            fail_reasons.append(
                f"Subscribers/Followers ({influencer.followers:,}) below micro-influencer floor of {self.min_followers:,}"
            )
        elif influencer.followers > self.max_followers:
            fail_reasons.append(
                f"Subscribers/Followers ({influencer.followers:,}) exceeds micro-influencer ceiling of {self.max_followers:,} (Macro tier)"
            )

        # Criterion 3: Engagement rate threshold
        if influencer.engagement_rate < self.min_engagement:
            fail_reasons.append(
                f"Engagement rate ({influencer.engagement_rate:.1f}%) is below minimum healthy baseline of {self.min_engagement:.1f}%"
            )

        # Criterion 4: Content recency / Activity
        if influencer.days_since_last_post is not None and influencer.days_since_last_post > self.max_days_inactive:
            fail_reasons.append(
                f"Channel inactive: last published content was {influencer.days_since_last_post} days ago (exceeds {self.max_days_inactive} days)"
            )

        # Criterion 5: Brand-fit and content relevance
        combined_text = (
            f"{influencer.name} {influencer.bio_summary} {' '.join(influencer.content_themes)} {influencer.recent_content_title}"
        ).lower()
        has_relevant_keyword = any(kw in combined_text for kw in TECH_KEYWORDS)
        if not has_relevant_keyword:
            fail_reasons.append(
                "Content relevance: No verified tech / software developer keywords found in recent content or bio"
            )

        # Determine final status
        passed = len(fail_reasons) == 0
        if passed:
            final_status = "PASSED"
            summary_reason = f"Passed all criteria: Tech niche, {influencer.followers:,} followers (within 5k-100k), {influencer.engagement_rate:.1f}% engagement, recently active."
        else:
            final_status = "FAILED"
            summary_reason = " | ".join(fail_reasons)

        # Update the influencer object directly for persistence
        influencer.filter_status = final_status
        influencer.filter_reason = summary_reason

        return FilterResult(
            influencer_name=influencer.name,
            passed=passed,
            reasons=fail_reasons if not passed else ["Passed all criteria successfully."],
            final_status=final_status
        )

    def filter_batch(self, influencers: List[Influencer]) -> Tuple[List[Influencer], List[Influencer]]:
        """
        Processes a collection of influencers.
        Returns a tuple: (qualified_influencers, disqualified_influencers).
        """
        passed_list: List[Influencer] = []
        failed_list: List[Influencer] = []

        for inf in influencers:
            result = self.evaluate(inf)
            if result.passed:
                passed_list.append(inf)
            else:
                failed_list.append(inf)

        return passed_list, failed_list
