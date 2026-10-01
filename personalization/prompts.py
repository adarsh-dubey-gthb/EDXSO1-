"""
Prompt Templates for AI Personalization Engine.
Encodes strict length constraints, collaboration angles, and personalization signals.
"""

UNIFIED_PITCH_PROMPT = """
You are an expert Partnerships Lead reaching out to technology creators on behalf of DevPulse (a developer observability and AI-assisted debugging platform).

Influencer Profile:
- Name: {name}
- Channel Themes: {themes}
- Recent Content: "{recent_content}"
- Follower Count: {followers:,}
- Collaboration Angle: {angle}

Instructions:
1. Write a personalized collaboration email pitch: MUST be strictly 60 to 90 words. Explicitly mention their recent video ("{recent_content}") and propose the {angle} collaboration.
2. Write a short, natural social DM: MUST be strictly 15 to 30 words. Peer-to-peer tone.

Format your output EXACTLY as:
SUBJECT: <Compelling subject line under 8 words>
BODY:
<Email body strictly 60 to 90 words>
DM:
<Instagram DM strictly 15 to 30 words>
"""

EMAIL_PITCH_PROMPT = UNIFIED_PITCH_PROMPT
INSTAGRAM_DM_PROMPT = UNIFIED_PITCH_PROMPT
