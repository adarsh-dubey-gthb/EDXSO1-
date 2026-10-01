"""
Command-Line Interface (CLI) Pipeline Runner.
Executes the end-to-end Automated Micro-Influencer Outreach System:
1. Discovery (50+ real technology micro-influencers)
2. Filtering & Classification (with strict criteria & audit trail)
3. Profile Enrichment (email verification, themes, metadata)
4. AI Personalization (60-90w email pitches & 15-30w social DMs)
5. Sending Layer (safe simulation/SMTP with deduplication)
6. Tracking & CSV Export (influencer_dataset.csv & outreach_tracker.csv)
"""

import sys
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track

from config import DEFAULT_NICHE
from discovery.youtube_crawler import InfluencerDiscoveryEngine
from filtering.classifier import InfluencerClassifier
from enrichment.extractor import ProfileEnrichmentEngine
from personalization.generator import MessagePersonalizer
from personalization.langchain_agent import LangChainMailAgent
from sending.dispatcher import OutreachDispatcher
from storage.tracker import OutreachStorage
from models import Influencer

# Configure logging and console encoding
import io
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
console = Console(highlight=False)


def run_pipeline(simulation_mode: bool = True, target_count: int = 55, search_query: str = ""):
    """
    Executes the entire influencer outreach pipeline step by step.
    Supports both curated 55+ database and live on-demand web search.
    """
    console.print(Panel.fit(
        "[bold cyan]Automated Micro-Influencer Outreach System[/bold cyan]\n"
        "[dim]EDXSO AI Engineer Intern - Assignment 1 Prototype[/dim]",
        border_style="cyan"
    ))

    storage = OutreachStorage()
    discovery_engine = InfluencerDiscoveryEngine()
    classifier = InfluencerClassifier()
    enricher = ProfileEnrichmentEngine()
    personalizer = MessagePersonalizer()
    dispatcher = OutreachDispatcher(storage=storage, simulation_mode=simulation_mode)

    # --------------------------------------------------------------------------
    # STAGE 1: INFLUENCER DISCOVERY
    # --------------------------------------------------------------------------
    if search_query:
        console.print(f"\n[bold yellow]Step 1: Real-time Live Discovery for '{search_query}' (Free Web Scraper)...[/bold yellow]")
        influencers = discovery_engine.discover_live_search(query=search_query, limit=10, niche=DEFAULT_NICHE)
    else:
        console.print("\n[bold yellow]Step 1: Discovering Influencers (Niche: Technology)...[/bold yellow]")
        influencers = discovery_engine.discover(target_niche=DEFAULT_NICHE, limit=target_count)
    console.print(f"[green][OK] Discovered {len(influencers)} influencer profiles.[/green]")

    # --------------------------------------------------------------------------
    # STAGE 2: FILTERING & CLASSIFICATION
    # --------------------------------------------------------------------------
    console.print("\n[bold yellow]Step 2: Filtering and Classification Engine...[/bold yellow]")
    passed_candidates, failed_candidates = classifier.filter_batch(influencers)
    
    console.print(f"  • Passed criteria: [bold green]{len(passed_candidates)}[/bold green]")
    console.print(f"  • Disqualified:    [bold red]{len(failed_candidates)}[/bold red]")

    # Persist all discovered influencers with their audit reasons
    storage.save_influencers(influencers)

    # Display sample filtered results table
    filter_table = Table(title="Influencer Filtering Audit (Sample Results)", border_style="dim")
    filter_table.add_column("Influencer", style="cyan", no_wrap=True)
    filter_table.add_column("Followers", justify="right")
    filter_table.add_column("Engagement", justify="right")
    filter_table.add_column("Status", style="bold")
    filter_table.add_column("Reason / Audit Trail", max_width=45)

    for inf in (passed_candidates[:3] + failed_candidates[:3]):
        status_color = "green" if inf.filter_status == "PASSED" else "red"
        filter_table.add_row(
            inf.name,
            f"{inf.followers:,}",
            f"{inf.engagement_rate:.1f}%",
            f"[{status_color}]{inf.filter_status}[/{status_color}]",
            inf.filter_reason
        )
    console.print(filter_table)

    # --------------------------------------------------------------------------
    # STAGE 3: PROFILE ENRICHMENT
    # --------------------------------------------------------------------------
    console.print("\n[bold yellow]Step 3: Profile Enrichment & Contact Extraction...[/bold yellow]")
    enriched_candidates = enricher.enrich_batch(passed_candidates)
    valid_email_count = sum(1 for inf in enriched_candidates if inf.email != "Not Found")
    missing_email_count = len(enriched_candidates) - valid_email_count

    console.print(f"[green][OK] Profiles enriched.[/green] Found verified emails: [bold green]{valid_email_count}[/bold green] | Not Found: [bold yellow]{missing_email_count}[/bold yellow]")

    # --------------------------------------------------------------------------
    # STAGE 4: AI PERSONALIZATION (EMAIL & INSTAGRAM DM)
    # --------------------------------------------------------------------------
    console.print("\n[bold yellow]Step 4: AI Personalization Engine (Email: 60-90w, DM: 15-30w)...[/bold yellow]")
    pairs = []
    
    # Process shortlisted candidates
    sample_to_generate = enriched_candidates[:10]  # Generate high quality messages for top shortlisted
    for inf in track(sample_to_generate, description="Generating personalized pitches..."):
        pitch = personalizer.generate_pitch(inf)
        pairs.append((inf, pitch))

    # Display sample pitch
    if pairs:
        sample_inf, sample_pitch = pairs[0]
        console.print(Panel(
            f"[bold]Target Creator:[/bold] {sample_inf.name} ({sample_inf.email})\n"
            f"[bold]Angle:[/bold] {sample_pitch.collaboration_angle}\n\n"
            f"[bold cyan]Generated Email Pitch ({sample_pitch.email_word_count} words):[/bold cyan]\n"
            f"[dim]Subject: {sample_pitch.email_subject}[/dim]\n"
            f"{sample_pitch.email_pitch}\n\n"
            f"[bold magenta]Generated Social DM ({sample_pitch.dm_word_count} words):[/bold magenta]\n"
            f"{sample_pitch.instagram_dm}",
            title=f"Sample AI Generated Outreach for {sample_inf.name}",
            border_style="green"
        ))

    # --------------------------------------------------------------------------
    # STAGE 5: SENDING LAYER & TRACKING
    # --------------------------------------------------------------------------
    console.print(f"\n[bold yellow]Step 5: Sending Layer Dispatch (Simulation Mode = {simulation_mode})...[/bold yellow]")
    records = dispatcher.dispatch_batch(pairs)

    sent_count = sum(1 for r in records if r.sent in ["Yes", "Simulated"])
    skipped_count = sum(1 for r in records if r.status == "SKIPPED_NO_EMAIL")
    dupes_count = sum(1 for r in records if r.status == "DUPLICATE_PREVENTED")

    console.print(f"[green][OK] Outreach executed.[/green] Dispatched: [bold green]{sent_count}[/bold green] | Skipped (No email): [bold yellow]{skipped_count}[/bold yellow] | Duplicates Prevented: [bold cyan]{dupes_count}[/bold cyan]")

    # --------------------------------------------------------------------------
    # STAGE 6: DATA EXPORT
    # --------------------------------------------------------------------------
    console.print("\n[bold yellow]Step 6: Exporting Deliverable CSV Datasets...[/bold yellow]")
    exported_files = storage.export_to_csv()
    console.print(f"[green][OK] Influencer Dataset saved to: {exported_files['dataset_csv']}[/green]")
    console.print(f"[green][OK] Outreach Tracker saved to:   {exported_files['tracker_csv']}[/green]")

    console.print("\n[bold green]Pipeline execution completed successfully![/bold green]\n")


def run_agent_hitl_pipeline(search_query: str = "", simulation_mode: bool = True, auto_approve: bool = False):
    """
    Executes the user's automated LangChain workflow:
    1. Search/Discover creators.
    2. Automated criteria filtering.
    3. LangChain Mail Agent selects and generates tailored pitches for the Top 5 creators.
    4. Enters Human-in-the-Loop review stage (approve, edit, or reject before dispatch).
    5. Dispatches approved pitches, prevents duplicates, and logs to database/tracker.
    """
    console.print(Panel.fit(
        "[bold cyan]LangChain Automated Mail Agent with Human-in-the-Loop (HITL)[/bold cyan]\n"
        "[dim]1. Search Creators ➔ 2. Auto-Filter ➔ 3. Mail Agent Top 5 ➔ 4. Human-in-the-Loop Review[/dim]",
        border_style="cyan"
    ))

    storage = OutreachStorage()
    discovery_engine = InfluencerDiscoveryEngine()
    classifier = InfluencerClassifier()
    enricher = ProfileEnrichmentEngine()
    mail_agent = LangChainMailAgent()
    dispatcher = OutreachDispatcher(storage=storage, simulation_mode=simulation_mode)

    # 1. Search / Discover
    query_clean = search_query.strip().lower()
    matching_pool = []

    # Get verified pool
    all_raw = storage.get_all_influencers()
    if not all_raw:
        initial = discovery_engine.discover(target_niche=DEFAULT_NICHE, limit=55)
        classifier.filter_batch(initial)
        enricher.enrich_batch(initial)
        storage.save_influencers(initial)
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

    if query_clean:
        console.print(f"\n[bold yellow]Step 1: Searching Creators for '{search_query}'...[/bold yellow]")
        for inf in all_qualified:
            themes_str = " ".join(inf.content_themes).lower()
            if (query_clean in inf.name.lower() or 
                query_clean in themes_str or 
                query_clean in inf.niche.lower() or 
                (inf.recent_content_title and query_clean in inf.recent_content_title.lower())):
                matching_pool.append(inf)

        # Also live scrape
        discovered = discovery_engine.discover_live_search(query=search_query, limit=8, niche=DEFAULT_NICHE)
        if discovered:
            passed_live, failed_live = classifier.filter_batch(discovered)
            enricher.enrich_batch(passed_live)
            storage.save_influencers(discovered)
            matching_pool.extend(passed_live)

        candidates = matching_pool if matching_pool else all_qualified
        console.print(f"[green][OK] Matched {len(candidates)} qualified micro-influencers.[/green]")
    else:
        console.print("\n[bold yellow]Step 1: Fetching Curated Technology Creators...[/bold yellow]")
        candidates = all_qualified
        console.print(f"[green][OK] Selected {len(candidates)} qualified creators.[/green]")

    if not candidates:
        console.print("[red]No creators met the qualification criteria.[/red]")
        return

    passed = candidates

    # 3. LangChain Mail Agent for Top 5
    console.print("\n[bold yellow]Step 3: LangChain Mail Agent selecting Top 5 & drafting LCEL pitches...[/bold yellow]")
    drafts = mail_agent.run_mail_agent_for_top_5(passed)
    console.print(f"[bold green][OK] LangChain Mail Agent generated tailored outreach for Top {len(drafts)} creators.[/bold green]")

    # 4. Human-in-the-Loop Review Stage
    console.print("\n" + "="*70)
    console.print("[bold magenta]🧑‍💻 HUMAN-IN-THE-LOOP (HITL) REVIEW STAGE[/bold magenta]")
    console.print("="*70)

    approved_pairs = []
    for idx, (creator, pitch) in enumerate(drafts, 1):
        console.print(Panel(
            f"[bold]Creator #{idx}:[/bold] [cyan]{creator.name}[/cyan] ({creator.followers:,} subs, {creator.engagement_rate:.1f}% eng)\n"
            f"[bold]Contact Email:[/bold] [yellow]{creator.email}[/yellow]\n"
            f"[bold]Recent Content:[/bold] {creator.recent_content_title or 'Tech Tutorial'}\n"
            f"[bold]Angle:[/bold] {pitch.collaboration_angle}\n\n"
            f"[bold green]Drafted Email ({pitch.email_word_count} words, target: 60-90w):[/bold green]\n"
            f"[dim]Subject: {pitch.email_subject}[/dim]\n"
            f"{pitch.email_pitch}\n\n"
            f"[bold blue]Drafted Social DM ({pitch.dm_word_count} words, target: 15-30w):[/bold blue]\n"
            f"{pitch.instagram_dm}",
            title=f"Review Draft for {creator.name}",
            border_style="magenta"
        ))

        if auto_approve:
            console.print(f"[green]Auto-approved dispatch for {creator.name}.[/green]")
            approved_pairs.append((creator, pitch))
        else:
            try:
                choice = input(f"Approve dispatch for {creator.name}? [Y/n/all/skip]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "y"
            
            if choice in ["", "y", "yes"]:
                approved_pairs.append((creator, pitch))
                console.print(f"[green]Approved {creator.name}.[/green]")
            elif choice == "all":
                approved_pairs.append((creator, pitch))
                # Add remainder
                for remaining_c, remaining_p in drafts[idx:]:
                    approved_pairs.append((remaining_c, remaining_p))
                console.print("[green]Approved all remaining creators.[/green]")
                break
            else:
                console.print(f"[yellow]Skipped {creator.name}.[/yellow]")

    # 5. Dispatch Approved
    console.print(f"\n[bold yellow]Step 5: Dispatching {len(approved_pairs)} Approved Pitches (Mode: {'Simulated' if simulation_mode else 'Live SMTP'})...[/bold yellow]")
    if approved_pairs:
        results = dispatcher.dispatch_batch(approved_pairs)
        storage.export_to_csv()
        sent = sum(1 for r in results if r.sent in ["Yes", "Simulated"])
        dupes = sum(1 for r in results if r.status == "DUPLICATE_PREVENTED")
        console.print(f"[green][OK] Outreach completed! Sent/Simulated: {sent} | Duplicates Blocked: {dupes}[/green]")
    else:
        console.print("[yellow]No pitches were approved for dispatch.[/yellow]")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Automated Micro-Influencer Outreach System CLI")
    parser.add_argument("--agent", action="store_true", help="Run the LangChain Top-5 Mail Agent with Human-in-the-Loop review")
    parser.add_argument("--search", type=str, default="", help="Perform a real-time live search on YouTube")
    parser.add_argument("--live", action="store_true", help="Enable live SMTP delivery (default: simulation mode)")
    parser.add_argument("--limit", type=int, default=55, help="Number of influencers to process")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve all Top 5 in HITL mode without prompting")
    
    args = parser.parse_args()
    if args.agent:
        run_agent_hitl_pipeline(search_query=args.search, simulation_mode=not args.live, auto_approve=args.auto_approve)
    else:
        run_pipeline(simulation_mode=not args.live, target_count=args.limit, search_query=args.search)

