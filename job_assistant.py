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


# Save document with a filename that includes the job title and timestamp for easy reference.
#  Include the job description in the saved file for context when reviewing later. .TXT format
#
# def save_cover_letter(cover_letter, job_description, job_title):
#    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#    safe_title = job_title.replace(" ", "-").lower()
#    filename = f"{OUTPUT_DIR}/{timestamp}_{safe_title}.txt"
#    with open(filename, "w") as f:
#        f.write(f"JOB: {job_title}\n")
#        f.write(f"DATE: {datetime.now().strftime('%B %d, %Y')}\n")
#        f.write(f"{'='*60}\n\n")
#        f.write(f"COVER LETTER:\n\n{cover_letter}\n\n")
#        f.write(f"{'='*60}\n\n")
#        f.write(f"JOB DESCRIPTION:\n\n{job_description}")
#    return filename


 
# ── CHANGED: save_cover_letter now builds a .docx instead of a .txt ──────────
#
# What changed and why:
#
#   OLD: opened a plain text file with open(filename, "w") and wrote
#        everything as a string with f.write().
#
#   NEW: uses python-docx to build a structured Word document with:
#        - A styled header block (name, title, contact info)
#        - A horizontal rule divider
#        - The generated cover letter body as formatted paragraphs
#        - A metadata section at the end with job title and date
#        - The raw job description appended for reference
#
#   The Document object works like a canvas — you add paragraphs
#   one at a time and style each one individually (font, size, color,
#   alignment, bold, spacing). Nothing is written to disk until
#   doc.save(filename) is called at the very end.
#
def save_cover_letter(cover_letter, job_description, job_title):
    # Build the output filename — same naming pattern as before, just .docx now
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = job_title.replace(" ", "-").lower()
    filename = f"{OUTPUT_DIR}/{timestamp}_{safe_title}.docx"   # <-- .docx not .txt
 
    # Create a blank Word document
    doc = Document()
 
    # ── Page margins ─────────────────────────────────────────────────────────
    # python-docx sizes use "twips" (1 inch = 914400 EMUs, but for margins
    # we use the Pt() or Inches() helpers). Here we tighten margins slightly
    # so the letter has more breathing room — matching our polished .docx style.
    from docx.shared import Inches
    for section in doc.sections:
        section.top_margin    = Inches(0.85)
        section.bottom_margin = Inches(0.85)
        section.left_margin   = Inches(1.0)
        section.right_margin  = Inches(1.0)
 
    # ── Helper: set font on every run in a paragraph ──────────────────────────
    # A "run" in python-docx is a contiguous stretch of text with the same
    # formatting. When you do para.add_run("text"), you get one run back.
    # This helper styles it consistently so we don't repeat ourselves.
    def style_run(run, size=11, bold=False, color=None):
        run.font.name = "Arial"
        run.font.size = Pt(size)
        run.bold = bold
        if color:
            # RGBColor takes three ints: red, green, blue (0-255)
            run.font.color.rgb = RGBColor(*color)
 
    # ── NAME (large, dark blue, bold) ────────────────────────────────────────
    name_para = doc.add_paragraph()
    name_para.paragraph_format.space_after = Pt(2)
    name_run = name_para.add_run("ADAM HAYWOOD")
    style_run(name_run, size=20, bold=True, color=(31, 56, 100))   # dark navy
 
    # ── Sub-title ─────────────────────────────────────────────────────────────
    subtitle_para = doc.add_paragraph()
    subtitle_para.paragraph_format.space_after = Pt(2)
    sub_run = subtitle_para.add_run(
        "Senior Engineering Manager  |  Quality Engineering & Partner Enablement"
    )
    style_run(sub_run, size=10, color=(85, 85, 85))
 
    # ── Contact line ──────────────────────────────────────────────────────────
    contact_para = doc.add_paragraph()
    contact_para.paragraph_format.space_after = Pt(2)
    contact_run = contact_para.add_run(
        "unixnrdu@yahoo.com  |  (919) 880-8528  |  Raleigh-Durham, NC  |  U.S. Navy Veteran"
    )
    style_run(contact_run, size=9, color=(85, 85, 85))
 
    # ── LinkedIn ──────────────────────────────────────────────────────────────
    linkedin_para = doc.add_paragraph()
    linkedin_para.paragraph_format.space_after = Pt(6)
    linkedin_run = linkedin_para.add_run("linkedin.com/in/haywooda")
    style_run(linkedin_run, size=9, color=(85, 85, 85))
 
    # ── Horizontal rule (a paragraph with a bottom border) ───────────────────
    # python-docx doesn't have a built-in "insert horizontal rule" method,
    # so we fake it by applying a bottom border to an empty paragraph.
    # The border XML is injected directly into the paragraph's properties.
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
 
    rule_para = doc.add_paragraph()
    rule_para.paragraph_format.space_after = Pt(10)
    pPr = rule_para._p.get_or_add_pPr()     # get the paragraph properties element
    pBdr = OxmlElement("w:pBdr")             # create a border container
    bottom = OxmlElement("w:bottom")         # create the bottom border
    bottom.set(qn("w:val"), "single")        # solid line style
    bottom.set(qn("w:sz"), "6")              # thickness (half-points, so 6 = 0.75pt)
    bottom.set(qn("w:space"), "1")           # space between text and border
    bottom.set(qn("w:color"), "1F3864")      # dark navy to match the name color
    pBdr.append(bottom)
    pPr.append(pBdr)
 
    # ── Date ─────────────────────────────────────────────────────────────────
    date_para = doc.add_paragraph()
    date_para.paragraph_format.space_after = Pt(8)
    date_run = date_para.add_run(datetime.now().strftime("%B %d, %Y"))
    style_run(date_run, size=10, color=(85, 85, 85))
 
    # ── Salutation ────────────────────────────────────────────────────────────
    sal_para = doc.add_paragraph()
    sal_para.paragraph_format.space_after = Pt(8)
    sal_run = sal_para.add_run("Dear Hiring Manager,")
    style_run(sal_run, size=11)
 
    # ── Cover letter body ─────────────────────────────────────────────────────
    # The AI returns the letter as a block of text with paragraphs separated
    # by blank lines. We split on double newlines so each paragraph gets its
    # own Word paragraph (proper spacing) rather than one giant text blob.
    body_paragraphs = [p.strip() for p in cover_letter.split("\n\n") if p.strip()]
 
    for para_text in body_paragraphs:
        # Collapse any internal line breaks within a paragraph into spaces
        para_text = " ".join(para_text.splitlines())
        body_para = doc.add_paragraph()
        body_para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY   # justified like a real letter
        body_para.paragraph_format.space_after = Pt(8)
        body_run = body_para.add_run(para_text)
        style_run(body_run, size=11)
 
    # ── Sign-off ──────────────────────────────────────────────────────────────
    doc.add_paragraph()   # blank line before sign-off
    signoff_para = doc.add_paragraph()
    signoff_para.paragraph_format.space_after = Pt(2)
    style_run(signoff_para.add_run("Respectfully,"), size=11)
 
    doc.add_paragraph()   # space for signature
    doc.add_paragraph()
 
    name_sig = doc.add_paragraph()
    name_sig.paragraph_format.space_after = Pt(2)
    style_run(name_sig.add_run("Adam Haywood"), size=11, bold=True)
 
    footer_line = doc.add_paragraph()
    style_run(
        footer_line.add_run("U.S. Navy Veteran  |  linkedin.com/in/haywooda"),
        size=9, color=(85, 85, 85)
    )
 
    # ── Metadata section (replaces the === header block from the old .txt) ────
    # This gives you the same "filing" info the old .txt had, tucked at the end.
    doc.add_page_break()
 
    meta_label = doc.add_paragraph()
    style_run(meta_label.add_run("— Reference Copy —"), size=9, color=(150, 150, 150))
 
    meta_job = doc.add_paragraph()
    meta_job.paragraph_format.space_after = Pt(2)
    style_run(meta_job.add_run(f"Job: {job_title}"), size=9, color=(120, 120, 120))
 
    meta_date = doc.add_paragraph()
    meta_date.paragraph_format.space_after = Pt(10)
    style_run(
        meta_date.add_run(f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}"),
        size=9, color=(120, 120, 120)
    )
 
    jd_label = doc.add_paragraph()
    jd_label.paragraph_format.space_after = Pt(4)
    style_run(jd_label.add_run("Job Description:"), size=10, bold=True, color=(85, 85, 85))
 
    # Split and add the job description the same way we handled the letter body
    for jd_para in [p.strip() for p in job_description.split("\n\n") if p.strip()]:
        jd_para = " ".join(jd_para.splitlines())
        jd_p = doc.add_paragraph()
        jd_p.paragraph_format.space_after = Pt(6)
        style_run(jd_p.add_run(jd_para), size=9, color=(100, 100, 100))
 
    # ── Write the file to disk ────────────────────────────────────────────────
    # Nothing above actually touched the filesystem — doc.save() is the
    # single call that serializes the whole Document object into a .docx file.
    doc.save(filename)
    return filename
# ─────────────────────────────────────────────────────────────────────────────
 

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
