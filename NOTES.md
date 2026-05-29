# AI Development Notes — Adam Haywood

Started: May 2026 | Repo: github.com/haywooda1/ai\_practice

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

## 1\. Environment Setup

### Tools Installed

| Tool | Purpose |
| :---- | :---- |
| VS Code | Code editor |
| Git | Version control |
| Python 3 (Homebrew) | Language runtime |
| Node.js | Required for MCP servers |
| Virtual environment (venv) | Isolated Python packages per project |

### Virtual Environment

\# Create (one time per project)

python3 \-m venv venv

\# Activate (every new terminal session)

source venv/bin/activate

\# Deactivate when done

deactivate

\# Install packages (always activate first)

pip install anthropic python-dotenv yfinance

**Why venv?** Homebrew Python blocks system-wide pip installs. Each project gets its own isolated set of packages — no conflicts.

### VS Code Settings

- Enable `python.terminal.useEnvFile` → auto-loads `.env` in terminal sessions  
- Install `Shell Command: Install 'code' command in PATH` → lets you open files with `code filename`

---

## 2\. Git & GitHub

### One-Time Git Setup

git config \--global user.name "Adam Haywood"

git config \--global user.email "unixnrdu@yahoo.com"

### The Daily Loop

\# 1\. Edit your file

\# 2\. Stage it

git add filename.py

\# 3\. Commit with a message

git commit \-m "What you changed and why"

\# 4\. Push to GitHub

git push origin main

### Common Git Commands

git status              \# see what's changed

git log \--oneline \-5    \# see last 5 commits

git show abc1234 \--stat \# see what files a commit changed

git reset HEAD\~1        \# undo last commit (keeps your edits)

git reset HEAD\~2        \# undo last 2 commits

git pull                \# pull latest from GitHub

git push origin main \--verbose  \# push with detailed error output

### .gitignore — What to Always Exclude

.env                  \# API keys — NEVER commit

venv/                 \# virtual environment — machine specific

cover\_letters/        \# personal job applications

portfolio\_reports/    \# financial reports

job\_digests/          \# LinkedIn job digests

\_\_pycache\_\_/          \# Python cache files

### .env File Pattern

\# .env (never committed)

ANTHROPIC\_API\_KEY=sk-ant-...

GMAIL\_ADDRESS=your@gmail.com

GMAIL\_APP\_PASSWORD=xxxx-xxxx-xxxx-xxxx

\# .env.example (committed — shows what variables are needed)

ANTHROPIC\_API\_KEY=your-key-here

GMAIL\_ADDRESS=your-gmail-here

GMAIL\_APP\_PASSWORD=your-app-password-here

---

## 3\. Python Concepts

### Imports

import anthropic              \# import whole library → use as anthropic.Anthropic()

from dotenv import load\_dotenv  \# import one thing → use directly as load\_dotenv()

from datetime import datetime, timedelta  \# import multiple things from one library

### Functions

def function\_name(input1, input2):

    """What this function does."""

    \# work happens here

    return result           \# hand back the output

- `def` defines a reusable block of code  
- Parameters are the inputs (in parentheses)  
- `return` hands data back to whoever called the function

### Dictionaries

\# Define

POSITIONS \= {

    "NTAP": {"name": "NetApp", "shares": 1900},

    "NVDA": {"name": "NVIDIA", "shares": 25},

}

\# Loop — three ways:

for ticker in POSITIONS:              \# keys only → "NTAP", "NVDA"

for pos in POSITIONS.values():        \# values only → {"name":...}, {"name":...}

for ticker, pos in POSITIONS.items(): \# both → use when you need key AND value

### f-strings — Variable Substitution

name \= "Adam"

price \= 140.50

print(f"Hello {name}, NTAP is at ${price:.2f}")

\# Output: Hello Adam, NTAP is at $140.50

Curly braces `{}` are substitution slots — Python replaces them with the variable's value at runtime.

### Regular Expressions

import re

re.split(r'-{10,}', text)      \# split text at 10+ dashes

re.search(r'pattern', text)    \# find first match — returns match object or None

re.findall(r'pattern', text)   \# find ALL matches — returns list

re.sub(r'pattern', 'new', text) \# replace matches with something else

\# Capture groups — extract specific parts

url\_match \= re.search(r'jobs/view/(\\d+)', url)

if url\_match:

    job\_id \= url\_match.group(1)  \# group(0)=full match, group(1)=first capture

\# Common patterns

r'\\d+'     \# one or more digits

r'\\w+'     \# one or more word characters

r'\\.''     \# literal dot (. alone means "any character")

r'-{10,}'  \# 10 or more dashes

### Data Flow Through Functions (Parameter Relay)

\# Data flows like a relay race — each function passes to the next

main()                          \# ticker \= "NTAP"

  → build\_stock\_summary(ticker) \# receives "NTAP", passes it on

    → get\_quote(ticker)         \# receives "NTAP"

      → fetch\_fmp(f"quote/{ticker}") \# "NTAP" fills into URL

### timedelta — Date Math

from datetime import datetime, timedelta

\# 7 days ago

since \= datetime.now() \- timedelta(days=7)

since\_str \= since.strftime("%d-%b-%Y")  \# "22-May-2026" — IMAP format

---

## 4\. Claude API

### Basic API Call Pattern

import anthropic

from dotenv import load\_dotenv

load\_dotenv()                    \# reads .env file

client \= anthropic.Anthropic()   \# creates connection, auto-reads ANTHROPIC\_API\_KEY

message \= client.messages.create(

    model="claude-sonnet-4-5",   \# which Claude model to use

    max\_tokens=1024,             \# max response length (\~750 words)

    system="You are a...",       \# sets Claude's role/behavior (optional)

    messages=\[

        {"role": "user", "content": "Your question here"}

    \]

)

print(message.content\[0\].text)   \# extract the text response

### Key Parameters

| Parameter | What it does |
| :---- | :---- |
| `model` | Which Claude version (`claude-sonnet-4-5` is current stable) |
| `max_tokens` | Cap on response length — 1024 is good for most tasks |
| `system` | System prompt — sets Claude's persona and behavior |
| `messages` | List of conversation turns with `role` and `content` |

### System Prompts

The `system` parameter is separate from the user message. It shapes how Claude responds to everything — think of it as a briefing before the conversation starts. The more specific, the better the output.

system="""You are an expert cover letter writer.

\- Be specific — reference actual job requirements

\- Keep to 3-4 paragraphs

\- Never use generic phrases like 'I am excited to apply'"""

### The `client` Namespaces

client.messages        \# conversational AI calls ← used most

client.models          \# list available models

client.batches         \# bulk requests (cheaper, async)

client.beta.messages   \# experimental features

### Discovering Available Methods

\# In VS Code — type client. and pause for autocomplete

\# In terminal:

python3 \-c "import anthropic; help(anthropic.Anthropic)"

---

## 5\. MCP Servers

### What MCP Is

Model Context Protocol — lets Claude connect to real tools and take actions, not just answer questions. Each MCP server gives Claude a new capability.

**Without MCP:** Claude answers based on what you type **With MCP:** Claude reads your files, searches the web, checks email, updates calendar

### Config File Location (Mac)

\~/Library/Application Support/Claude/claude\_desktop\_config.json

### Config File Structure

{

  "mcpServers": {

    "filesystem": {

      "command": "npx",

      "args": \["-y", "@modelcontextprotocol/server-filesystem", "/Users/Adam/DEV\_Space"\]

    }

  }

}

**Important:** Merge into existing config — don't replace it. Always quit and relaunch Claude Desktop after editing (`Cmd+Q` then reopen).

### Filesystem Server

Gives Claude read/write access to a specific folder on your Mac. Test it in Claude Desktop:

"Read my basic\_script.py file and tell me what it does"

### Available MCP Servers

| Server | What it gives Claude |
| :---- | :---- |
| filesystem | Read/write local files |
| GitHub | Read repos, create issues, review PRs |
| Gmail | Read/send email |
| Google Calendar | Read/create calendar events |
| Google Drive | Access Drive files |
| Brave Search | Real-time web search |

---

## 6\. Agents Built

### Agent 1 — Hello Claude (`basic_script.py`)

First Claude API call. Sends a message, prints the response. **Concepts:** imports, client setup, messages.create, extracting response text

---

### Agent 2 — Job Search Assistant (`job_assistant.py`)

Reads job descriptions, drafts tailored cover letters, saves to files.

**Run:**

python3 job\_assistant.py

\# Paste job description → type END → enter a filename → get cover letter

**Key concepts:** system prompts, multi-line input, file saving with timestamps, `os.makedirs`, `MY_BACKGROUND` as resume context

**Output:** Saves to `cover_letters/YYYYMMDD_HHMMSS_job-title.txt`

---

### Agent 3 — Portfolio Monitor (`portfolio_monitor.py`)

Fetches live stock data for 13 positions, calculates gain/loss, gets analyst ratings and news, sends Claude's analysis as an HTML email every weekday at 8am.

**Run:**

python3 portfolio\_monitor.py

**Schedule (cron):**

0 8 \* \* 1-5 /Users/Adam/DEV\_Space/ai\_practice/venv/bin/python3 /Users/Adam/DEV\_Space/ai\_practice/portfolio\_monitor.py \>\> /Users/Adam/DEV\_Space/ai\_practice/portfolio\_reports/cron.log 2\>&1

**Your Positions:** | Ticker | Shares | Cost Basis | |---|---|---| | NTAP | 1,900 | ESPP/RSU mix — see Etrade | | CDE | 150 | $14.996 | | HIMS | 100 | $25.45 | | LAC | 50 | $7.156 | | NTSK | 90 | $21.33 | | NVDA | 25 | $120.45 | | NVO | 5 | $147.254 | | NVTS | 200 | $15.145 | | QBTS | 168 | $9.518 | | RIOT | 30 | $10.22 | | RIVN | 100 | $12.64 | | SOFI | 100 | $9.30 | | ZS | 9 | $133.41 |

**Note:** 200 NTAP RSU shares (grant RS100768, vest Aug 2026\) forfeited — excluded. \~82 additional ESPP shares expected end of May 2026\.

**Data source:** `yfinance` (free, no API key, pulls from Yahoo Finance) **Key concepts:** dictionary loops, `.items()`, f-strings, HTML email, SMTP, cron

---

### Agent 4 — LinkedIn Job Alert Agent (`job_alert_agent.py`)

Reads LinkedIn job alert emails from Gmail, scores each job against your resume using Claude (0-100), filters to top matches, sends ranked HTML digest daily.

**Run:**

python3 job\_alert\_agent.py

**Schedule (cron):**

0 9 \* \* 1-5 /Users/Adam/DEV\_Space/ai\_practice/venv/bin/python3 /Users/Adam/DEV\_Space/ai\_practice/job\_alert\_agent.py \>\> /Users/Adam/DEV\_Space/ai\_practice/job\_digests/cron.log 2\>&1

**Scoring breakdown (25 pts each):**

- Title Fit — does the job title match Senior EM/Director/VP target?  
- Skill Match — do required skills match your background?  
- Seniority Level — is it the right level?  
- Industry Fit — enterprise tech, cloud, AI/ML, storage?

**Threshold:** Jobs scoring 60+ are included. Change `SCORE_THRESHOLD` in script.

**Gmail setup needed:**

- Yahoo Mail → forward LinkedIn alerts to Gmail  
- Gmail → enable IMAP (Settings → Forwarding and POP/IMAP)  
- Gmail App Password → myaccount.google.com → Security → App Passwords

**Key concepts:** IMAP email reading, regex parsing, heuristic text extraction, JSON scoring via Claude, HTML digest, deduplication

---

## 7\. Key Commands

### Daily Workflow

cd /Users/Adam/DEV\_Space/ai\_practice  \# go to repo

source venv/bin/activate               \# activate environment

python3 script\_name.py                 \# run a script

deactivate                             \# when done

### Git

git status

git add .

git commit \-m "message"

git push origin main

git pull

### Cron

crontab \-e        \# edit scheduled tasks

crontab \-l        \# list current scheduled tasks

### Cron Time Format

\* \* \* \* \*  command

│ │ │ │ └── day of week (0=Sun, 1=Mon ... 5=Fri, 1-5=weekdays)

│ │ │ └──── month (1-12)

│ │ └────── day of month (1-31)

│ └──────── hour (0-23)

└────────── minute (0-59)

0 8 \* \* 1-5  \= 8:00am Monday through Friday

0 9 \* \* 1-5  \= 9:00am Monday through Friday

### Python

python3 \--version          \# check Python version

pip list | grep anthropic  \# check if library installed

pip install package-name   \# install a package (venv must be active)

pip3 show anthropic        \# show package details

---

## 8\. Troubleshooting Log

| Problem | Cause | Fix |
| :---- | :---- | :---- |
| `git: user.name not set` | Git needs identity before committing | `git config --global user.name "Your Name"` |
| `Can't push — remote rejected` | GitHub branch protection or secret scanning | Check Settings → Branches → Rules |
| `externally-managed-environment` | Homebrew Python blocks system pip | Use venv: `python3 -m venv venv` |
| `UNSEEN` emails \= 0 | Emails already read | Change IMAP search to `SINCE date` |
| MCP hammer icon missing | Version difference | Ask Claude "what tools do you have?" |
| `.env` not loading | `load_dotenv()` not called | Add `load_dotenv()` before API calls |
| `SyntaxError: invalid syntax` | Missing comma or bracket on previous line | Check the line ABOVE the error |
| `DeprecationWarning` on model | Old model name | Use `claude-sonnet-4-5` |
| `403 Forbidden` on FMP | Free tier limit | Switch to `yfinance` (free, no key needed) |
| Push rejected — secrets | API key in a commit | Remove from commit history, rotate the key |

---

*Last updated: May 2026* *Repo: github.com/haywooda1/ai\_practice*  
