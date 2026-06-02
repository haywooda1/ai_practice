import anthropic
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

# Folder where cover letters get saved
OUTPUT_DIR = "cover_letters"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Your background — pulled directly from your resume
MY_BACKGROUND = """
Name: Adam Haywood
Location: Raleigh-Durham, NC
Contact: unixnrdu@yahoo.com | (919)880-8528 | linkedin.com/in/haywooda
#Identity: U.S. Navy Veteran | 25+ Years Experience
Identity: 25+ Years Experience

EXECUTIVE SUMMARY:
Senior Engineering Manager with 25+ years of experience leading global R&D,
Quality Engineering, and Interoperability organizations across enterprise
infrastructure platforms. Track record of aligning complex engineering execution
with customer and go-to-market priorities, helping support over $94M in quarterly
corporate revenue through accelerated partner and customer readiness. Experienced
in scaling high-impact teams, owning Capex/Opex planning and spend governance,
and driving AI/ML-enabled automation initiatives that improve operational
efficiency, decision quality, and delivery velocity.

CORE COMPETENCIES:
- Executive Leadership: Strategic planning and execution; global team leadership
  across FTE and contingent models; Capex/Opex and budget optimization; SOW and
  vendor management aligned to business and delivery objectives.
- Innovation & AI: Championed enterprise adoption of AI/ML-enabled automation to
  accelerate failure triage, improve engineering throughput, and reduce manual
  diagnostic effort across large-scale QA and R&D organizations.
- Technical Ecosystems: Directed validation and enablement of complex Linux,
  networking, and storage ecosystems ensuring scalable, high-performance platforms.
- Storage & Interoperability: Multi-vendor storage and fabric interoperability
  (NetApp ONTAP, EMC, Hitachi, HP, Cisco, Brocade).
- Compliance & Strategy: Governance and risk leadership; alignment of technical
  roadmaps with corporate financial, compliance, and go-to-market priorities.

PROFESSIONAL EXPERIENCE:

NetApp | Raleigh-Durham, NC | Jan 2005 – Recent

Senior Manager, Partner & Customer Enablement Solutions | June 2021 – Recent
- Directed FPVR testing and delivery supporting $94.5M in Q1/Q2 revenue through
  accelerated partner and customer readiness.
- Drove AI-enabled automation including multi-agent failure-triage capabilities,
  reducing manual diagnostic effort and improving testing velocity.
- Led globally distributed organization of 10 FTEs and 18 contingent resources.
- Owned Capex/Opex planning, SOW negotiation, and vendor oversight.
- Served on cross-functional portfolio councils prioritizing revenue-critical releases.

Manager, Partner & Customer Enablement Solutions | June 2011 – June 2021
- Scaled Quality Engineering capabilities sustaining 99.9% interoperability
  standards across complex multi-vendor environments.
- Established standardized R&D and QA workflows reducing time-to-market.
- Partnered with R&D, Product Management, and external technology partners.

Team Lead, Rapid Response Engineering QA/Interoperability | Jan 2005 – May 2011
- Led QA and interoperability efforts across heterogeneous SAN environments.
- Architected SAN test strategies across Solaris, RHEL, AIX, HP-UX, Windows.
- Introduced automation to streamline lab provisioning and test execution.

MILITARY SERVICE:
United States Navy — Electronics Technician
Specialized in SATCOM, microwave communications, and navigation systems.

CURRENTLY LEARNING:
Hands-on AI development — Claude API, MCP servers, Python agents, GitHub.
Actively building AI-powered tools and agents.
"""

def get_job_description():
    print("\n📋 Paste the job description below.")
    print("When done, type END on its own line and press Enter:\n")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def get_job_title():
    return input("\n📌 Enter a short job title for the filename (e.g. 'ai-eng-manager-google'): ").strip()


def generate_cover_letter(job_description):
    print("\n⏳ Generating your cover letter...")
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system="""You are an expert career coach and cover letter writer specializing
in senior engineering and AI leadership roles. Write a tailored, compelling cover
letter based on the candidate's background and the job description provided.

Guidelines:
- Be specific — reference actual requirements from the job posting by name
- Lead with the candidate's most relevant strength for THIS role
- Highlight the $94.5M revenue impact and AI/ML automation work where relevant
- Mention Navy veteran background if the role values leadership or discipline
- Keep it to 3-4 tight paragraphs — hiring managers don't read long letters
- Professional but warm tone — avoid stiff corporate language
- Never use generic filler phrases like 'I am excited to apply' or 'I am a team player'
- End with a confident, specific call to action""",
        messages=[{
            "role": "user",
            "content": f"My background:\n{MY_BACKGROUND}\n\nJob description:\n{job_description}"
        }]
    )
    return message.content[0].text


def save_cover_letter(cover_letter, job_description, job_title):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = job_title.replace(" ", "-").lower()
    filename = f"{OUTPUT_DIR}/{timestamp}_{safe_title}.txt"
    with open(filename, "w") as f:
        f.write(f"JOB: {job_title}\n")
        f.write(f"DATE: {datetime.now().strftime('%B %d, %Y')}\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"COVER LETTER:\n\n{cover_letter}\n\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"JOB DESCRIPTION:\n\n{job_description}")
    return filename


def main():
    print("🤖 Job Search Assistant — Adam Haywood")
    print("=======================================")
    while True:
        job_description = get_job_description()
        if not job_description.strip():
            print("No job description entered. Exiting.")
            break
        job_title = get_job_title()
        cover_letter = generate_cover_letter(job_description)
        print(f"\n✅ COVER LETTER:\n\n{cover_letter}")
        filename = save_cover_letter(cover_letter, job_description, job_title)
        print(f"\n💾 Saved to: {filename}")
        another = input("\nGenerate another? (y/n): ")
        if another.lower() != "y":
            break


if __name__ == "__main__":
    main()
