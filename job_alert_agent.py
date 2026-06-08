import os
import re
import json
import anthropic
import smtplib
from datetime import datetime, timedelta
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

load_dotenv()

client = anthropic.Anthropic()

# ─────────────────────────────────────────────
# Adam's background — used for scoring each job
# ─────────────────────────────────────────────
MY_BACKGROUND = """
Name: Adam Haywood
Location: Raleigh-Durham, NC (open to remote, hybrid, or on-site in RDU area)
Target Roles: Senior Engineering Manager, Director of Engineering, Quality Engineering Manager, Quality Assurance Manager 

SUMMARY:
Engineering leader with 25+ years of experience owning end-to-end software delivery, platform strategy, and
engineering team development across complex, enterprise-scale environments. Proven track record defining
technical roadmaps aligned to business outcomes - including enabling $94.5M in quarterly revenue through
disciplined delivery execution and accelerated partner readiness. Experienced building and scaling high-performing
engineering organizations, operationalizing AI-driven automation, and establishing SDLC governance, quality
standards, and CI/CD practices that improve release velocity and platform stability. Brings deep credibility in
distributed systems, cross-functional alignment, and change leadership - with a hands-on approach to both people
and craft.

KEY STRENGTHS:
- Engineering Strategy & Technical Roadmap Ownership
- Software Delivery Lifecycle (SDLC) Governance
- CI/CD Adoption & Engineering Excellence
- RESTful APIs, Distributed Systems & Platform Architecture
- Production Incident Management & Operational Stability
- Engineering Talent Strategy, Coaching & Career Development
- Capex/Opex Planning & Vendor Governance
- AI/ML-Enabled Automation & Modern Engineering Practices
- Cross-Functional Leadership: Product, Program, Architectire
- Stakeholder Communication & Delivery Transparency

# Global team leadership (10 FTEs + 18 contingent resources)
# AI/ML automation and multi-agent systems
# Enterprise storage/infrastructure (NetApp ONTAP, SAN/NAS)
# Quality Engineering and Interoperability at scale
# Budget ownership, SOW negotiation, vendor management
# Cross-functional collaboration with Product, R&D, Sales

AI LEADERSHIP & HANDS-ON PRACTICE:
I work directly with AI tools daily — including Claude API and LLM-driven
workflows — and have led teams building multi-agent automation systems.
I understand the technology well enough to direct it strategically and
translate it for both engineers and executives.

SENIORITY: Senior Manager → Director level preferred
INDUSTRY FIT: Enterprise tech, cloud infrastructure, infrastructure, storage, networking
NOT A FIT: Pure IC engineering roles, sales, finance, non-tech management, Pure Software Development
"""

# Minimum match score to include in digest (0-100)
SCORE_THRESHOLD = 60

# ─────────────────────────────────────────────
# Source definitions — add new sources here
# Each entry: (sender_address, source_label)
# source_label appears on the job card and digest header
# ─────────────────────────────────────────────
LINKEDIN_SENDERS = [
    "jobalerts-noreply@linkedin.com",
    "jobs-noreply@linkedin.com",
    "messages-noreply@linkedin.com",
]

INDEED_SENDERS = [
    "donotreply@match.indeed.com",
    "alert@indeed.com",
]

# Combined list used for IMAP search — (address, source_label)
ALL_SENDERS = (
    [(s, "LinkedIn") for s in LINKEDIN_SENDERS] +
    [(s, "Indeed")   for s in INDEED_SENDERS]
)


# ─────────────────────────────────────────────
# Email parsers — one per source
# Each returns a list of job dicts with a
# consistent shape: title, company, location,
# link, email_id, source
# ─────────────────────────────────────────────

def parse_linkedin_email(body, email_id):
    """Extract job listings from a LinkedIn alert email body."""
    jobs = []
    # LinkedIn separates listings with lines of dashes
    sections = re.split(r'-{10,}', body)

    for section in sections:
        lines = [l.strip() for l in section.strip().splitlines() if l.strip()]
        if not lines:
            continue

        title, company, location, link = None, None, None, None

        for line in lines:
            # Skip footer / utility lines
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
                any(s in line for s in
                    ['NC', 'NY', 'CA', 'TX', 'Remote', 'Hybrid', 'United States'])
            ):
                location = line

        # LinkedIn wraps job URLs with a tracking redirect — extract the job ID
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
                "email_id": email_id,
                "source":   "LinkedIn",
            })

    return jobs


def parse_indeed_email(body, email_id):
    """Extract job listings from an Indeed alert email body."""
    jobs = []

    # Indeed uses a different structure — each job block contains a job title
    # as a link, followed by company and location on separate lines.
    # We look for job title + company/location before the next URL block.

    # Strategy: split on blank lines, then look for blocks with a job URL
    sections = re.split(r'\n{2,}', body)

    for section in sections:
        lines = [l.strip() for l in section.strip().splitlines() if l.strip()]
        if not lines:
            continue

        title, company, location, link = None, None, None, None

        # Look for an Indeed job URL anywhere in the section
        url_match = re.search(
            r'https://(?:www\.)?indeed\.com/(?:rc/clk|viewjob|pagead/clk)[^\s"\'<>]+',
            section
        )
        # Also catch short redirect links like r.indeed.com
        if not url_match:
            url_match = re.search(r'https://r\.indeed\.com/[^\s"\'<>]+', section)

        if not url_match:
            continue  # no job URL = not a job block

        link = url_match.group(0).rstrip('.')

        for line in lines:
            # Skip Indeed utility lines
            if any(x in line.lower() for x in
                   ['unsubscribe', 'manage alerts', 'view all jobs',
                    'indeed.com', 'privacy', 'http']):
                continue
            if line.startswith('http') or line.startswith('www'):
                continue
            if len(line) < 3:
                continue

            if not title and len(line) > 5:
                title = line
            elif title and not company and len(line) > 2:
                company = line
            elif company and not location and (
                ',' in line or
                any(s in line for s in
                    ['NC', 'NY', 'CA', 'TX', 'Remote', 'Hybrid',
                     'United States', 'Full-time', 'Part-time'])
            ):
                location = line

        if title and link:
            jobs.append({
                "title":    title,
                "company":  company or "See listing",
                "location": location or "See listing",
                "link":     link,
                "email_id": email_id,
                "source":   "Indeed",
            })

    return jobs


def parse_email_body(body, email_id, source):
    """Route to the correct parser based on source label."""
    if source == "LinkedIn":
        return parse_linkedin_email(body, email_id)
    elif source == "Indeed":
        return parse_indeed_email(body, email_id)
    return []


# ─────────────────────────────────────────────
# Claude scoring — unchanged
# ─────────────────────────────────────────────

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
 "total":85,"why_good":"Director-level role at enterprise tech company aligns with NetApp background.",
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


# ─────────────────────────────────────────────
# HTML digest builders
# ─────────────────────────────────────────────

def score_config(total):
    """Return (text_color, label, card_bg, badge_bg, badge_text) based on score."""
    if total >= 80:
        return "#15803d", "Strong Match", "#f0fdf4", "#bbf7d0", "#166534"
    elif total >= 60:
        return "#b45309", "Good Match",   "#fffbeb", "#fde68a", "#92400e"
    else:
        return "#b91c1c", "Below Threshold", "#fef2f2", "#fecaca", "#991b1b"


def score_bar_html(value, max_val=25):
    """Render a mini horizontal score bar for a sub-score."""
    pct = int((value / max_val) * 100)
    bar_color = "#16a34a" if pct >= 80 else ("#d97706" if pct >= 60 else "#ef4444")
    return (
        f'<div style="flex:1;height:4px;background:#e5e7eb;border-radius:2px;overflow:hidden;">'
        f'<div style="width:{pct}%;height:100%;background:{bar_color};border-radius:2px;"></div>'
        f'</div>'
    )


def source_badge_html(source):
    """Render a small source pill — LinkedIn blue or Indeed blue."""
    if source == "Indeed":
        bg, fg, label = "#e8f0fe", "#1a56db", "Indeed"
    else:
        bg, fg, label = "#e8f4fd", "#0a66c2", "LinkedIn"
    return (
        f'<span style="font-size:10px;font-weight:700;letter-spacing:0.06em;'
        f'background:{bg};color:{fg};padding:2px 8px;border-radius:4px;'
        f'text-transform:uppercase;">{label}</span>'
    )


def build_job_card(job, scoring, rank):
    """Build a single polished job card for the HTML digest."""
    total    = scoring.get("total", 0)
    why      = scoring.get("why_good", "")
    concerns = scoring.get("concerns", "")

    tf  = scoring.get("title_fit", 0)
    sm  = scoring.get("skill_match", 0)
    sl  = scoring.get("seniority_level", 0)
    inf = scoring.get("industry_fit", 0)

    text_color, _, card_bg, _, _ = score_config(total)

    is_strong   = total >= 80
    left_border = "4px solid #15803d" if is_strong else "1px solid #e5e7eb"
    card_border = "1px solid #bbf7d0" if is_strong else "1px solid #e5e7eb"
    card_bg     = "#f0fdf4"           if is_strong else "#ffffff"

    strong_banner = ""
    if is_strong:
        strong_banner = (
            '<div style="background:#15803d;color:#ffffff;font-size:11px;font-weight:700;'
            'letter-spacing:0.08em;text-transform:uppercase;padding:5px 14px;'
            'border-radius:4px;display:inline-block;margin-bottom:12px;">&#9733; Strong Match</div>'
        )

    concerns_html = ""
    if concerns and concerns.strip().lower() not in ("none", "none."):
        concerns_html = (
            f'<div style="display:flex;align-items:flex-start;gap:6px;margin-top:8px;'
            f'padding:8px 10px;background:#fffbeb;border-radius:6px;'
            f'border-left:3px solid #f59e0b;">'
            f'<span style="font-size:12px;color:#92400e;line-height:1.5;">'
            f'&#9888;&#xfe0e; {concerns}</span></div>'
        )

    # Button label and URL vary by source
    source      = job.get("source", "LinkedIn")
    btn_label   = f"View on {source} &#8594;"

    return f"""
    <div style="background:{card_bg};border:{card_border};border-left:{left_border};
                border-radius:10px;padding:20px 22px;margin-bottom:14px;">

        {strong_banner}

        <div style="display:flex;align-items:flex-start;gap:14px;">
            <div style="flex-shrink:0;width:32px;height:32px;border-radius:50%;
                        background:#f3f4f6;border:1px solid #e5e7eb;
                        display:flex;align-items:center;justify-content:center;
                        font-size:13px;font-weight:700;color:#6b7280;">{rank}</div>
            <div style="flex:1;min-width:0;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                    <div style="font-size:16px;font-weight:700;color:#111827;line-height:1.3;">
                        {job['title']}</div>
                    {source_badge_html(source)}
                </div>
                <div style="font-size:13px;color:#6b7280;">
                    {job['company']} &nbsp;&middot;&nbsp; {job['location']}
                </div>
            </div>
            <div style="flex-shrink:0;text-align:center;min-width:52px;">
                <div style="font-size:26px;font-weight:800;color:{text_color};line-height:1;">{total}</div>
                <div style="font-size:10px;color:#9ca3af;margin-top:1px;">/ 100</div>
            </div>
        </div>

        <div style="margin:14px 0 10px;display:grid;grid-template-columns:1fr 1fr;gap:8px 20px;">
            <div>
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">
                    <span style="font-size:11px;color:#9ca3af;width:72px;">Title Fit</span>
                    {score_bar_html(tf)}
                    <span style="font-size:11px;font-weight:600;color:#374151;width:28px;text-align:right;">{tf}/25</span>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:11px;color:#9ca3af;width:72px;">Skills</span>
                    {score_bar_html(sm)}
                    <span style="font-size:11px;font-weight:600;color:#374151;width:28px;text-align:right;">{sm}/25</span>
                </div>
            </div>
            <div>
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">
                    <span style="font-size:11px;color:#9ca3af;width:72px;">Seniority</span>
                    {score_bar_html(sl)}
                    <span style="font-size:11px;font-weight:600;color:#374151;width:28px;text-align:right;">{sl}/25</span>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:11px;color:#9ca3af;width:72px;">Industry</span>
                    {score_bar_html(inf)}
                    <span style="font-size:11px;font-weight:600;color:#374151;width:28px;text-align:right;">{inf}/25</span>
                </div>
            </div>
        </div>

        <div style="font-size:13px;color:#374151;line-height:1.6;padding:10px 12px;
                    background:#f9fafb;border-radius:6px;border-left:3px solid #d1d5db;
                    margin-bottom:4px;">{why}</div>

        {concerns_html}

        <div style="margin-top:14px;">
            <a href="{job['link']}"
               style="display:inline-block;background:#0a66c2;color:#ffffff;
                      text-decoration:none;font-size:13px;font-weight:600;
                      padding:9px 20px;border-radius:6px;letter-spacing:0.01em;">
                {btn_label}
            </a>
        </div>
    </div>"""


def build_html_digest(scored_jobs, all_count, source_counts):
    """Build the full HTML email digest.

    source_counts is a dict like {"LinkedIn": 8, "Indeed": 6}
    used to show the per-source breakdown in the header.
    """
    date_str = datetime.now().strftime("%A, %B %d, %Y")
    shown    = len(scored_jobs)
    skipped  = all_count - shown
    strong   = sum(1 for _, s in scored_jobs if s.get("total", 0) >= 80)
    good     = sum(1 for _, s in scored_jobs if 60 <= s.get("total", 0) < 80)

    # Source breakdown line for the header
    source_line = " &nbsp;&middot;&nbsp; ".join(
        f"{v} {k}" for k, v in sorted(source_counts.items()) if v > 0
    )

    # Split cards into strong / good sections
    strong_cards = ""
    good_cards   = ""
    for i, (job, scoring) in enumerate(scored_jobs, 1):
        card = build_job_card(job, scoring, i)
        if scoring.get("total", 0) >= 80:
            strong_cards += card
        else:
            good_cards += card

    strong_section = ""
    if strong_cards:
        strong_section = (
            f'<div style="font-size:11px;font-weight:700;color:#15803d;letter-spacing:0.1em;'
            f'text-transform:uppercase;margin:24px 0 10px;">'
            f'&#9733; Strong Matches &mdash; {strong} job{"s" if strong != 1 else ""}</div>'
            f'{strong_cards}'
        )

    good_section = ""
    if good_cards:
        good_section = (
            f'<div style="font-size:11px;font-weight:700;color:#b45309;letter-spacing:0.1em;'
            f'text-transform:uppercase;margin:24px 0 10px;">'
            f'Good Matches &mdash; {good} job{"s" if good != 1 else ""}</div>'
            f'{good_cards}'
        )

    no_matches_msg = ""
    if not scored_jobs:
        no_matches_msg = (
            '<div style="text-align:center;padding:40px 20px;color:#9ca3af;">'
            '<div style="font-size:32px;margin-bottom:12px;">&#128270;</div>'
            '<div style="font-size:15px;font-weight:600;color:#6b7280;">No matches today</div>'
            '<div style="font-size:13px;margin-top:6px;">No jobs cleared the score threshold. Check back tomorrow.</div>'
            '</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Digest &mdash; {date_str}</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">

<div style="max-width:660px;margin:0 auto;padding:28px 16px 40px;">

    <!-- Header -->
    <div style="background:#0a2540;border-radius:12px;padding:28px 28px 24px;
                margin-bottom:20px;color:#ffffff;">
        <div style="font-size:11px;font-weight:700;letter-spacing:0.12em;
                    text-transform:uppercase;color:#60a5fa;margin-bottom:8px;">
            Job Alert Digest
        </div>
        <div style="font-size:22px;font-weight:700;line-height:1.2;margin-bottom:4px;">
            {date_str}
        </div>
        <div style="font-size:13px;color:#94a3b8;margin-top:4px;">
            Adam Haywood &nbsp;&middot;&nbsp; Senior EM / Director / VP Engineering
        </div>
        <div style="font-size:12px;color:#64748b;margin-top:6px;">
            Sources: {source_line}
        </div>
    </div>

    <!-- Summary stats -->
    <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:10px;
                padding:20px 24px;margin-bottom:8px;">
        <div style="font-size:11px;font-weight:700;color:#9ca3af;letter-spacing:0.1em;
                    text-transform:uppercase;margin-bottom:16px;">Today&rsquo;s summary</div>
        <div style="display:flex;gap:0;flex-wrap:wrap;">
            <div style="flex:1;min-width:80px;padding:0 16px 0 0;border-right:1px solid #f3f4f6;">
                <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;">Scanned</div>
                <div style="font-size:26px;font-weight:800;color:#111827;">{all_count}</div>
            </div>
            <div style="flex:1;min-width:80px;padding:0 16px;border-right:1px solid #f3f4f6;">
                <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;">Shown</div>
                <div style="font-size:26px;font-weight:800;color:#0a66c2;">{shown}</div>
            </div>
            <div style="flex:1;min-width:80px;padding:0 16px;border-right:1px solid #f3f4f6;">
                <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;">Strong</div>
                <div style="font-size:26px;font-weight:800;color:#15803d;">{strong}</div>
            </div>
            <div style="flex:1;min-width:80px;padding:0 16px;border-right:1px solid #f3f4f6;">
                <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;">Good</div>
                <div style="font-size:26px;font-weight:800;color:#b45309;">{good}</div>
            </div>
            <div style="flex:1;min-width:80px;padding:0 0 0 16px;">
                <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;">Filtered</div>
                <div style="font-size:26px;font-weight:800;color:#d1d5db;">{skipped}</div>
            </div>
        </div>
        <div style="margin-top:14px;padding-top:14px;border-top:1px solid #f3f4f6;
                    font-size:12px;color:#9ca3af;">
            Threshold: {SCORE_THRESHOLD}+ / 100 &nbsp;&middot;&nbsp;
            Scored against Senior EM / Director profile &nbsp;&middot;&nbsp;
            Ranked highest to lowest
        </div>
    </div>

    {strong_section}
    {good_section}
    {no_matches_msg}

    <!-- Footer -->
    <div style="text-align:center;margin-top:28px;padding-top:20px;border-top:1px solid #e5e7eb;">
        <div style="font-size:12px;color:#9ca3af;line-height:1.8;">
            Generated by Job Alert Agent &nbsp;&middot;&nbsp; Powered by Claude AI<br>
            Adjust threshold: <code style="font-size:11px;background:#f3f4f6;
            padding:1px 5px;border-radius:3px;">SCORE_THRESHOLD</code>
            in job_alert_agent.py
        </div>
    </div>

</div>
</body>
</html>"""


# ─────────────────────────────────────────────
# Email sender — unchanged
# ─────────────────────────────────────────────

def send_digest(html_content, job_count):
    gmail_address  = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_password:
        print("  ⚠️  Gmail credentials not in .env — skipping email")
        return

    print("\n📧 Sending job digest to Gmail...")
    msg            = MIMEMultipart("alternative")
    msg["Subject"] = (
        f"💼 Job Digest — {job_count} match{'es' if job_count != 1 else ''} · "
        f"{datetime.now().strftime('%b %d, %Y')}"
    )
    msg["From"] = gmail_address
    msg["To"]   = gmail_address

    plain = (
        f"Job Digest — {datetime.now().strftime('%B %d, %Y')}\n"
        f"{job_count} match{'es' if job_count != 1 else ''} found. "
        f"Open the HTML version to view details."
    )
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, gmail_address, msg.as_string())
        print("  ✅ Job digest sent to Gmail")
    except Exception as e:
        print(f"  ⚠️  Email failed: {e}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    import imaplib
    import email as email_lib

    print(f"\n💼 Job Alert Agent — Adam Haywood")
    print(f"   {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}\n")

    gmail_address  = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    print("📬 Connecting to Gmail via IMAP...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_address, gmail_password)
        mail.select("inbox")
    except Exception as e:
        print(f"  ❌ Gmail IMAP connection failed: {e}")
        print("  Enable IMAP in Gmail Settings → See all settings → Forwarding and POP/IMAP")
        return

    all_jobs     = []
    since_str    = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
    source_counts = {"LinkedIn": 0, "Indeed": 0}

    # ── Fetch emails from all senders
    for sender, source in ALL_SENDERS:
        _, msg_nums = mail.search(None, f'(FROM "{sender}" SINCE "{since_str}")')
        ids = msg_nums[0].split()
        print(f"  {source}: {len(ids)} email(s) from {sender}")

        for num in ids:
            _, msg_data = mail.fetch(num, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            jobs = parse_email_body(body, num.decode(), source)
            all_jobs.extend(jobs)

    mail.logout()

    if not all_jobs:
        print("\n  No job alert emails found in the last 7 days.")
        return

    # ── Deduplicate by link
    seen_links = set()
    unique_jobs = []
    for job in all_jobs:
        if job["link"] not in seen_links:
            seen_links.add(job["link"])
            unique_jobs.append(job)
            source_counts[job["source"]] = source_counts.get(job["source"], 0) + 1

    print(f"\n📋 {len(unique_jobs)} unique listings "
          f"(LinkedIn: {source_counts['LinkedIn']}, Indeed: {source_counts['Indeed']}) "
          f"— scoring each...\n")

    # ── Score each job with Claude
    scored = []
    for i, job in enumerate(unique_jobs, 1):
        print(f"  [{i}/{len(unique_jobs)}] [{job['source']}] "
              f"{job['title']} at {job['company']}...", end="", flush=True)
        scoring = score_job(job)
        total   = scoring.get("total", 0)
        rec     = scoring.get("recommendation", "Skip")
        print(f" {total}/100 — {rec}")

        if total >= SCORE_THRESHOLD:
            scored.append((job, scoring))

    scored.sort(key=lambda x: x[1].get("total", 0), reverse=True)

    print(f"\n✅ {len(scored)} jobs above threshold ({SCORE_THRESHOLD}+) "
          f"out of {len(unique_jobs)} total\n")

    # ── Build and send digest (always sends, even on zero-match days)
    html = build_html_digest(scored, len(unique_jobs), source_counts)
    send_digest(html, len(scored))

    # ── Save locally
    os.makedirs("job_digests", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath  = f"job_digests/digest_{timestamp}.html"
    with open(filepath, "w") as f:
        f.write(html)
    print(f"💾 Digest saved to {filepath}")

    # ── Terminal summary
    print(f"\n{'='*60}")
    print(f"  TOP MATCHES")
    print(f"{'='*60}")
    for job, s in scored[:5]:
        print(f"  {s['total']:3d}/100  [{job['source']}] {job['title']} at {job['company']}")
        print(f"          {job['location']}")
        print(f"          {s['recommendation']} — {s['why_good'][:70]}")
        print()


if __name__ == "__main__":
    main()
