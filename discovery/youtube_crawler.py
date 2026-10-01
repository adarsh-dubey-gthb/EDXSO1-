"""
Discovery Engine Module.
Discovers and extracts influencer candidate profiles from social platforms
(YouTube Data API v3 or curated seed dataset).
"""

import logging
from typing import List, Optional
import requests
from config import YOUTUBE_API_KEY, TECH_KEYWORDS, DEFAULT_NICHE
from models import Influencer
from discovery.seed_dataset import get_seed_influencers
from discovery.live_scraper import LiveYouTubeScraper

logger = logging.getLogger(__name__)


class InfluencerDiscoveryEngine:
    """
    Discovery engine responsible for querying platform APIs, live web scrapers,
    or verified repositories to retrieve micro-influencers matching a target niche.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or YOUTUBE_API_KEY
        self.live_scraper = LiveYouTubeScraper()

    def discover_live_search(self, query: str = "python developer", limit: int = 10, niche: str = DEFAULT_NICHE) -> List[Influencer]:
        """
        Executes real-time live discovery from YouTube without requiring any API keys.
        """
        return self.live_scraper.search_live(query=query, limit=limit, niche=niche)

    def discover_from_youtube_api(self, query: str = "python developer", max_results: int = 15) -> List[Influencer]:
        """
        Queries the official YouTube Data API v3 for channels matching tech queries.
        Retrieves channel statistics, subscriber counts, and recent video uploads.
        """
        if not self.api_key:
            logger.warning("YouTube API key not configured. Falling back to local discovery repository.")
            return []

        discovered: List[Influencer] = []
        try:
            # Step 1: Search for channels by keyword
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_params = {
                "key": self.api_key,
                "q": query,
                "type": "channel",
                "part": "snippet",
                "maxResults": min(max_results, 50)
            }
            resp = requests.get(search_url, params=search_params, timeout=10)
            if resp.status_code != 200:
                logger.error(f"YouTube search API returned status {resp.status_code}: {resp.text}")
                return []

            items = resp.json().get("items", [])
            channel_ids = [item["id"]["channelId"] for item in items if "channelId" in item.get("id", {})]
            if not channel_ids:
                return []

            # Step 2: Fetch detailed channel statistics
            channels_url = "https://www.googleapis.com/youtube/v3/channels"
            channels_params = {
                "key": self.api_key,
                "id": ",".join(channel_ids),
                "part": "snippet,statistics"
            }
            c_resp = requests.get(channels_url, params=channels_params, timeout=10)
            if c_resp.status_code != 200:
                return []

            for c in c_resp.json().get("items", []):
                snippet = c.get("snippet", {})
                stats = c.get("statistics", {})

                title = snippet.get("title", "Unknown")
                custom_url = snippet.get("customUrl", "")
                profile_url = f"https://www.youtube.com/{custom_url}" if custom_url else f"https://www.youtube.com/channel/{c['id']}"
                sub_count = int(stats.get("subscriberCount", 0))
                view_count = int(stats.get("viewCount", 0))
                video_count = max(int(stats.get("videoCount", 1)), 1)
                
                # Approximate engagement rate based on average views per video relative to subscribers
                avg_views = view_count / video_count
                engagement = round(min(max((avg_views / max(sub_count, 1)) * 100, 0.5), 15.0), 2)

                discovered.append(Influencer(
                    name=title,
                    platform="YouTube",
                    profile_url=profile_url,
                    followers=sub_count,
                    engagement_rate=engagement,
                    niche=DEFAULT_NICHE,
                    content_themes=[query.capitalize(), "Software Development"],
                    email="Not Found",
                    bio_summary=snippet.get("description", "")[:250],
                    recent_content_title=f"Recent update from {title}",
                    days_since_last_post=7
                ))

        except Exception as e:
            logger.error(f"Error during YouTube API discovery: {e}")

        return discovered

    def discover(self, target_niche: str = DEFAULT_NICHE, limit: int = 50) -> List[Influencer]:
        """
        Main discovery orchestrator.
        Loads at least 50 real influencer records, populating all mandatory fields.
        """
        raw_data = get_seed_influencers()
        influencers: List[Influencer] = []

        for item in raw_data:
            try:
                creator = Influencer(
                    name=item["name"],
                    platform=item.get("platform", "YouTube"),
                    profile_url=item["profile_url"],
                    followers=item["followers"],
                    engagement_rate=item["engagement_rate"],
                    niche=item.get("niche", target_niche),
                    content_themes=item.get("content_themes", []),
                    email=item.get("email", "Not Found"),
                    bio_summary=item.get("bio_summary", ""),
                    recent_content_title=item.get("recent_content_title", ""),
                    days_since_last_post=item.get("days_since_last_post", 10),
                    website=item.get("website"),
                    social_handles=item.get("social_handles"),
                    audience_geography=item.get("audience_geography", "Global"),
                    audience_age=item.get("audience_age", "18-34"),
                    audience_gender=item.get("audience_gender", "Mixed"),
                    filter_status="PENDING",
                    filter_reason="Awaiting evaluation"
                )
                influencers.append(creator)
            except Exception as err:
                logger.error(f"Error parsing record for {item.get('name')}: {err}")

        # If live YouTube API key is provided, supplement with live results
        if self.api_key:
            live_creators = self.discover_from_youtube_api(query="python ai engineer", max_results=10)
            influencers.extend(live_creators)

        logger.info(f"Discovered total of {len(influencers)} influencers.")
        return influencers[:max(limit, 50)]
