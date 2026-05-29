import os
import re
import json
import anthropic
import smtplib
from datetime import datetime, timedelta  # ← CHANGED: added timedelta
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import urllib.request
import urllib.parse

load_dotenv()

client = anthropic.Anthropic()

# ─────────────────────────────────────────────
# Adam's background — used for scoring each job
# ─────────────────────────────────────────────
MY_BACKGROUND = """
Name: Adam Haywood
Location: Raleigh-Durham, NC (open to remote, hybrid, or on-site in RDU area)
Target Roles: Senior Engineering Manager, Director of Engineering, VP Engineering,
              Director of AI/ML, Head of Engineering, AI Product Director

SUMMARY:
Senior Engineering Manager with 25+ years leading global R&D, Quality Engineering,
and Interoperability organizations. Track record supporting $94.5M in quarterly
revenue through accelerated partner/customer readiness. Experienced in scaling
high-impact teams, Capex/Opex planning, AI/ML automation initiatives.

KEY STRENGTHS:
- Global team leadership (10 FTEs + 18 contingent resources)
- AI/ML automation and multi-agent systems
- Enterprise storage/infrastructure (NetApp ONTAP, SAN/NAS)
- Quality Engineering and Interoperability at scale
- Budget ownership, SOW negotiation, vendor management
- Cross-functional collaboration with Product, R&D, Sales

AI LEADERSHIP & HANDS-ON PRACTICE:
I work directly with AI tools daily — including Claude API and LLM-driven
workflows — and have led teams building multi-agent automation systems.
I understand the technology well enough to direct it strategically and
translate it for both engineers and executives.

SENIORITY: Senior Manager → Director level preferred
INDUSTRY FIT: Enterprise tech, cloud infrastructure, AI/ML, storage, networking
NOT A FIT: Pure IC engineering roles, sales, finance, non-tech management
"""

# Minimum match score to include in digest (0-100)
SCORE_THRESHOLD = 60

# Gmail sender addresses LinkedIn uses
LINKEDIN_SENDERS = [
    "jobalerts-noreply@linkedin.com",
    "jobs-noreply@linkedin.com",
    "messages-noreply@linkedin.com",
]


def fetch_linkedin_emails():
    """Fetch unread LinkedIn job alert emails from Gmail via Anthropic API + Gmail MCP."""
    print("📬 Fetching LinkedIn job alert emails from Gmail...")

    query_parts = " OR ".join([f"from:{s}" for s in LINKEDIN_SENDERS])
    search_query = f"({query_parts}) is:unread newer_than:2d"

    # Use Anthropic API with Gmail MCP to search and read emails
    response = client.beta.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        tools=[{
            "type": "computer_use_20250124",
            "name": "computer"
        }],
        betas=["computer-use-2024-10-22"],
        mcp_servers=[{
            "type": "url",
            "url": "https://gmailmcp.googleapis.com/mcp/v1",
            "name": "gmail-mcp"
        }],
        system="""You are a Gmail assistant. Search for LinkedIn job alert emails 
using the Gmail MCP tools and return ALL job listings found as a JSON array.

For each job listing extract:
- title: job title
- company: company name  
- location: job location
- link: the LinkedIn job URL (starts with https://www.linkedin.com)
- email_id: the Gmail message ID

Return ONLY a JSON array with no other text. Example:
[{"title":"Engineering Manager","company":"Acme","location":"Durham, NC",
  "link":"https://linkedin.com/jobs/view/123","email_id":"abc123"}]""",
        messages=[{
            "role": "user",
            "content": f"Search Gmail for: {search_query}\n\nRead each email found and extract all job listings. Return as JSON array."
        }]
    )

    # Parse response
    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text += block.text

    try:
        # Find JSON array in response
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            jobs = json.loads(match.group())
            print(f"  Found {len(jobs)} job listings")
            return jobs
    except Exception as e:
        print(f"  ⚠️  Could not parse job listings: {e}")

    return []


def fetch_emails_direct():
    """
    Fallback: directly call Gmail API via Anthropic MCP client.
    Reads unread LinkedIn emails and extracts job listings from plaintext body.
    """
    print("📬 Reading LinkedIn emails from Gmail...")

    # Read the stored emails we already found
    jobs = []

    # Parse email body for job listings
    def parse_jobs_from_body(body, email_id):
        found = []
        # Split on separator lines
        sections = re.split(r'-{10,}', body)
        for section in sections:
            lines = [l.strip() for l in section.strip().splitlines() if l.strip()]
            if not lines:
                continue

            # Look for job title + company + location pattern
            title, company, location, link = None, None, None, None
            for i, line in enumerate(lines):
                # Skip tracking/utility lines
                if any(x in line.lower() for x in ['manage your', 'connections', 'view job', 'http', 'unsubscribe']):
                    continue
                if not title and len(line) > 5 and not line.startswith('http'):
                    title = line
                elif title and not company and len(line) > 2 and not line.startswith('http'):
                    company = line
                elif company and not location and len(line) > 2 and not line.startswith('http') and (',' in line or any(s in line for s in ['NC', 'NY', 'CA', 'TX', 'Remote', 'Hybrid'])):
                    location = line

            # Find LinkedIn job URL
            url_match = re.search(r'https://www\.linkedin\.com/comm/jobs/view/(\d+)', section)
            if url_match:
                job_id = url_match.group(1)
                link = f"https://www.linkedin.com/jobs/view/{job_id}/"

            if title and company and link:
                found.append({
                    "title": title,
                    "company": company,
                    "location": location or "See listing",
                    "link": link,
                    "email_id": email_id
                })
        return found

    # We'll use the email body we already fetched
    sample_body = """Your job alert for System Engineer in Raleigh

Senior Systems Software Engineer
Hewlett Packard Enterprise
Durham, NC

8 connections
View job: https://www.linkedin.com/comm/jobs/view/4420688494/

---------------------------------------------------------

Software Engineer (Performance)
NetApp
Morrisville, NC

47 connections
View job: https://www.linkedin.com/comm/jobs/view/4412010590/

---------------------------------------------------------

Business Systems Engineer
Vulcan Elements
Durham, NC
View job: https://www.linkedin.com/comm/jobs/view/4408114491/"""

    parsed = parse_jobs_from_body(sample_body, "19e73e98aeacccf8")
    jobs.extend(parsed)

    return jobs, parse_jobs_from_body


def parse_email_body(body, email_id):
    """Extract job listings from a LinkedIn alert email body."""
    jobs = []
    sections = re.split(r'-{10,}', body)

    for section in sections:
        lines = [l.strip() for l in section.strip().splitlines() if l.strip()]
        if not lines:
            continue

        title, company, location, link = None, None, None, None

        for line in lines:
            if any(x in line.lower() for x in
                   ['manage your', 'connections', 'view job',
                    'unsubscribe', 'linkedin.com/comm', 'midtoken']):
                continue
            if line.startswith('http'):
                continue

            if not title and len(line) > 5:
                title = line
            elif title and not company and len(line) > 2:
                company = line
            elif company and not location and (
                ',' in line or
                any(s in line for s in ['NC', 'NY', 'CA', 'TX', 'Remote', 'Hybrid', 'United States'])
            ):
                location = line

        # Extract clean LinkedIn job URL
        url_match = re.search(
            r'https://www\.linkedin\.com/comm/jobs/view/(\d+)', section)
        if url_match:
            link = f"https://www.linkedin.com/jobs/view/{url_match.group(1)}/"

        if title and company and link:
            jobs.append({
                "title":    title,
                "company":  company,
                "location": location or "See listing",
                "link":     link,
                "email_id": email_id
            })

    return jobs


def score_job(job):
    """Send a job to Claude for scoring against Adam's background."""
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        system="""You are a career matching specialist. Score a job listing against 
a candidate's background and return ONLY a JSON object with no other text.

Scoring criteria (each 0-25 points):
1. title_fit: How well does the job title match target seniority and role type?
2. skill_match: How well do required skills match the candidate's experience?
3. seniority_level: Is this the right level (Sr Manager/Director/VP)?
4. industry_fit: Is this the right industry/domain?

Also include:
- total: sum of all four scores (0-100)
- why_good: 1-2 sentences on strongest match points (be specific)
- concerns: 1 sentence on any gaps or concerns (or "None" if strong match)
- recommendation: one of "Strong Match", "Good Match", "Weak Match", "Skip"

Return ONLY valid JSON. Example:
{"title_fit":22,"skill_match":20,"seniority_level":25,"industry_fit":18,
 "total":85,"why_good":"Director-level role at enterprise tech company aligns with NetApp background and team leadership experience.",
 "concerns":"Role focuses more on hardware than AI/ML.",
 "recommendation":"Strong Match"}""",
        messages=[{
            "role": "user",
            "content": (
                f"CANDIDATE BACKGROUND:\n{MY_BACKGROUND}\n\n"
                f"JOB LISTING:\n"
                f"Title: {job['title']}\n"
                f"Company: {job['company']}\n"
                f"Location: {job['location']}\n"
            )
        }]
    )

    text = response.content[0].text.strip()
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass

    return {
        "title_fit": 0, "skill_match": 0,
        "seniority_level": 0, "industry_fit": 0,
        "total": 0, "why_good": "Could not score",
        "concerns": "Scoring error", "recommendation": "Skip"
    }


def score_color(score):
    if score >= 80:
        return "#16a34a"  # green
    elif score >= 60:
        return "#d97706"  # amber
    return "#dc2626"      # red


def rec_badge_color(rec):
    colors = {
        "Strong Match": ("#dcfce7", "#166534"),
        "Good Match":   ("#fef9c3", "#854d0e"),
        "Weak Match":   ("#fee2e2", "#991b1b"),
        "Skip":         ("#f3f4f6", "#6b7280"),
    }
    return colors.get(rec, ("#f3f4f6", "#6b7280"))


def build_job_card(job, scoring):
    total     = scoring.get("total", 0)
    rec       = scoring.get("recommendation", "Skip")
    why       = scoring.get("why_good", "")
    concerns  = scoring.get("concerns", "")
    bg, fg    = rec_badge_color(rec)
    clr       = score_color(total)

    score_breakdown = (
        f"Title Fit: {scoring.get('title_fit',0)}/25 &nbsp;|&nbsp; "
        f"Skills: {scoring.get('skill_match',0)}/25 &nbsp;|&nbsp; "
        f"Seniority: {scoring.get('seniority_level',0)}/25 &nbsp;|&nbsp; "
        f"Industry: {scoring.get('industry_fit',0)}/25"
    )

    concerns_html = (
        f'<div style="font-size:12px;color:#6b7280;margin-top:4px;">⚠️ {concerns}</div>'
        if concerns and concerns.lower() != "none" else ""
    )

    return f"""
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;
                padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.06);">
        <div style="display:flex;justify-content:space-between;
                    align-items:flex-start;flex-wrap:wrap;gap:8px;">
            <div style="flex:1;">
                <div style="font-size:17px;font-weight:700;color:#111;">
                    {job['title']}</div>
                <div style="font-size:14px;color:#374151;margin-top:2px;">
                    {job['company']}
                    <span style="color:#9ca3af;margin:0 6px;">·</span>
                    {job['location']}</div>
            </div>
            <div style="text-align:right;flex-shrink:0;">
                <div style="font-size:28px;font-weight:700;color:{clr};">{total}</div>
                <div style="font-size:11px;color:#9ca3af;">/ 100</div>
            </div>
        </div>

        <div style="margin:10px 0;">
            <span style="background:{bg};color:{fg};font-size:12px;font-weight:600;
                         padding:3px 10px;border-radius:20px;">{rec}</span>
        </div>

        <div style="font-size:11px;color:#9ca3af;margin:8px 0 4px;">{score_breakdown}</div>

        <div style="font-size:13px;color:#374151;margin-top:8px;line-height:1.6;">
            ✅ {why}</div>
        {concerns_html}

        <div style="margin-top:14px;">
            <a href="{job['link']}"
               style="background:#2563eb;color:#fff;text-decoration:none;
                      font-size:13px;font-weight:600;padding:8px 18px;
                      border-radius:6px;display:inline-block;">
                View on LinkedIn →
            </a>
        </div>
    </div>"""


def build_html_digest(scored_jobs, all_count):
    date_str   = datetime.now().strftime("%A, %B %d, %Y")
    shown      = len(scored_jobs)
    skipped    = all_count - shown
    cards_html = "\n".join([build_job_card(j, s) for j, s in scored_jobs])

    strong = sum(1 for _, s in scored_jobs if s.get("recommendation") == "Strong Match")
    good   = sum(1 for _, s in scored_jobs if s.get("recommendation") == "Good Match")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<div style="max-width:680px;margin:0 auto;padding:24px 16px;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1e3a5f,#0f766e);
                border-radius:12px;padding:24px;margin-bottom:24px;color:#fff;">
        <div style="font-size:22px;font-weight:700;">💼 LinkedIn Job Digest</div>
        <div style="font-size:14px;opacity:.8;margin-top:4px;">{date_str}</div>
        <div style="font-size:13px;opacity:.7;margin-top:2px;">Adam Haywood · AI-filtered opportunities</div>
    </div>

    <!-- Summary -->
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;
                padding:20px;margin-bottom:24px;">
        <div style="font-size:13px;font-weight:600;color:#6b7280;
                    text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px;">
            Today's Summary
        </div>
        <div style="display:flex;gap:32px;flex-wrap:wrap;">
            <div>
                <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;">Total Scanned</div>
                <div style="font-size:24px;font-weight:700;color:#111;">{all_count}</div>
            </div>
            <div>
                <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;">Matches Shown</div>
                <div style="font-size:24px;font-weight:700;color:#2563eb;">{shown}</div>
            </div>
            <div>
                <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;">Strong Match</div>
                <div style="font-size:24px;font-weight:700;color:#16a34a;">{strong}</div>
            </div>
            <div>
                <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;">Good Match</div>
                <div style="font-size:24px;font-weight:700;color:#d97706;">{good}</div>
            </div>
            <div>
                <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;">Filtered Out</div>
                <div style="font-size:24px;font-weight:700;color:#9ca3af;">{skipped}</div>
            </div>
        </div>
        <div style="font-size:12px;color:#9ca3af;margin-top:12px;">
            Showing jobs scoring {SCORE_THRESHOLD}+ out of 100 · 
            Scored against your Senior EM/Director profile
        </div>
    </div>

    <!-- Job Cards -->
    <div style="font-size:13px;font-weight:600;color:#6b7280;
                text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px;">
        Top Matches — Ranked by Score
    </div>
    {cards_html}

    <!-- Footer -->
    <div style="text-align:center;font-size:12px;color:#9ca3af;
                margin-top:24px;padding:16px;">
        Generated by Job Alert Agent · Scored by Claude AI<br>
        Adjust scoring threshold in job_alert_agent.py → SCORE_THRESHOLD
    </div>
</div>
</body>
</html>"""


def send_digest(html_content, job_count):
    gmail_address  = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_password:
        print("  ⚠️  Gmail credentials not in .env — skipping email")
        return

    print("\n📧 Sending job digest to Gmail...")
    msg            = MIMEMultipart("alternative")
    msg["Subject"] = (f"💼 Job Digest — {job_count} matches · "
                      f"{datetime.now().strftime('%b %d, %Y')}")
    msg["From"]    = gmail_address
    msg["To"]      = gmail_address

    plain = f"LinkedIn Job Digest — {datetime.now().strftime('%B %d, %Y')}\n{job_count} matches found. Open HTML version to view details."
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, gmail_address, msg.as_string())
        print("  ✅ Job digest sent to Gmail")
    except Exception as e:
        print(f"  ⚠️  Email failed: {e}")


def main():
    print(f"\n💼 LinkedIn Job Alert Agent — Adam Haywood")
    print(f"   {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}\n")

    # ── Step 1: Get LinkedIn emails from Gmail
    # We use the Gmail MCP via the Anthropic API
    # For the standalone script we read directly via requests
    # using the stored token from the MCP connection
    gmail_address  = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    # Use IMAP to read Gmail (works alongside SMTP we already use)
    import imaplib
    import email as email_lib
    from email.header import decode_header

    print("📬 Connecting to Gmail via IMAP...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_address, gmail_password)
        mail.select("inbox")
    except Exception as e:
        print(f"  ❌ Gmail IMAP connection failed: {e}")
        print("  Make sure IMAP is enabled in Gmail Settings → See all settings → Forwarding and POP/IMAP")
        return

    # Search for unread LinkedIn emails from last 2 days
    all_jobs = []
    processed_ids = []

    # ↓ CHANGED: search last 7 days instead of UNSEEN only
    since_str = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")

    for sender in LINKEDIN_SENDERS:
        _, msg_nums = mail.search(None, f'(FROM "{sender}" SINCE "{since_str}")')
        ids = msg_nums[0].split()
        print(f"  Found {len(ids)} emails from {sender} since {since_str}")

        for num in ids:
            _, msg_data = mail.fetch(num, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)

            # Get plain text body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            email_id = num.decode()
            jobs = parse_email_body(body, email_id)
            all_jobs.extend(jobs)
            processed_ids.append(num)

    mail.logout()

    if not all_jobs:
        print("\n  No new LinkedIn job alerts found. Check back tomorrow!")
        return

    # Deduplicate by link
    seen_links = set()
    unique_jobs = []
    for job in all_jobs:
        if job["link"] not in seen_links:
            seen_links.add(job["link"])
            unique_jobs.append(job)

    print(f"\n📋 Found {len(unique_jobs)} unique job listings — scoring each...\n")

    # ── Step 2: Score each job with Claude
    scored = []
    for i, job in enumerate(unique_jobs, 1):
        print(f"  [{i}/{len(unique_jobs)}] Scoring: {job['title']} at {job['company']}...",
              end="", flush=True)
        scoring = score_job(job)
        total   = scoring.get("total", 0)
        rec     = scoring.get("recommendation", "Skip")
        print(f" {total}/100 — {rec}")

        if total >= SCORE_THRESHOLD:
            scored.append((job, scoring))

    # Sort by score descending
    scored.sort(key=lambda x: x[1].get("total", 0), reverse=True)

    print(f"\n✅ {len(scored)} jobs above threshold ({SCORE_THRESHOLD}+) "
          f"out of {len(unique_jobs)} total\n")

    if not scored:
        print("  No jobs met the score threshold today.")
        return

    # ── Step 3: Build and send HTML digest
    html = build_html_digest(scored, len(unique_jobs))
    send_digest(html, len(scored))

    # ── Step 4: Save digest
    os.makedirs("job_digests", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"job_digests/digest_{timestamp}.html", "w") as f:
        f.write(html)
    print(f"💾 Digest saved to job_digests/digest_{timestamp}.html")

    # ── Step 5: Print summary to terminal
    print(f"\n{'='*60}")
    print(f"  TOP MATCHES")
    print(f"{'='*60}")
    for job, s in scored[:5]:
        print(f"  {s['total']:3d}/100  {job['title']} at {job['company']}")
        print(f"          {job['location']}")
        print(f"          {s['recommendation']} — {s['why_good'][:70]}")
        print()


if __name__ == "__main__":
    main()
