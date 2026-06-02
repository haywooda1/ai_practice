# AI Development Notes — Adam Haywood
> Started: May 2026 | Repo: github.com/haywooda1/ai_practice

---

## Table of Contents
1. [Environment Setup](#1-environment-setup)
2. [Git & GitHub](#2-git--github)
3. [Python Concepts](#3-python-concepts)
4. [Claude API](#4-claude-api)
5. [MCP Servers](#5-mcp-servers)
6. [Agents Built](#6-agents-built)
7. [Key Commands](#7-key-commands)
8. [Troubleshooting Log](#8-troubleshooting-log)

---

## 1. Environment Setup

### Tools Installed
| Tool | Purpose |
|---|---|
| VS Code | Code editor |
| Git | Version control |
| Python 3 (Homebrew) | Language runtime |
| Node.js | Required for MCP servers |
| Virtual environment (venv) | Isolated Python packages per project |

### Virtual Environment
```bash
# Create (one time per project)
python3 -m venv venv

# Activate (every new terminal session)
source venv/bin/activate

# Deactivate when done
deactivate

# Install packages (always activate first)
pip install anthropic python-dotenv yfinance
```

**Why venv?** Homebrew Python blocks system-wide pip installs.
Each project gets its own isolated set of packages — no conflicts.

### VS Code Settings
- Enable `python.terminal.useEnvFile` → auto-loads `.env` in terminal sessions
- Install `Shell Command: Install 'code' command in PATH` → lets you open files with `code filename`

---

## 2. Git & GitHub

### One-Time Git Setup
```bash
git config --global user.name "Adam Haywood"
git config --global user.email "unixnrdu@yahoo.com"
```

### The Daily Loop
```bash
# 1. Edit your file
# 2. Stage it
git add filename.py
# 3. Commit with a message
git commit -m "What you changed and why"
# 4. Push to GitHub
git push origin main
```

### Common Git Commands
```bash
git status              # see what's changed
git log --oneline -5    # see last 5 commits
git show abc1234 --stat # see what files a commit changed
git reset HEAD~1        # undo last commit (keeps your edits)
git reset HEAD~2        # undo last 2 commits
git pull                # pull latest from GitHub
git push origin main --verbose  # push with detailed error output
```

### .gitignore — What to Always Exclude
```
.env                  # API keys — NEVER commit
venv/                 # virtual environment — machine specific
cover_letters/        # personal job applications
portfolio_reports/    # financial reports
job_digests/          # LinkedIn job digests
__pycache__/          # Python cache files
```

### .env File Pattern
```bash
# .env (never committed)
ANTHROPIC_API_KEY=sk-ant-...
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

# .env.example (committed — shows what variables are needed)
ANTHROPIC_API_KEY=your-key-here
GMAIL_ADDRESS=your-gmail-here
GMAIL_APP_PASSWORD=your-app-password-here
```

---

## 3. Python Concepts

### Imports
```python
import anthropic              # import whole library → use as anthropic.Anthropic()
from dotenv import load_dotenv  # import one thing → use directly as load_dotenv()
from datetime import datetime, timedelta  # import multiple things from one library
```

### Functions
```python
def function_name(input1, input2):
    """What this function does."""
    # work happens here
    return result           # hand back the output
```
- `def` defines a reusable block of code
- Parameters are the inputs (in parentheses)
- `return` hands data back to whoever called the function

### Dictionaries
```python
# Define
POSITIONS = {
    "NTAP": {"name": "NetApp", "shares": 1900},
    "NVDA": {"name": "NVIDIA", "shares": 25},
}

# Loop — three ways:
for ticker in POSITIONS:              # keys only → "NTAP", "NVDA"
for pos in POSITIONS.values():        # values only → {"name":...}, {"name":...}
for ticker, pos in POSITIONS.items(): # both → use when you need key AND value
```

### f-strings — Variable Substitution
```python
name = "Adam"
price = 140.50
print(f"Hello {name}, NTAP is at ${price:.2f}")
# Output: Hello Adam, NTAP is at $140.50
```
Curly braces `{}` are substitution slots — Python replaces them with the variable's value at runtime.

### Regular Expressions
```python
import re

re.split(r'-{10,}', text)      # split text at 10+ dashes
re.search(r'pattern', text)    # find first match — returns match object or None
re.findall(r'pattern', text)   # find ALL matches — returns list
re.sub(r'pattern', 'new', text) # replace matches with something else

# Capture groups — extract specific parts
url_match = re.search(r'jobs/view/(\d+)', url)
if url_match:
    job_id = url_match.group(1)  # group(0)=full match, group(1)=first capture

# Common patterns
r'\d+'     # one or more digits
r'\w+'     # one or more word characters
r'\.''     # literal dot (. alone means "any character")
r'-{10,}'  # 10 or more dashes
```


### File I/O — The `open()` Function
Python's built-in `open()` function reads and writes files.

**Basic syntax:**
```python
open(filename, mode)
```

**Modes:**
| Mode | Meaning | Behavior |
|---|---|---|
| `"r"` | Read | Opens for reading — default if not specified |
| `"w"` | Write | Creates file if missing, **overwrites** if exists |
| `"a"` | Append | Creates file if missing, **adds to end** if exists |
| `"x"` | Create | Creates file — fails if it already exists |

**Always use `with open(...)` — never plain `open()`:**
```python
with open("NOTES.md", "a") as f:
    f.write("something")
```
`with` is a context manager — automatically closes and saves the file when
the block finishes, even if your script crashes mid-write.

**`as f`** names the open file object. `f` is just convention — call it anything.

**Methods on the file object:**
```python
f.write("text")    # write a string
f.read()           # read entire file as one string
f.readlines()      # read as a list of lines
f.readline()       # read one line at a time
```

**Three patterns you'll use constantly:**
```python
# Read a file
with open("NOTES.md", "r") as f:
    content = f.read()

# Write a new file (or overwrite existing)
with open("output.txt", "w") as f:
    f.write("Hello world")

# Append to existing file without touching current content
with open("NOTES.md", "a") as f:
    f.write("\n## New Section\n")
    f.write("Some new content")
```

**When to use `"w"` vs `"a"`:**
- `"w"` → fresh file each run (timestamped reports, cover letters)
- `"a"` → running log that grows over time (NOTES.md updates, cron logs)

You already use this in `portfolio_monitor.py` and `job_alert_agent.py`
when saving reports — `"w"` creates a fresh timestamped file each run.

### Data Flow Through Functions (Parameter Relay)
```python
# Data flows like a relay race — each function passes to the next
main()                          # ticker = "NTAP"
  → build_stock_summary(ticker) # receives "NTAP", passes it on
    → get_quote(ticker)         # receives "NTAP"
      → fetch_fmp(f"quote/{ticker}") # "NTAP" fills into URL
```

### timedelta — Date Math
```python
from datetime import datetime, timedelta

# 7 days ago
since = datetime.now() - timedelta(days=7)
since_str = since.strftime("%d-%b-%Y")  # "22-May-2026" — IMAP format
```

### Multiple Return Values & Unpacking
```python
# A function can return multiple values at once (separated by commas)
def score_config(total):
    if total >= 80:
        return "#15803d", "Strong Match", "#f0fdf4", "#bbf7d0", "#166534"
    elif total >= 60:
        return "#b45309", "Good Match", "#fffbeb", "#fde68a", "#92400e"

# Caller unpacks them into named variables
text_color, label, card_bg, badge_bg, badge_text = score_config(85)

# Use _ to discard values you don't need
text_color, _, card_bg, _, _ = score_config(85)
```
This pattern is common when a function produces a bundle of related values.
One call gives you everything; change the logic once and all callers update.

### Ternary / Inline If-Else
```python
# Full if/else (two lines)
if is_strong:
    left_border = "4px solid green"
else:
    left_border = "1px solid gray"

# Ternary — same thing, one line
left_border = "4px solid green" if is_strong else "1px solid gray"
```
Use ternary when you're just assigning a variable — not for complex logic.

### Empty String as a Conditional Toggle
```python
# Start with nothing
strong_banner = ""

# Conditionally overwrite with content
if is_strong:
    strong_banner = "<div>★ Strong Match</div>"

# Drop into f-string — empty string contributes nothing, content shows up
return f"...{strong_banner}..."
```
Standard pattern for optional HTML chunks. Avoids nested f-strings or
conditional expressions inside the template.

### Default Parameters
```python
# max_val=25 is the default — used if caller doesn't specify it
def score_bar_html(value, max_val=25):
    pct = int((value / max_val) * 100)

score_bar_html(20)      # max_val = 25  →  pct = 80%
score_bar_html(20, 100) # max_val = 100 →  pct = 20%
```
Makes functions flexible without requiring the caller to always pass everything.

### enumerate() — Index + Value in One Loop
```python
# Without enumerate — manual counter
i = 1
for job, scoring in scored_jobs:
    card = build_job_card(job, scoring, i)
    i += 1

# With enumerate — cleaner, starting at 1
for i, (job, scoring) in enumerate(scored_jobs, 1):
    card = build_job_card(job, scoring, i)
```
The `(job, scoring)` on the left is tuple unpacking — each item in the list
is a pair, and Python splits it into two variables automatically.

### Dispatcher / Router Pattern
```python
# Instead of one function that handles everything with if/elif chains,
# use a router that delegates to the right specialist function:

def parse_email_body(body, email_id, source):
    if source == "LinkedIn":
        return parse_linkedin_email(body, email_id)
    elif source == "Indeed":
        return parse_indeed_email(body, email_id)
    return []
```
Clean to extend — adding Glassdoor means adding one `elif` and one new function.
Each parser focuses on one format; none of them know about the others.

### List of Tuples — Paired Data
```python
# Each item is a (address, label) pair
ALL_SENDERS = (
    [(s, "LinkedIn") for s in LINKEDIN_SENDERS] +
    [(s, "Indeed")   for s in INDEED_SENDERS]
)

# Unpack the pair in the loop
for sender, source in ALL_SENDERS:
    print(f"Checking {sender} ({source})")
```
Useful when two values always belong together — avoids parallel lists
that can drift out of sync.

### String Concatenation in a Loop
```python
strong_cards = ""   # start with empty string

for i, (job, scoring) in enumerate(scored_jobs, 1):
    card = build_job_card(job, scoring, i)
    if scoring.get("total", 0) >= 80:
        strong_cards += card   # append each card's HTML to the growing string
```
By the end of the loop `strong_cards` is one long HTML string containing
all the strong-match cards. Same pattern used for `good_cards`.

---

## 4. Claude API

### Basic API Call Pattern
```python
import anthropic
from dotenv import load_dotenv

load_dotenv()                    # reads .env file
client = anthropic.Anthropic()   # creates connection, auto-reads ANTHROPIC_API_KEY

message = client.messages.create(
    model="claude-sonnet-4-5",   # which Claude model to use
    max_tokens=1024,             # max response length (~750 words)
    system="You are a...",       # sets Claude's role/behavior (optional)
    messages=[
        {"role": "user", "content": "Your question here"}
    ]
)

print(message.content[0].text)   # extract the text response
```

### Key Parameters
| Parameter | What it does |
|---|---|
| `model` | Which Claude version (`claude-sonnet-4-5` is current stable) |
| `max_tokens` | Cap on response length — 1024 is good for most tasks |
| `system` | System prompt — sets Claude's persona and behavior |
| `messages` | List of conversation turns with `role` and `content` |

### System Prompts
The `system` parameter is separate from the user message. It shapes how Claude
responds to everything — think of it as a briefing before the conversation starts.
The more specific, the better the output.

```python
system="""You are an expert cover letter writer.
- Be specific — reference actual job requirements
- Keep to 3-4 paragraphs
- Never use generic phrases like 'I am excited to apply'"""
```

### The `client` Namespaces
```python
client.messages        # conversational AI calls ← used most
client.models          # list available models
client.batches         # bulk requests (cheaper, async)
client.beta.messages   # experimental features
```

### Discovering Available Methods
```python
# In VS Code — type client. and pause for autocomplete
# In terminal:
python3 -c "import anthropic; help(anthropic.Anthropic)"
```

---

## 5. MCP Servers

### What MCP Is
Model Context Protocol — lets Claude connect to real tools and take actions,
not just answer questions. Each MCP server gives Claude a new capability.

**Without MCP:** Claude answers based on what you type
**With MCP:** Claude reads your files, searches the web, checks email, updates calendar

### Config File Location (Mac)
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

### Config File Structure
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/Adam/DEV_Space"]
    }
  }
}
```
**Important:** Merge into existing config — don't replace it. Always quit and
relaunch Claude Desktop after editing (`Cmd+Q` then reopen).

### Filesystem Server
Gives Claude read/write access to a specific folder on your Mac.
Test it in Claude Desktop:
> "Read my basic_script.py file and tell me what it does"

### Available MCP Servers
| Server | What it gives Claude |
|---|---|
| filesystem | Read/write local files |
| GitHub | Read repos, create issues, review PRs |
| Gmail | Read/send email |
| Google Calendar | Read/create calendar events |
| Google Drive | Access Drive files |
| Brave Search | Real-time web search |

---

## 6. Agents Built

### Agent 1 — Hello Claude (`basic_script.py`)
First Claude API call. Sends a message, prints the response.
**Concepts:** imports, client setup, messages.create, extracting response text

---

### Agent 2 — Job Search Assistant (`job_assistant.py`)
Reads job descriptions, drafts tailored cover letters, saves to files.

**Run:**
```bash
python3 job_assistant.py
# Paste job description → type END → enter a filename → get cover letter
```

**Key concepts:** system prompts, multi-line input, file saving with timestamps,
`os.makedirs`, `MY_BACKGROUND` as resume context

**Output:** Saves to `cover_letters/YYYYMMDD_HHMMSS_job-title.txt`

---

### Agent 3 — Portfolio Monitor (`portfolio_monitor.py`)
Fetches live stock data for 13 positions, calculates gain/loss, gets analyst
ratings and news, sends Claude's analysis as an HTML email every weekday at 8am.

**Run:**
```bash
python3 portfolio_monitor.py
```

**Schedule (cron):**
```
0 8 * * 1-5 /Users/Adam/DEV_Space/ai_practice/venv/bin/python3 /Users/Adam/DEV_Space/ai_practice/portfolio_monitor.py >> /Users/Adam/DEV_Space/ai_practice/portfolio_reports/cron.log 2>&1
```

**Your Positions:**
| Ticker | Shares | Cost Basis |
|---|---|---|
| NTAP | 1,900 | ESPP/RSU mix — see Etrade |
| CDE | 150 | $14.996 |
| HIMS | 100 | $25.45 |
| LAC | 50 | $7.156 |
| NTSK | 90 | $21.33 |
| NVDA | 25 | $120.45 |
| NVO | 5 | $147.254 |
| NVTS | 200 | $15.145 |
| QBTS | 168 | $9.518 |
| RIOT | 30 | $10.22 |
| RIVN | 100 | $12.64 |
| SOFI | 100 | $9.30 |
| ZS | 9 | $133.41 |

**Note:** 200 NTAP RSU shares (grant RS100768, vest Aug 2026) forfeited — excluded.
~82 additional ESPP shares expected end of May 2026.

**Data source:** `yfinance` (free, no API key, pulls from Yahoo Finance)
**Key concepts:** dictionary loops, `.items()`, f-strings, HTML email, SMTP, cron

---

### Agent 4 — Job Alert Agent (`job_alert_agent.py`)
Reads LinkedIn and Indeed job alert emails from Gmail, scores each job against
your resume using Claude (0-100), filters to top matches, sends a ranked HTML
digest daily at 9am weekdays.

**Run:**
```bash
python3 job_alert_agent.py
```

**Schedule (cron):**
```
0 9 * * 1-5 /Users/Adam/DEV_Space/ai_practice/venv/bin/python3 /Users/Adam/DEV_Space/ai_practice/job_alert_agent.py >> /Users/Adam/DEV_Space/ai_practice/job_digests/cron.log 2>&1
```

**Scoring breakdown (25 pts each):**
- Title Fit — does the job title match Senior EM/Director/VP target?
- Skill Match — do required skills match your background?
- Seniority Level — is it the right level?
- Industry Fit — enterprise tech, cloud, AI/ML, storage?

**Threshold:** Jobs scoring 60+ are included. Change `SCORE_THRESHOLD` in script.

**Sources supported:**
| Source | Senders watched |
|---|---|
| LinkedIn | jobalerts-noreply@linkedin.com, jobs-noreply@linkedin.com, messages-noreply@linkedin.com |
| Indeed | donotreply@match.indeed.com, alert@indeed.com |

To add a new source: add a `NEW_SENDERS` list, add it to `ALL_SENDERS`, and write a
`parse_new_email()` function. Then add one `elif` in `parse_email_body()`.

**Gmail setup needed:**
- Forward LinkedIn/Indeed alerts to Gmail
- Gmail → enable IMAP (Settings → Forwarding and POP/IMAP)
- Gmail App Password → myaccount.google.com → Security → App Passwords

**HTML digest features:**
- Dark navy header with name and target role
- Summary stats bar: Scanned / Shown / Strong / Good / Filtered
- Jobs split into "★ Strong Matches" (80+) and "Good Matches" (60–79) sections
- Strong matches: green card background, thick left border, "★ Strong Match" banner
- Score breakdown: mini bar charts per sub-score (green/amber/red)
- Source badge on each card (LinkedIn blue / Indeed blue)
- Concerns shown in amber callout box
- "No matches today" empty state — digest always sends so you know the cron ran
- Local copy saved to `job_digests/digest_YYYYMMDD_HHMMSS.html`

**Key functions:**
| Function | What it does |
|---|---|
| `parse_linkedin_email(body, id)` | Extracts jobs from LinkedIn email format (dash-separated sections) |
| `parse_indeed_email(body, id)` | Extracts jobs from Indeed email format (blank-line sections, different URL patterns) |
| `parse_email_body(body, id, source)` | Router — dispatches to the right parser based on source label |
| `score_job(job)` | Sends job to Claude, returns JSON scoring dict |
| `score_config(total)` | Returns color/label/bg values based on score threshold |
| `score_bar_html(value)` | Renders a mini horizontal bar for a sub-score |
| `source_badge_html(source)` | Renders LinkedIn/Indeed pill badge |
| `build_job_card(job, scoring, rank)` | Builds one HTML job card |
| `build_html_digest(scored_jobs, all_count, source_counts)` | Assembles full HTML email |
| `send_digest(html, count)` | Sends via SMTP SSL to Gmail |

**Key concepts:** IMAP email reading, multipart email parsing, regex URL extraction,
dispatcher/router pattern, heuristic text extraction, JSON scoring via Claude,
conditional HTML via empty-string toggle, HTML digest with source badges

---

## 7. Key Commands

### Daily Workflow
```bash
cd /Users/Adam/DEV_Space/ai_practice  # go to repo
source venv/bin/activate               # activate environment
python3 script_name.py                 # run a script
deactivate                             # when done
```

### Git
```bash
git status
git add .
git commit -m "message"
git push origin main
git pull
```

### Cron
```bash
crontab -e        # edit scheduled tasks
crontab -l        # list current scheduled tasks
```

### Cron Time Format
```
* * * * *  command
│ │ │ │ └── day of week (0=Sun, 1=Mon ... 5=Fri, 1-5=weekdays)
│ │ │ └──── month (1-12)
│ │ └────── day of month (1-31)
│ └──────── hour (0-23)
└────────── minute (0-59)

0 8 * * 1-5  = 8:00am Monday through Friday
0 9 * * 1-5  = 9:00am Monday through Friday
```

### Python
```bash
python3 --version          # check Python version
pip list | grep anthropic  # check if library installed
pip install package-name   # install a package (venv must be active)
pip3 show anthropic        # show package details
```

---

## 8. Troubleshooting Log

| Problem | Cause | Fix |
|---|---|---|
| `git: user.name not set` | Git needs identity before committing | `git config --global user.name "Your Name"` |
| `Can't push — remote rejected` | GitHub branch protection or secret scanning | Check Settings → Branches → Rules |
| `externally-managed-environment` | Homebrew Python blocks system pip | Use venv: `python3 -m venv venv` |
| `UNSEEN` emails = 0 | Emails already read | Change IMAP search to `SINCE date` |
| MCP hammer icon missing | Version difference | Ask Claude "what tools do you have?" |
| `.env` not loading | `load_dotenv()` not called | Add `load_dotenv()` before API calls |
| `SyntaxError: invalid syntax` | Missing comma or bracket on previous line | Check the line ABOVE the error |
| `DeprecationWarning` on model | Old model name | Use `claude-sonnet-4-5` |
| `403 Forbidden` on FMP | Free tier limit | Switch to `yfinance` (free, no key needed) |
| Push rejected — secrets | API key in a commit | Remove from commit history, rotate the key |
| Indeed jobs not parsing | URL pattern mismatch | Check email source — add pattern to `parse_indeed_email()` regex |

---

## 9. How Email Body Parsing Works

This covers how `body` gets defined and flows through `job_alert_agent.py` —
a question that comes up because `parse_email_body` receives `body` as a
parameter but never defines it itself.

### The Full Flow

**Step 1 — IMAP fetches the raw email bytes**
```python
_, msg_data = mail.fetch(num, "(RFC822)")
raw = msg_data[0][1]
```
`RFC822` is the standard email format. This returns the entire email as raw
bytes — headers, body, attachments — exactly as received.

**Step 2 — Python parses the bytes into an email object**
```python
msg = email_lib.message_from_bytes(raw)
```
Converts raw bytes into a structured Python object you can interrogate.
Now you can ask questions like "is this multipart?" and "what's the content type?"

**Step 3 — Extract the plain text body**
```python
body = ""
if msg.is_multipart():
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
            break
else:
    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
```

**Why the multipart check?**
Emails often come in two flavors at once — a plain text version and an HTML
version — bundled together as a "multipart" email. `is_multipart()` tells
you which case you're in:
- **Multipart:** `msg.walk()` iterates through all parts; we grab the first
  `text/plain` one and stop
- **Not multipart:** the whole message is plain text, so call `get_payload()` directly

**What `.decode("utf-8", errors="ignore")` does:**
`get_payload(decode=True)` returns raw `bytes`, not a `str`. The `.decode()`
call converts bytes → Python string. `errors="ignore"` skips any characters
that can't be decoded rather than crashing.

**Step 4 — Pass body to the router**
```python
jobs = parse_email_body(body, num.decode(), source)
```
`body` is now a plain text string. `parse_email_body` routes it to the right
parser based on `source` ("LinkedIn" or "Indeed").

**Step 5 — Source-specific parsing**
```python
def parse_email_body(body, email_id, source):
    if source == "LinkedIn":
        return parse_linkedin_email(body, email_id)
    elif source == "Indeed":
        return parse_indeed_email(body, email_id)
    return []
```

### LinkedIn vs Indeed Format Differences

| | LinkedIn | Indeed |
|---|---|---|
| Job separator | Lines of 10+ dashes (`----------`) | Blank lines between blocks |
| URL pattern | `linkedin.com/comm/jobs/view/1234567` | `indeed.com/rc/clk` or `r.indeed.com/...` |
| Split strategy | `re.split(r'-{10,}', body)` | `re.split(r'\n{2,}', body)` |
| URL extraction | Capture the numeric job ID, rebuild clean URL | Grab the raw URL as-is |

### Key Takeaway
`body` is always built in `main()` before any parser is called.
`parse_email_body()` is a pure router — it receives the string and dispatches it.
The source-specific parsers (`parse_linkedin_email`, `parse_indeed_email`) do
the actual work of finding structure in that string.

---

*Last updated: June 2026*
*Repo: github.com/haywooda1/ai_practice*
