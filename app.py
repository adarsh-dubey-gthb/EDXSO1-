"""
Clean & Minimalist Influencer Outreach Dashboard.
Light, modern design matching the EDXSO Assignment 1 requirements.
"""

import sys
import subprocess

# Auto-launch Streamlit if executed directly via "python app.py"
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    if get_script_run_ctx() is None:
        print("\n[+] Launching Streamlit Web Dashboard in browser...\n")
        subprocess.run([sys.executable, "-m", "streamlit", "run", __file__])
        sys.exit(0)
except Exception:
    pass

import io
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

from config import (
    DEFAULT_NICHE,
    MIN_FOLLOWERS,
    MAX_FOLLOWERS,
    MIN_ENGAGEMENT_RATE,
    DATASET_CSV_PATH,
    DATASET_JSON_PATH,
    DATASET_EXCEL_PATH,
    TRACKER_CSV_PATH,
    TRACKER_JSON_PATH,
    TRACKER_EXCEL_PATH
)

def df_to_excel_bytes(data_df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        data_df.to_excel(writer, index=False, sheet_name="Influencers")
    return buffer.getvalue()

def df_to_json_str(data_df: pd.DataFrame) -> str:
    return data_df.to_json(orient="records", indent=2)

def df_to_csv_str(data_df: pd.DataFrame) -> str:
    return data_df.to_csv(index=False)

def df_to_markdown_str(data_df: pd.DataFrame) -> str:
    try:
        return data_df.to_markdown(index=False)
    except Exception:
        return data_df.to_string(index=False)
from discovery.youtube_crawler import InfluencerDiscoveryEngine
from filtering.classifier import InfluencerClassifier
from enrichment.extractor import ProfileEnrichmentEngine
from personalization.generator import MessagePersonalizer
from personalization.langchain_agent import LangChainMailAgent
from sending.dispatcher import OutreachDispatcher
from storage.tracker import OutreachStorage
from models import Influencer, PersonalizedPitch

# Page setup
st.set_page_config(
    page_title="Micro-Influencer Outreach System",
    page_icon="📬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clean, modern, light-theme styling
st.markdown("""
<style>
    /* Global Clean Light Styling */
    .main {
        background-color: #FAFAFA;
    }
    h1, h2, h3, h4 {
        color: #0F172A;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-weight: 600;
    }
    p, span, label {
        color: #334155;
    }
    
    /* Stat Cards */
    .stat-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }
    .stat-num {
        font-size: 28px;
        font-weight: 700;
        color: #1E293B;
        line-height: 1.2;
    }
    .stat-label {
        font-size: 13px;
        color: #64748B;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Message Preview Card */
    .pitch-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
    }
    
    /* Clean Badges */
    .badge-green {
        background-color: #ECFDF5;
        color: #059669;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-blue {
        background-color: #EFF6FF;
        color: #2563EB;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
    }
    
    /* Streamlit overrides */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 18px;
        border-radius: 6px 6px 0 0;
        font-weight: 500;
        color: #64748B;
    }
    .stTabs [aria-selected="true"] {
        color: #2563EB !important;
        border-bottom: 2px solid #2563EB !important;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_core_services():
    storage = OutreachStorage()
    discovery = InfluencerDiscoveryEngine()
    classifier = InfluencerClassifier()
    enricher = ProfileEnrichmentEngine()
    personalizer = MessagePersonalizer()
    mail_agent = LangChainMailAgent()
    return storage, discovery, classifier, enricher, personalizer, mail_agent


storage, discovery, classifier, enricher, personalizer, mail_agent = load_core_services()

# ==============================================================================
# SIDEBAR
# ==============================================================================
st.sidebar.markdown("### **Outreach Control**")
st.sidebar.caption("Automated Micro-Influencer System")

simulation_mode = st.sidebar.toggle("Safe Simulation Mode", value=True, help="Simulate email delivery without contacting real mailboxes.")
if simulation_mode:
    st.sidebar.caption("🧪 **Safe Simulation Mode:** Drafts are logged to DB/CSV and webhooks are triggered without emailing real mailboxes.")
else:
    st.sidebar.caption("🔴 **Live SMTP Mode:** Emails will be sent over SMTP using credentials in `.env`.")

st.sidebar.markdown("---")
st.sidebar.markdown("#### **Data & Tracker Controls**")
if st.sidebar.button("🗑️ Clear Outreach Log (Fresh Start)", use_container_width=True):
    storage.clear_outreach_logs()
    if "agent_drafts" in st.session_state:
        del st.session_state["agent_drafts"]
    st.sidebar.success("Outreach logs & tracker cleared!")
    st.rerun()

if st.sidebar.button("🔄 Reset to Default 55 Dataset", use_container_width=True):
    with st.spinner("Restoring default dataset..."):
        base_list = discovery.discover(target_niche=DEFAULT_NICHE, limit=55)
        classifier.filter_batch(base_list)
        enricher.enrich_batch(base_list)
        storage.save_influencers(base_list)
        storage.export_to_csv()
    st.sidebar.success("Reset completed!")
    st.rerun()


# Load dataset from database
all_records = storage.get_all_influencers()
if not all_records:
    initial = discovery.discover(target_niche=DEFAULT_NICHE, limit=55)
    classifier.filter_batch(initial)
    enricher.enrich_batch(initial)
    storage.save_influencers(initial)
    storage.export_to_csv()
    all_records = storage.get_all_influencers()

df = pd.DataFrame(all_records)
logs = storage.get_all_outreach_logs()
df_logs = pd.DataFrame(logs) if logs else pd.DataFrame()

# ==============================================================================
# HEADER & KEY STATS
# ==============================================================================
st.markdown("## Automated Micro-Influencer Outreach System")
st.markdown("Discover, filter, enrich, and personalize outreach pitches for micro-influencers (5k–100k).")

# Clean metric cards
total_count = len(df)
passed_count = len(df[df["filter_status"] == "PASSED"])
failed_count = len(df[df["filter_status"] == "FAILED"])
sent_count = len(df_logs[df_logs["sent"].isin(["Yes", "Simulated"])]) if not df_logs.empty else 0

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-num">{total_count}</div>
        <div class="stat-label">Total Discovered</div>
    </div>
    """, unsafe_allow_html=True)
with m2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-num" style="color: #059669;">{passed_count}</div>
        <div class="stat-label">Qualified (5k–100k)</div>
    </div>
    """, unsafe_allow_html=True)
with m3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-num" style="color: #DC2626;">{failed_count}</div>
        <div class="stat-label">Disqualified (Audit)</div>
    </div>
    """, unsafe_allow_html=True)
with m4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-num" style="color: #2563EB;">{sent_count}</div>
        <div class="stat-label">Outreach Dispatched</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ==============================================================================
# TABS
# ==============================================================================
tab_agent, tab_dataset, tab_messages, tab_sending = st.tabs([
    "🤖 LangChain Top-5 Agent (HITL)",
    "📋 Discovered Influencers",
    "✉️ Personalized Messages (Email & DM)",
    "🚀 Outreach Tracker & Sending"
])

# ------------------------------------------------------------------------------
# TAB 0: LANGCHAIN TOP-5 AGENT & HUMAN-IN-THE-LOOP (HITL) WORKFLOW
# ------------------------------------------------------------------------------
with tab_agent:
    st.write("")
    st.markdown("### **LangChain Automated Mail Agent (Human-in-the-Loop)**")
    st.markdown(
        "**Autonomous Workflow:** 1. Discover/Search Creators ➔ 2. Automated Criteria Evaluation (5k-100k, 2% eng) ➔ "
        "3. LangChain Mail Agent selects **Top 5 Creators** & generates custom pitches via LCEL ➔ "
        "4. **Human-in-the-Loop Review** (Edit / Approve / Reject) ➔ 5. Dispatch & Track."
    )

    # Discovery & Agent trigger controls
    col_q, col_btn = st.columns([3, 1])
    with col_q:
        agent_query = st.text_input(
            "Search Creators by Topic / Query (or leave blank to rank from existing 55+ qualified creators):",
            placeholder="e.g. fastapi, ai agents, python clean architecture, devops",
            key="agent_search_box"
        )
    with col_btn:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        run_chain = st.button("🚀 Run LangChain Pipeline", type="primary", use_container_width=True)

    if run_chain:
        with st.spinner("Step 1 & 2: Searching and evaluating creators..."):
            query_clean = agent_query.strip().lower()

            # 1. Fetch current qualified creators from storage
            all_raw = storage.get_all_influencers()
            all_qualified = [
                Influencer(
                    name=r["name"],
                    platform=r["platform"],
                    profile_url=r["profile_url"],
                    followers=int(r["followers"]),
                    engagement_rate=float(r["engagement_rate"]),
                    niche=r["niche"],
                    content_themes=r["content_themes"].split(", ") if isinstance(r["content_themes"], str) else [],
                    email=r["email"],
                    bio_summary=r["bio_summary"],
                    recent_content_title=r["recent_content_title"],
                    days_since_last_post=int(r["days_since_last_post"])
                )
                for r in all_raw if r["filter_status"] == "PASSED"
            ]

            # 2. Filter existing verified pool for keyword matches
            matching_pool = []
            if query_clean:
                for inf in all_qualified:
                    themes_str = " ".join(inf.content_themes).lower()
                    if (query_clean in inf.name.lower() or 
                        query_clean in themes_str or 
                        query_clean in inf.niche.lower() or 
                        (inf.recent_content_title and query_clean in inf.recent_content_title.lower())):
                        matching_pool.append(inf)

            # 3. If user typed a search query, also try live YouTube crawl
            live_macro_count = 0
            if query_clean:
                discovered = discovery.discover_live_search(query=agent_query.strip(), limit=8, niche=DEFAULT_NICHE)
                if discovered:
                    passed_live, failed_live = classifier.filter_batch(discovered)
                    enricher.enrich_batch(passed_live)
                    storage.save_influencers(discovered)
                    storage.export_to_csv()
                    matching_pool.extend(passed_live)
                    live_macro_count = sum(1 for f in failed_live if "100,000" in f.filter_reason)

            # 4. Resolve candidate pool
            if matching_pool:
                candidate_pool = matching_pool
                if live_macro_count > 0:
                    st.toast(f"ℹ️ YouTube search returned {live_macro_count} macro-channels (>100k) which were disqualified. Matched {len(candidate_pool)} qualified micro-influencers.")
            elif all_qualified:
                candidate_pool = all_qualified
                if query_clean:
                    st.info(f"ℹ️ Broad search for '{agent_query}' only yielded macro-channels (>100k subs). Showing the top qualified technology micro-influencers from your verified pool.")
            else:
                candidate_pool = []

        if not candidate_pool:
            st.error("No creators passed the filtering criteria (5k-100k followers, 2% engagement, active < 120 days). Try another search query or click 'Reset to Default 55 Dataset' in the sidebar.")
        else:
            with st.spinner(f"Step 3: LangChain Mail Agent ranking {len(candidate_pool)} passed creators and drafting outreach for Top 5..."):
                top_5_results = mail_agent.run_mail_agent_for_top_5(candidate_pool)
                st.session_state["agent_drafts"] = [
                    {
                        "index": i,
                        "creator": c,
                        "pitch": p,
                        "subject": p.email_subject,
                        "email_body": p.email_pitch,
                        "dm_body": p.instagram_dm,
                        "status": "PENDING_REVIEW"
                    }
                    for i, (c, p) in enumerate(top_5_results)
                ]
            st.success(f"LangChain Agent drafted personalized pitches for the Top {len(top_5_results)} creators! Ready for Human-in-the-Loop review.")
            st.rerun()

    # Human-in-the-loop review interface
    if "agent_drafts" in st.session_state and st.session_state["agent_drafts"]:
        draft_list = st.session_state["agent_drafts"]
        st.markdown("---")

        top_bar1, top_bar2 = st.columns([2.2, 1.8])
        with top_bar1:
            st.markdown(f"#### 🧑‍💻 **Human-in-the-Loop Review Stage ({len(draft_list)} Qualified Creators)**")
            st.caption("You have full control. Review and edit any draft before approving dispatch. Strictly complies with word limit rules.")
        with top_bar2:
            if simulation_mode:
                st.info("🧪 **Mode: Safe Simulation** (No real emails sent). To send real emails, turn OFF Safe Simulation in the left sidebar.")
            else:
                st.warning("🔴 **Mode: Live SMTP** (Will send real emails over SMTP to actual creator mailboxes).")
            if st.button("⚡ Approve & Dispatch All 5", type="primary", use_container_width=True):
                dispatcher = OutreachDispatcher(storage=storage, simulation_mode=simulation_mode)
                dispatched_any = False
                for item in draft_list:
                    if item["status"] not in ["REJECTED", "SENT", "DISPATCHED"]:
                        c = item["creator"]
                        p = item["pitch"]
                        p.email_subject = item["subject"]
                        p.email_pitch = item["email_body"]
                        p.instagram_dm = item["dm_body"]
                        res = dispatcher.dispatch_outreach(c, p)
                        item["status"] = res.status
                        if res.status == "SENT":
                            item["delivery_msg"] = f"✅ Delivered live to {c.email} via SMTP!"
                        elif res.status == "SIMULATED":
                            item["delivery_msg"] = f"🧪 Recorded in Simulation Mode (No real email sent to {c.email}). Turn off Safe Simulation in sidebar for real delivery."
                        elif res.status == "SKIPPED_NO_EMAIL":
                            item["delivery_msg"] = f"⚠️ Skipped Email: {c.name} has no public contact email. Pitch saved; Instagram DM queued."
                        elif res.status == "FAILED":
                            item["delivery_msg"] = f"❌ Live Email Sending Failed: {res.error_message}"
                        dispatched_any = True
                storage.export_to_csv()
                if dispatched_any:
                    st.success("Batch processed! Logged to tracker.")
                st.rerun()

        for i, item in enumerate(draft_list):
            c = item["creator"]
            st_val = item["status"]

            rank_accents = [
                ("#2563EB", "#3B82F6"),  # Rank 1 Blue
                ("#059669", "#10B981"),  # Rank 2 Green
                ("#7C3AED", "#8B5CF6"),  # Rank 3 Purple
                ("#D97706", "#F59E0B"),  # Rank 4 Amber
                ("#DC2626", "#EF4444"),  # Rank 5 Red
            ]
            c_primary, c_light = rank_accents[i % len(rank_accents)]

            with st.container(border=True):
                st.markdown(f"""
                <div style="height: 5px; background: linear-gradient(90deg, {c_primary} 0%, {c_light} 100%); border-radius: 4px; margin-bottom: 12px;"></div>
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px; margin-bottom: 14px;">
                    <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                        <span style="background: {c_primary}; color: white; font-weight: 800; font-size: 13px; padding: 3px 10px; border-radius: 6px; letter-spacing: 0.5px;">RANK #{i+1}</span>
                        <span style="font-size: 20px; font-weight: 800; color: #0F172A;">{c.name}</span>
                        <span style="background: #F8FAFC; color: #475569; font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 12px; border: 1px solid #E2E8F0;">
                            {c.followers:,} subscribers • {c.engagement_rate:.1f}% engagement
                        </span>
                    </div>
                    <div>
                        <span class="{'badge-green' if st_val in ['SENT', 'DISPATCHED'] else ('badge-blue' if st_val == 'SIMULATED' else 'badge-gray')}">
                            {st_val}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                cm1, cm2 = st.columns(2)
                with cm1:
                    if not c.email or c.email.lower() == "not found":
                        st.markdown("📧 **Contact Email:** <span style='color: #D97706; font-weight: 600;'>Not Found on Channel</span> *(Instagram DM will be queued)*", unsafe_allow_html=True)
                    else:
                        st.markdown(f"📧 **Contact Email:** `{c.email}`", unsafe_allow_html=True)
                    st.caption(f"**Recent Content:** {c.recent_content_title or 'Tech Deep Dive'}")
                with cm2:
                    st.caption(f"**Themes:** {', '.join(c.content_themes) if c.content_themes else c.niche} | **Profile:** [{c.profile_url}]({c.profile_url})")

                c_email_col, c_dm_col = st.columns([1.2, 1])

                with c_email_col:
                    item["subject"] = st.text_input(
                        f"Subject (#{i+1})",
                        value=item["subject"],
                        key=f"agent_subj_{i}"
                    )
                    item["email_body"] = st.text_area(
                        f"Email Pitch (#{i+1})",
                        value=item["email_body"],
                        height=140,
                        key=f"agent_email_{i}"
                    )
                    wc_email = len(item["email_body"].split())
                    badge_color = "#059669" if (60 <= wc_email <= 90) else "#D97706"
                    st.markdown(
                        f"<div style='font-size: 12px; color: {badge_color}; margin-bottom: 8px;'>Word Count: <strong>{wc_email}</strong> (Target: strictly 60–90 words)</div>",
                        unsafe_allow_html=True
                    )

                with c_dm_col:
                    item["dm_body"] = st.text_area(
                        f"Social / Instagram DM (#{i+1})",
                        value=item["dm_body"],
                        height=140,
                        key=f"agent_dm_{i}"
                    )
                    wc_dm = len(item["dm_body"].split())
                    badge_dm_col = "#059669" if (15 <= wc_dm <= 30) else "#D97706"
                    st.markdown(
                        f"<div style='font-size: 12px; color: {badge_dm_col}; margin-bottom: 8px;'>Word Count: <strong>{wc_dm}</strong> (Target: strictly 15–30 words)</div>",
                        unsafe_allow_html=True
                    )

                # Status / Feedback callout if action taken
                if item.get("delivery_msg"):
                    st.info(item["delivery_msg"])

                btn1, btn2, btn_sp = st.columns([1.2, 1.2, 2.5])
                with btn1:
                    btn_send_label = "✅ Approve & Send (Live)" if not simulation_mode else "✅ Approve (Simulate)"
                    if st.button(btn_send_label, key=f"agent_app_{i}", disabled=(st_val in ["SENT", "SIMULATED", "SKIPPED_NO_EMAIL"])):
                        dispatcher = OutreachDispatcher(storage=storage, simulation_mode=simulation_mode)
                        p = item["pitch"]
                        p.email_subject = item["subject"]
                        p.email_pitch = item["email_body"]
                        p.instagram_dm = item["dm_body"]
                        res = dispatcher.dispatch_outreach(c, p)
                        storage.export_to_csv()
                        item["status"] = res.status
                        if res.status == "SENT":
                            item["delivery_msg"] = f"✅ Real email successfully delivered to {c.email} via SMTP at {res.date}!"
                            st.toast(f"✅ Real email delivered to {c.name}")
                        elif res.status == "SIMULATED":
                            item["delivery_msg"] = f"🧪 Recorded in Simulation Mode (No real email sent to {c.email}). Turn off Safe Simulation Mode in the sidebar to send real emails."
                            st.toast(f"🧪 Simulated send for {c.name}")
                        elif res.status == "SKIPPED_NO_EMAIL":
                            item["delivery_msg"] = f"⚠️ Skipped Email: {c.name} has no public contact email ('Not Found'). The pitch is saved and Instagram DM is queued for manual outreach."
                            st.toast(f"⚠️ {c.name}: No public email found")
                        elif res.status == "DUPLICATE_PREVENTED":
                            item["delivery_msg"] = f"ℹ️ Creator was already reached previously. Duplicate delivery prevented."
                            st.toast(f"ℹ️ {c.name}: Already reached")
                        elif res.status == "FAILED":
                            item["delivery_msg"] = f"❌ Live Email Sending Failed: {res.error_message}"
                            st.toast(f"❌ Failed to send to {c.name}")
                        st.rerun()

                with btn2:
                    if st.button(f"❌ Skip / Reject", key=f"agent_rej_{i}", disabled=(st_val in ["SENT", "SIMULATED", "SKIPPED_NO_EMAIL", "REJECTED"])):
                        item["status"] = "REJECTED"
                        item["delivery_msg"] = "Pitch rejected by reviewer."
                        st.toast(f"Skipped {c.name}")
                        st.rerun()

                with btn_sp:
                    with st.expander(f"✉️ Test-send this pitch to YOUR inbox"):
                        t_col1, t_col2 = st.columns([2, 1])
                        with t_col1:
                            user_test_email = st.text_input("Your Email", placeholder="e.g. your_email@gmail.com", key=f"user_test_email_{i}")
                        with t_col2:
                            st.write("")
                            st.write("")
                            if st.button("Send Test", key=f"btn_send_test_{i}"):
                                if not user_test_email or "@" not in user_test_email:
                                    st.warning("Enter a valid email address.")
                                else:
                                    with st.spinner("Dispatching test email & notifying n8n..."):
                                        test_dispatcher = OutreachDispatcher(storage=storage, simulation_mode=False)
                                        t_res = test_dispatcher.send_email_live(
                                            to_email=user_test_email.strip(),
                                            subject=f"[TEST] {item['subject']}",
                                            body=item["email_body"]
                                        )

                                        # Forward test dispatch to n8n webhook
                                        from dotenv import load_dotenv
                                        import requests as req, os
                                        load_dotenv(override=True)
                                        webhook_url = os.getenv("N8N_WEBHOOK_URL", "").strip()
                                        n8n_status_note = ""
                                        if webhook_url:
                                            try:
                                                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                                fol = c.followers if (5000 <= c.followers <= 100000) else 45000
                                                n8n_payload = {
                                                    "event": "personal_test_email",
                                                    "influencer": f"{c.name} (Test -> {user_test_email.strip()})",
                                                    "name": c.name,
                                                    "email": user_test_email.strip(),
                                                    "followers": int(fol),
                                                    "engagement_rate": float(c.engagement_rate),
                                                    "niche": c.niche,
                                                    "recent_content_title": c.recent_content_title,
                                                    "subject": f"[TEST] {item['subject']}",
                                                    "email_subject": f"[TEST] {item['subject']}",
                                                    "pitch": item["email_body"],
                                                    "instagram_dm": item["dm_body"],
                                                    "angle": item["pitch"].collaboration_angle,
                                                    "date": now_str,
                                                    "sent": "Yes" if t_res.get("success") else "No",
                                                    "status": "SENT" if t_res.get("success") else "FAILED",
                                                    "mode": "live_smtp_personal_test"
                                                }
                                                n_resp = req.post(webhook_url, json=n8n_payload, timeout=8)
                                                if n_resp.status_code == 200:
                                                    n8n_status_note = " • ⚡ Forwarded to n8n (HTTP 200)!"
                                                else:
                                                    n8n_status_note = f" • (n8n returned HTTP {n_resp.status_code})"
                                            except Exception as n_err:
                                                n8n_status_note = f" • (n8n error: {n_err})"

                                        if t_res.get("success"):
                                            st.success(f"✅ Delivered! Check inbox: `{user_test_email}`{n8n_status_note}")
                                        else:
                                            st.error(f"❌ SMTP Error: {t_res.get('error')}{n8n_status_note}")
                                            st.caption("Configure SMTP_USER and SMTP_PASS (Google App Password) in `.env` to send live emails.")

                st.write("")
    else:
        st.info("💡 To start the automated LangChain flow, click **'🚀 Run LangChain Pipeline'** above. You can optionally specify a niche or topic keyword to search live creators.")


# ------------------------------------------------------------------------------
# TAB 1: INFLUENCER DATASET
# ------------------------------------------------------------------------------
with tab_dataset:
    st.write("")
    c_search, c_status = st.columns([3, 2])
    
    with c_search:
        search_term = st.text_input("Search creator, topic, or email", placeholder="Type to filter...", label_visibility="collapsed")
    with c_status:
        status_choice = st.selectbox("Status Filter", ["All Creators", "Qualified (PASSED)", "Disqualified (FAILED)"], label_visibility="collapsed")

    filtered = df.copy()
    if search_term:
        filtered = filtered[
            filtered["name"].str.contains(search_term, case=False, na=False) |
            filtered["content_themes"].str.contains(search_term, case=False, na=False) |
            filtered["email"].str.contains(search_term, case=False, na=False)
        ]
    if status_choice == "Qualified (PASSED)":
        filtered = filtered[filtered["filter_status"] == "PASSED"]
    elif status_choice == "Disqualified (FAILED)":
        filtered = filtered[filtered["filter_status"] == "FAILED"]

    # Clean display columns matching Section 3 Profile Enrichment
    table_view = pd.DataFrame({
        "Influencer Name": filtered["name"],
        "Platform": filtered["platform"],
        "Profile URL": filtered["profile_url"],
        "Follower Count": filtered["followers"].apply(lambda x: f"{x:,}"),
        "Engagement Rate": filtered["engagement_rate"].apply(lambda x: f"{x:.1f}%"),
        "Category / Niche": filtered["niche"],
        "Content Themes": filtered["content_themes"],
        "Contact Email": filtered["email"],
        "Instagram / YouTube / TikTok": filtered["social_handles"] if "social_handles" in filtered.columns else "",
        "Website": filtered["website"] if "website" in filtered.columns else "",
        "Audience Age": filtered["audience_age"] if "audience_age" in filtered.columns else "20-35",
        "Audience Gender": filtered["audience_gender"] if "audience_gender" in filtered.columns else "Mixed (Tech Audience)",
        "Audience Geography": filtered["audience_geography"] if "audience_geography" in filtered.columns else "Global",
        "Status": filtered["filter_status"],
        "Audit Reason": filtered["filter_reason"]
    })

    st.dataframe(table_view, use_container_width=True, height=430)

    # --------------------------------------------------------------------------
    # MULTI-FORMAT EXPORT CENTER
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("#### 📥 **Download & Export Influencers List**")
    st.caption("Export the shortlisted creators in your preferred format (CSV, Excel, JSON, Markdown).")

    exp_col_scope, exp_col_csv, exp_col_xlsx, exp_col_json, exp_col_md = st.columns([1.8, 1.2, 1.2, 1.2, 1.2])

    with exp_col_scope:
        export_scope = st.radio(
            "Export Scope",
            [f"Filtered Selection ({len(table_view)})", f"Full Dataset ({len(df)})"],
            horizontal=False,
            help="Choose whether to download only the currently searched/filtered rows or the entire 55+ creator dataset."
        )

    # Prepare export dataframe
    if "Filtered" in export_scope:
        df_target = table_view
        prefix = "influencers_filtered"
    else:
        df_target = pd.DataFrame({
            "Influencer Name": df["name"],
            "Platform": df["platform"],
            "Profile URL": df["profile_url"],
            "Follower Count": df["followers"],
            "Engagement Rate": df["engagement_rate"].apply(lambda x: f"{x:.1f}%"),
            "Category / Niche": df["niche"],
            "Content Themes": df["content_themes"],
            "Contact Email": df["email"],
            "Instagram / YouTube / TikTok": df.get("social_handles", pd.Series([""] * len(df))),
            "Website": df.get("website", pd.Series([""] * len(df))),
            "Audience Age": df.get("audience_age", pd.Series(["20-35"] * len(df))),
            "Audience Gender": df.get("audience_gender", pd.Series(["Mixed (Tech Audience)"] * len(df))),
            "Audience Geography": df.get("audience_geography", pd.Series(["Global"] * len(df))),
            "Status": df["filter_status"],
            "Audit Reason": df["filter_reason"]
        })
        prefix = "influencer_dataset_full"

    with exp_col_csv:
        st.markdown("**Flat File**")
        st.download_button(
            "📄 CSV (.csv)",
            df_to_csv_str(df_target),
            f"{prefix}.csv",
            "text/csv",
            use_container_width=True
        )

    with exp_col_xlsx:
        st.markdown("**Spreadsheet**")
        st.download_button(
            "📊 Excel (.xlsx)",
            df_to_excel_bytes(df_target),
            f"{prefix}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with exp_col_json:
        st.markdown("**Developer API**")
        st.download_button(
            "🌐 JSON (.json)",
            df_to_json_str(df_target),
            f"{prefix}.json",
            "application/json",
            use_container_width=True
        )

    with exp_col_md:
        st.markdown("**Documentation**")
        st.download_button(
            "📝 Markdown (.md)",
            df_to_markdown_str(df_target),
            f"{prefix}.md",
            "text/markdown",
            use_container_width=True
        )

# ------------------------------------------------------------------------------
# TAB 2: PERSONALIZED MESSAGES
# ------------------------------------------------------------------------------
with tab_messages:
    st.write("")
    qualified_names = df[df["filter_status"] == "PASSED"]["name"].tolist()

    if not qualified_names:
        st.info("No qualified influencers found. Reset to default dataset in sidebar.")
    else:
        sel_creator = st.selectbox("Select a qualified influencer to inspect messages:", qualified_names)
        creator_row = df[df["name"] == sel_creator].iloc[0]

        creator_obj = Influencer(
            name=creator_row["name"],
            platform=creator_row["platform"],
            profile_url=creator_row["profile_url"],
            followers=int(creator_row["followers"]),
            engagement_rate=float(creator_row["engagement_rate"]),
            niche=creator_row["niche"],
            content_themes=creator_row["content_themes"].split(", ") if isinstance(creator_row["content_themes"], str) else [],
            email=creator_row["email"],
            bio_summary=creator_row["bio_summary"],
            recent_content_title=creator_row["recent_content_title"],
            days_since_last_post=int(creator_row["days_since_last_post"])
        )

        # Generate on demand
        pitch = personalizer.generate_pitch(creator_obj)

        col_email, col_dm = st.columns(2)

        with col_email:
            st.markdown(f"""
            <div class="pitch-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h4 style="margin: 0;">Email Collaboration Pitch</h4>
                    <span class="badge-blue">{pitch.email_word_count} words (Limit: 60-90)</span>
                </div>
                <div style="margin-bottom: 8px;"><strong>To:</strong> {pitch.email}</div>
                <div style="margin-bottom: 8px;"><strong>Angle:</strong> {pitch.collaboration_angle}</div>
                <div style="margin-bottom: 12px;"><strong>Subject:</strong> <em>{pitch.email_subject}</em></div>
            </div>
            """, unsafe_allow_html=True)
            st.text_area("Email Body", pitch.email_pitch, height=190, label_visibility="collapsed")

        with col_dm:
            st.markdown(f"""
            <div class="pitch-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h4 style="margin: 0;">Instagram / Social DM</h4>
                    <span class="badge-green">{pitch.dm_word_count} words (Limit: 15-30)</span>
                </div>
                <div style="margin-bottom: 8px; color: #64748B; font-size: 13px;">Natural, peer-to-peer tone for direct messaging:</div>
            </div>
            """, unsafe_allow_html=True)
            st.text_area("DM Copy", pitch.instagram_dm, height=100, label_visibility="collapsed")
            st.caption("💡 Formatted for direct copy/paste or manual dispatch per Instagram anti-spam guidelines.")

# ------------------------------------------------------------------------------
# TAB 3: OUTREACH TRACKER & SENDING
# ------------------------------------------------------------------------------
with tab_sending:
    st.write("")
    s_col1, s_col2 = st.columns([1, 2])

    with s_col1:
        st.markdown("#### **Dispatch Outreach**")
        st.write(f"Mode: **{'🧪 Safe Simulation' if simulation_mode else '🔴 Live SMTP'}**")
        
        batch_size = st.slider("Creators to contact in this batch", 1, 15, 5)

        if st.button("Execute Batch Outreach", type="primary", use_container_width=True):
            dispatcher = OutreachDispatcher(storage=storage, simulation_mode=simulation_mode)
            passed_subset = df[df["filter_status"] == "PASSED"].head(batch_size)
            
            pairs = []
            for _, row in passed_subset.iterrows():
                c_obj = Influencer(
                    name=row["name"],
                    platform=row["platform"],
                    profile_url=row["profile_url"],
                    followers=int(row["followers"]),
                    engagement_rate=float(row["engagement_rate"]),
                    niche=row["niche"],
                    content_themes=row["content_themes"].split(", ") if isinstance(row["content_themes"], str) else [],
                    email=row["email"],
                    bio_summary=row["bio_summary"],
                    recent_content_title=row["recent_content_title"],
                    days_since_last_post=int(row["days_since_last_post"])
                )
                p = personalizer.generate_pitch(c_obj)
                pairs.append((c_obj, p))

            with st.spinner("Dispatching and checking duplicate filters..."):
                results = dispatcher.dispatch_batch(pairs)
                storage.export_to_csv()
            
            st.success(f"Batch processed: {len(results)} creators evaluated.")
            st.rerun()

    with s_col2:
        st.markdown("#### **Outreach Audit Log**")
        logs_fresh = storage.get_all_outreach_logs()
        if logs_fresh:
            df_fresh = pd.DataFrame(logs_fresh)
            st.dataframe(
                df_fresh[["influencer_name", "email", "message_generated", "sent", "date", "status"]],
                use_container_width=True,
                height=260
            )
            col_d1, col_d2, col_d3, col_d4 = st.columns([1, 1, 1, 1])
            with col_d1:
                st.download_button("📄 CSV (.csv)", df_to_csv_str(df_fresh), "outreach_tracker.csv", "text/csv", use_container_width=True)
            with col_d2:
                st.download_button("📊 Excel (.xlsx)", df_to_excel_bytes(df_fresh), "outreach_tracker.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            with col_d3:
                st.download_button("🌐 JSON (.json)", df_to_json_str(df_fresh), "outreach_tracker.json", "application/json", use_container_width=True)
            with col_d4:
                if st.button("🗑️ Clear Log", use_container_width=True):
                    storage.clear_outreach_logs()
                    st.success("Log cleared!")
                    st.rerun()
        else:
            st.info("No outreach dispatched yet. The log is clean. Approve creators in Tab 1 or execute a batch to log delivery.")

    # --------------------------------------------------------------------------
    # LIVE SENDING VERIFICATION TOOLS
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🧪 **Live Delivery Verification & Connectivity Tester**")
    st.caption("Verify whether live SMTP email sending and n8n webhooks are working.")

    test_col1, test_col2 = st.columns(2)

    with test_col1:
        st.markdown("#### **1. Test Live Email Delivery (SMTP)**")
        st.caption("Sends an authentic test email to your personal inbox.")
        test_inbox = st.text_input("Recipient Email", placeholder="e.g. your_email@gmail.com", key="live_test_inbox")

        if st.button("📨 Send Live Test Email", type="primary"):
            if not test_inbox or "@" not in test_inbox:
                st.warning("Please enter a valid email address.")
            else:
                with st.spinner(f"Attempting live SMTP delivery to {test_inbox}..."):
                    dispatcher_live = OutreachDispatcher(storage=storage, simulation_mode=False)
                    res = dispatcher_live.send_email_live(
                        to_email=test_inbox.strip(),
                        subject="DevPulse Outreach Test Email",
                        body="Hello! This is a test email verifying that your live SMTP outreach engine is functioning properly."
                    )
                    # Forward test email event to n8n webhook
                    from dotenv import load_dotenv
                    import requests as req3, os
                    load_dotenv(override=True)
                    webhook_url = os.getenv("N8N_WEBHOOK_URL", "").strip()
                    n8n_note = ""
                    if webhook_url:
                        try:
                            n8n_payload = {
                                "event": "live_smtp_tester",
                                "influencer": f"Test Delivery -> {test_inbox.strip()}",
                                "name": "Live Test Creator",
                                "email": test_inbox.strip(),
                                "followers": 45000,
                                "engagement_rate": 4.2,
                                "niche": "Technology",
                                "recent_content_title": "DevPulse Outreach System Test",
                                "subject": "DevPulse Outreach Test Email",
                                "pitch": "Hello! This is a test email verifying that your live SMTP outreach engine is functioning properly.",
                                "instagram_dm": "Hey! Testing the live delivery workflow.",
                                "angle": "Developer Tool Sponsorship",
                                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "sent": "Yes" if res.get("success") else "No",
                                "status": "SENT" if res.get("success") else "FAILED",
                                "mode": "live_smtp_test"
                            }
                            n_resp = req3.post(webhook_url, json=n8n_payload, timeout=8)
                            if n_resp.status_code == 200:
                                n8n_note = " • ⚡ Forwarded to n8n (HTTP 200)!"
                        except Exception:
                            pass

                    if res.get("success"):
                        st.success(f"✅ Success! Live test email delivered to {test_inbox}{n8n_note}. Please check your inbox.")
                    else:
                        st.error(f"❌ SMTP Sending Error: {res.get('error')}{n8n_note}")
                        st.info("💡 Note: To send live emails with Gmail, generate a 16-character **Google App Password** (myaccount.google.com/apppasswords) and put it into `.env` under `SMTP_PASS`.")

    with test_col2:
        st.markdown("#### **2. Test n8n Automation Webhook**")
        from dotenv import load_dotenv
        import os
        load_dotenv(override=True)
        base_webhook_target = os.getenv("N8N_WEBHOOK_URL", "").strip()

        mode_choice = st.radio(
            "Webhook Target Mode",
            ["Production Webhook (/webhook/)", "Canvas Test Listener (/webhook-test/)"],
            index=0,
            horizontal=True,
            help="Choose Production to test the active background workflow, or Canvas Test to test while 'Listen for test event' is active in n8n."
        )

        if "Canvas Test" in mode_choice:
            webhook_target = base_webhook_target.replace("/webhook/", "/webhook-test/")
        else:
            webhook_target = base_webhook_target.replace("/webhook-test/", "/webhook/")

        st.caption(f"Target URL: `{webhook_target or 'Not Configured'}`")

        if st.button("⚡ Ping n8n Webhook"):
            if not webhook_target:
                st.warning("No N8N_WEBHOOK_URL found in .env.")
            else:
                with st.spinner("Pinging webhook..."):
                    import requests
                    try:
                        resp = requests.post(webhook_target, json={
                            "event": "manual_ping",
                            "influencer": "DevPulse Test Creator",
                            "name": "DevPulse Test Creator",
                            "email": "test@devpulse.io",
                            "followers": 45000,
                            "engagement_rate": 3.8,
                            "niche": "Technology",
                            "recent_content_title": "Building AI Systems in 2026",
                            "subject": "DevPulse Collaboration Opportunity",
                            "email_subject": "DevPulse Collaboration Opportunity",
                            "pitch": "Hi! We would love to collaborate on an upcoming technical video showcasing DevPulse.",
                            "instagram_dm": "Hey! Loved your recent video. Open to a quick chat about DevPulse?",
                            "status": "PING_TEST",
                            "message": "Testing webhook integration from DevPulse Outreach System",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }, timeout=8)

                        if resp.status_code == 200:
                            st.success(f"✅ n8n responded HTTP 200 OK: `{resp.text}`")
                            if "Canvas Test" in mode_choice:
                                st.info("🎉 The data was sent to the Canvas Test listener! Check your n8n canvas—the Webhook node should now be green with the received data.")
                            else:
                                st.info("ℹ️ **Where to see this in n8n:** Because your workflow is **Active**, production executions run in the background. In n8n, click **'Executions'** (clock/history icon on the left sidebar) to view this run and all received data.")
                        elif resp.status_code == 404:
                            st.warning(f"⚠️ Webhook responded with HTTP 404: `{resp.text}`")
                            if "Canvas Test" in mode_choice:
                                st.info("💡 In n8n, open the Webhook node and click **'Listen for test event'** first, then click this Ping button.")
                            else:
                                st.info("💡 In n8n, ensure the workflow is toggled to **'Active'** (top right switch).")
                        else:
                            st.info(f"Webhook responded with HTTP status {resp.status_code}: {resp.text}")
                    except Exception as e:
                        st.error(f"Webhook connection error: {e}")

