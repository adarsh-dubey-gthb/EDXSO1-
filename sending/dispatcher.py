"""
Sending Layer Module.
Orchestrates outreach delivery:
- Filters for candidates with valid contact email
- Retrieves personalized email message & DM
- Enforces strict duplicate outreach prevention (idempotency)
- Dispatches via Live SMTP or Safe Simulation Mode
- Logs delivery status into persistent storage
- Demonstrates manual/simulated Instagram DM queue workflow
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, Optional
import requests
from config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASS,
    SENDER_NAME,
    DEFAULT_SIMULATION_MODE,
    N8N_WEBHOOK_URL
)
from models import Influencer, PersonalizedPitch, OutreachRecord
from storage.tracker import OutreachStorage

logger = logging.getLogger(__name__)


class OutreachDispatcher:
    """
    Manages email dispatching and simulated outreach execution.
    """

    def __init__(self, storage: Optional[OutreachStorage] = None, simulation_mode: bool = DEFAULT_SIMULATION_MODE):
        self.storage = storage or OutreachStorage()
        self.simulation_mode = simulation_mode

    def send_email_live(self, to_email: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Sends an outreach email via live SMTP server.
        """
        from dotenv import load_dotenv
        load_dotenv(override=True)
        smtp_user = os.getenv("SMTP_USER", "").strip()
        smtp_pass = os.getenv("SMTP_PASS", "").strip()
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
        try:
            smtp_port = int(os.getenv("SMTP_PORT", "587").strip())
        except ValueError:
            smtp_port = 587
        sender_name = os.getenv("SENDER_NAME", "DevPulse Partnerships").strip()

        if not smtp_user or smtp_user == "your_email@gmail.com" or not smtp_pass or smtp_pass == "your_app_password":
            return {
                "success": False,
                "error": "Live SMTP credentials not configured in .env. Please set SMTP_USER (your Gmail) and SMTP_PASS (16-char Google App Password)."
            }

        try:
            msg = MIMEMultipart()
            msg["From"] = f"{sender_name} <{smtp_user}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            return {"success": True, "error": None}
        except smtplib.SMTPAuthenticationError:
            err = "SMTP Authentication failed. For Gmail, use a 16-character App Password (not your personal login password)."
            logger.error(err)
            return {"success": False, "error": err}
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return {"success": False, "error": str(e)}

    def dispatch_outreach(self, influencer: Influencer, pitch: PersonalizedPitch) -> OutreachRecord:
        """
        Executes outreach for a single influencer:
        1. Validates that email exists ('Not Found' is safely handled)
        2. Checks against duplicate logs to prevent repeat contacts
        3. Dispatches via live SMTP or logs simulated delivery
        4. Records the result in the OutreachTracker database
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Step 1: Check for valid email
        if not influencer.email or influencer.email.strip().lower() == "not found":
            record = OutreachRecord(
                influencer_name=influencer.name,
                email="Not Found",
                message_generated="Yes",
                email_subject=pitch.email_subject,
                pitch_preview=pitch.email_pitch[:80] + "...",
                instagram_dm=pitch.instagram_dm,
                sent="No",
                date=now_str,
                status="SKIPPED_NO_EMAIL",
                error_message="No public contact email available on channel profile."
            )
            self.storage.log_outreach(record)
            return record

        # Step 2: Prevent duplicate outreach
        if self.storage.is_already_contacted(influencer.email, influencer.name):
            logger.info(f"Duplicate prevented: {influencer.name} ({influencer.email}) already reached.")
            record = OutreachRecord(
                influencer_name=influencer.name,
                email=influencer.email,
                message_generated="Yes",
                email_subject=pitch.email_subject,
                pitch_preview=pitch.email_pitch[:80] + "...",
                instagram_dm=pitch.instagram_dm,
                sent="No",
                date=now_str,
                status="DUPLICATE_PREVENTED",
                error_message="Creator was previously contacted. Duplicate delivery prevented."
            )
            return record

        # Step 3: Dispatch (Simulation or Live SMTP)
        if self.simulation_mode:
            logger.info(f"[SIMULATION] Outreach dispatched to {influencer.name} <{influencer.email}>")
            record = OutreachRecord(
                influencer_name=influencer.name,
                email=influencer.email,
                message_generated="Yes",
                email_subject=pitch.email_subject,
                pitch_preview=pitch.email_pitch,
                instagram_dm=pitch.instagram_dm,
                sent="Simulated",
                date=now_str,
                status="SIMULATED",
                error_message=None
            )
            self.storage.log_outreach(record)

        else:
            send_result = self.send_email_live(influencer.email, pitch.email_subject, pitch.email_pitch)
            if send_result["success"]:
                record = OutreachRecord(
                    influencer_name=influencer.name,
                    email=influencer.email,
                    message_generated="Yes",
                    email_subject=pitch.email_subject,
                    pitch_preview=pitch.email_pitch,
                    instagram_dm=pitch.instagram_dm,
                    sent="Yes",
                    date=now_str,
                    status="SENT",
                    error_message=None
                )
            else:
                record = OutreachRecord(
                    influencer_name=influencer.name,
                    email=influencer.email,
                    message_generated="Yes",
                    email_subject=pitch.email_subject,
                    pitch_preview=pitch.email_pitch,
                    instagram_dm=pitch.instagram_dm,
                    sent="No",
                    date=now_str,
                    status="FAILED",
                    error_message=send_result["error"]
                )
            self.storage.log_outreach(record)

        # Step 4: Forward outreach event to n8n / Zapier webhook if configured
        from dotenv import load_dotenv
        load_dotenv(override=True)
        webhook_url = os.getenv("N8N_WEBHOOK_URL", "").strip() or N8N_WEBHOOK_URL

        if webhook_url:
            try:
                payload = {
                    "influencer": record.influencer_name,
                    "name": record.influencer_name,
                    "email": record.email,
                    "followers": influencer.followers,
                    "engagement_rate": influencer.engagement_rate,
                    "niche": influencer.niche,
                    "recent_content_title": influencer.recent_content_title,
                    "subject": record.email_subject,
                    "email_subject": record.email_subject,
                    "pitch": pitch.email_pitch,
                    "instagram_dm": pitch.instagram_dm,
                    "angle": pitch.collaboration_angle,
                    "date": record.date,
                    "sent": record.sent,
                    "status": record.status,
                    "mode": "simulation" if self.simulation_mode else "live_smtp"
                }
                resp = requests.post(webhook_url, json=payload, timeout=6)
                logger.info(f"Forwarded outreach event for {influencer.name} to n8n webhook (HTTP {resp.status_code}).")
            except Exception as wh_err:
                logger.warning(f"Could not forward to n8n webhook: {wh_err}")

        return record

    def dispatch_batch(self, pairs: list[tuple[Influencer, PersonalizedPitch]]) -> list[OutreachRecord]:
        """
        Executes outreach for a collection of (influencer, pitch) pairs.
        """
        records: list[OutreachRecord] = []
        for inf, pitch in pairs:
            rec = self.dispatch_outreach(inf, pitch)
            records.append(rec)
        return records

    # Convenient alias for dispatch_outreach
    dispatch_email = dispatch_outreach

