# Python Notes
*Reference log for Python concepts, patterns, and learnings*

---

## Table of Contents
- [Environment & Tooling](#environment--tooling)
  - [Virtual Environment (venv)](#virtual-environment-venv)
  - [.env File Pattern](#env-file-pattern)
  - [Python Key Commands](#python-key-commands)
- [Where to Find Modules & Packages](#where-to-find-modules--packages)
- [Standard Library Quick Reference](#standard-library-quick-reference)
- [Python Concepts](#python-concepts)
  - [Imports](#imports)
  - [Functions](#functions)
  - [Dictionaries](#dictionaries)
  - [f-strings](#f-strings--variable-substitution)
  - [Regular Expressions](#regular-expressions)
  - [File I/O — The open() Function](#file-io--the-open-function)
  - [Pandas — Working with Tabular Data](#pandas--working-with-tabular-data)
  - [Data Flow Through Functions](#data-flow-through-functions-parameter-relay)
  - [timedelta — Date Math](#timedelta--date-math)
- [Claude API in Python](#claude-api-in-python)
  - [Basic API Call Pattern](#basic-api-call-pattern)
  - [Key Parameters](#key-parameters)
  - [System Prompts](#system-prompts)
  - [The client Namespaces](#the-client-namespaces)
- [Reading Files into Lists](#reading-files-into-lists)
- [Python Troubleshooting](#python-troubleshooting)

---

## Environment & Tooling

### Virtual Environment (venv)

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
Each project gets its own isolated set of packages — no conflicts between projects.

---

### .env File Pattern

Every script that uses API keys or credentials follows this pattern:

```bash
# .env  (never committed — add to .gitignore)
ANTHROPIC_API_KEY=sk-ant-...
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

# .env.example  (committed — shows teammates what variables are needed)
ANTHROPIC_API_KEY=your-key-here
GMAIL_ADDRESS=your-gmail-here
GMAIL_APP_PASSWORD=your-app-password-here
```

**In Python — loading the .env file:**
```python
from dotenv import load_dotenv
import os

load_dotenv()                        # reads .env into environment
api_key = os.getenv("ANTHROPIC_API_KEY")  # retrieve a value
```

**Convention across all scripts:** always use `GMAIL_ADDRESS` and
`GMAIL_APP_PASSWORD` as the variable names — this is the established
standard across the codebase.

**Common mistake:** forgetting `load_dotenv()` before the first `os.getenv()`
call — the variable comes back `None` and you get cryptic auth errors downstream.

---

### Python Key Commands

```bash
python3 --version               # check Python version
pip list | grep anthropic       # check if a library is installed
pip install package-name        # install a package (venv must be active)
pip3 show anthropic             # show package details and version
python3 -c "help('modules')"    # list ALL importable modules
```

---

## Where to Find Modules & Packages

### The Mental Model

```
Built-in to Python? → docs.python.org/3/library/   (just import, no install needed)
       ↓ not there
Need to install?    → pypi.org                      (pip install <package>)
       ↓ mid-coding
Need to explore?    → dir() and help() in the REPL
       ↓ stuck
Need examples?      → Stack Overflow, realpython.com, or ask Claude
```

### Key Resources

| Resource | URL | What it's for |
|---|---|---|
| Python Standard Library | `docs.python.org/3/library/` | Every built-in module — bookmark this |
| PyPI | `pypi.org` | Third-party packages you `pip install` |
| Real Python | `realpython.com` | Tutorials and practical guides |

### Exploring Modules Interactively

```python
# See everything a module exposes
import csv
dir(csv)

# Read built-in docs without leaving the terminal
help(csv)
help(csv.DictReader)

# See ALL importable modules (takes a moment)
python -c "help('modules')"
```

### Standard Library vs. Third-Party — How to Tell

- **Standard library** (no install): `csv`, `json`, `pathlib`, `os`, `re`, `datetime` — these will NOT appear in `requirements.txt`
- **Third-party** (pip install required): `anthropic`, `pandas`, `openpyxl`, `yfinance`, `dotenv` — these WILL be in `requirements.txt` and your `venv`

---

## Standard Library Quick Reference

Modules that come up constantly — no `pip install` needed:

| Module | What it does | Common use |
|---|---|---|
| `csv` | Read/write CSV files | `csv.DictReader`, `csv.writer` |
| `json` | Parse/write JSON | `json.loads()`, `json.dumps()` |
| `pathlib` | File and directory paths | `Path("file.txt").read_text()` |
| `os` | OS interaction, env vars | `os.getenv()`, `os.path.exists()` |
| `datetime` | Dates, times, formatting | `datetime.now()`, `strftime()` |
| `re` | Regular expressions | `re.search()`, `re.findall()` |
| `collections` | Specialized containers | `Counter`, `defaultdict`, `namedtuple` |
| `logging` | Proper logging | Replaces `print()` in production scripts |
| `argparse` | CLI argument parsing | Scripts that take command-line flags |
| `subprocess` | Run shell commands | `subprocess.run(["git", "status"])` |
| `smtplib` | Send email | Used under the hood in Gmail scripts |
| `itertools` | Iteration tools | Chaining, grouping, combinations |
| `functools` | Function utilities | `partial()`, `lru_cache()` |

---

## Python Concepts

### Imports

```python
import anthropic              # import whole library → use as anthropic.Anthropic()
from dotenv import load_dotenv  # import one thing → use directly as load_dotenv()
from datetime import datetime, timedelta  # import multiple things from one library
```

---

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

---

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

---

### f-strings — Variable Substitution

```python
name = "Adam"
price = 140.50
print(f"Hello {name}, NTAP is at ${price:.2f}")
# Output: Hello Adam, NTAP is at $140.50
```
Curly braces `{}` are substitution slots — Python replaces them with the variable's
value at runtime.

---

### Regular Expressions

```python
import re

re.split(r'-{10,}', text)       # split text at 10+ dashes
re.search(r'pattern', text)     # find first match — returns match object or None
re.findall(r'pattern', text)    # find ALL matches — returns list
re.sub(r'pattern', 'new', text) # replace matches with something else

# Capture groups — extract specific parts
url_match = re.search(r'jobs/view/(\d+)', url)
if url_match:
    job_id = url_match.group(1)  # group(0)=full match, group(1)=first capture

# Common patterns
r'\d+'     # one or more digits
r'\w+'     # one or more word characters
r'\.'      # literal dot (. alone means "any character")
r'-{10,}'  # 10 or more dashes
```

---

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

---

### Pandas — Working with Tabular Data

Pandas is the standard library for reading and manipulating spreadsheet-style
data (CSVs, Excel exports) in Python. Used in `net_worth_snapshot.py` to read
Fidelity CSV exports.

**Import convention:**
```python
import pandas as pd
```

**Two core data structures:**
- **Series** — a single column of data (like one Excel column)
- **DataFrame** — a full table with rows and columns (like an Excel sheet)

**Loading data:**
```python
df = pd.read_csv("Etrade_Positions.csv")  # CSV → DataFrame
df.head()        # preview first 5 rows
df.columns       # list all column names
df.dtypes        # show data type of every column — int64, float64, object (string)
```

**`groupby()` — split into sub-tables by column value:**
```python
for account_name, group in df.groupby("Account Name"):
    # account_name = "Traditional IRA" (first loop), "401(K) PLAN" (second loop)
    # group = DataFrame containing only rows for that account
```
This is pandas' equivalent of "for each unique value in this column,
give me just the rows that match."

**`iterrows()` — loop through rows one at a time:**
```python
for _, row in group.iterrows():
    qty = row.get("Quantity", None)
```
- Returns `(index, row)` pairs — `_` discards the index since it's unused
- `row.get("ColumnName", default)` works like a dictionary lookup

**`pd.to_numeric()` — convert strings to numbers safely:**
```python
qty = pd.to_numeric(row.get("Quantity", None), errors="coerce")
```
- `"150"` → `150.0`
- `"1,234.5"` → `1234.5` (commas handled automatically)
- `errors="coerce"` → unconvertible values become `NaN` instead of crashing

**`pd.notna()` — check for missing/NaN values:**
```python
qty_str = f"{qty:,.3f}" if pd.notna(qty) else "–"
```
`NaN` (Not a Number) is pandas' marker for missing data. `pd.notna()` returns
`False` for `NaN`, letting you handle missing values gracefully.

**Other common operations:**
```python
df["Symbol"]                              # get one column as a Series
df[df["Quantity"] > 0]                    # filter rows by condition
df.sort_values("Value", ascending=False)  # sort by column
df["Value"].sum()                         # sum a column
df.fillna(0)                              # replace NaN with 0
```

**Why this matters:** CSV exports (Fidelity, Etrade) often store numbers as
text strings — especially if they contain `$`, `,`, or `%`. Always check
`df.dtypes` when debugging formatting errors — if a numeric column shows
`object` instead of `int64`/`float64`, that's your clue to add `pd.to_numeric()`.

**`index_col=False` — preventing column misalignment:**
```python
df = pd.read_csv(io.StringIO(csv_text), index_col=False)
```
If a CSV's data rows have a value in every column but pandas decides to use
the first column as the row index anyway, every other column's data shifts
left by one position relative to its header. Symptoms: `groupby("Account Name")`
returns symbol/ticker values instead of account names, dollar columns show
`$0.00` or `NaN` everywhere, and the leftmost "index" in printed output looks
like real data (e.g. account numbers).

**How to diagnose:** print a few columns side by side and compare to the raw CSV:
```python
print(df[["Account Name", "Symbol", "Current Value"]].to_string())
```
If the values look shifted by one column versus what you see in the raw CSV,
add `index_col=False` to `read_csv()`. This tells pandas "never use any column
as the row index — keep all columns as columns."

---

### Data Flow Through Functions (Parameter Relay)

```python
# Data flows like a relay race — each function passes to the next
main()                          # ticker = "NTAP"
  → build_stock_summary(ticker) # receives "NTAP", passes it on
    → get_quote(ticker)         # receives "NTAP"
      → fetch_fmp(f"quote/{ticker}") # "NTAP" fills into URL
```

---

### timedelta — Date Math

```python
from datetime import datetime, timedelta

# 7 days ago
since = datetime.now() - timedelta(days=7)
since_str = since.strftime("%d-%b-%Y")  # "22-May-2026" — IMAP format
```

---

## Claude API in Python

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

---

### Key Parameters

| Parameter | What it does |
|---|---|
| `model` | Which Claude version (`claude-sonnet-4-5` is current stable) |
| `max_tokens` | Cap on response length — 1024 is good for most tasks |
| `system` | System prompt — sets Claude's persona and behavior |
| `messages` | List of conversation turns with `role` and `content` |

---

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

---

### The `client` Namespaces

```python
client.messages        # conversational AI calls ← used most
client.models          # list available models
client.batches         # bulk requests (cheaper, async)
client.beta.messages   # experimental features
```

**Discovering available methods:**
```python
# In VS Code — type client. and pause for autocomplete
# In terminal:
python3 -c "import anthropic; help(anthropic.Anthropic)"
```

---

## Reading Files into Lists

### Pattern: one function per file type, all return a plain Python list

```python
import csv
import json
import pathlib
```

### 1. Plain Text → `list[str]`

```python
def read_text_to_list(filepath: str) -> list[str]:
    """One item per non-empty line."""
    path = pathlib.Path(filepath)
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]
```

**Key concepts:**
- `pathlib.Path` is the modern way to work with file paths (replaces `os.path`)
- `.read_text()` opens, reads, and closes the file in one call
- `.splitlines()` handles `\n`, `\r\n`, and `\r` line endings correctly
- List comprehension filters and strips in one pass

---

### 2. CSV → `list[dict]` or `list[list]`

```python
def read_csv_to_list(filepath: str, has_header: bool = True) -> list:
    with open(filepath, newline="", encoding="utf-8") as fh:
        if has_header:
            reader = csv.DictReader(fh)
            return [dict(row) for row in reader]
        else:
            return list(csv.reader(fh))
```

**Key concepts:**
- `newline=""` is required by the csv module — skipping it causes bugs on Windows
- `csv.DictReader` uses the first row as column names → gives you `{"col": value}` dicts
- `csv.reader` (no Dict) gives positional lists → `["val1", "val2"]`
- Always prefer `DictReader` when the file has headers — much easier to work with

---

### 3. JSON → `list`

```python
def read_json_to_list(filepath: str, key: str | None = None) -> list:
    data = json.loads(pathlib.Path(filepath).read_text(encoding="utf-8"))
    if key:
        return data[key]           # {"jobs": [...]}  →  data["jobs"]
    if isinstance(data, list):
        return data                # root is already a list
    return list(data.values())     # root is a dict — return values as list
```

**Key concepts:**
- `json.loads()` parses a JSON *string*; `json.load()` reads from a file object — both work
- Most API responses wrap data in a dict: `{"results": [...]}` — use the `key` parameter
- `isinstance(data, list)` is a type check — lets the function handle both shapes

---

### 4. XLSX → `list[dict]`

```python
# pip install openpyxl
from openpyxl import load_workbook

def read_xlsx_to_list(filepath: str, sheet: str | int = 0,
                      has_header: bool = True) -> list:
    wb = load_workbook(filepath, read_only=True, data_only=True)
    ws = wb[sheet] if isinstance(sheet, str) else wb.worksheets[sheet]
    rows_iter = ws.iter_rows(values_only=True)
    if has_header:
        headers = [str(h) for h in next(rows_iter)]
        result = [dict(zip(headers, row)) for row in rows_iter]
    else:
        result = list(rows_iter)
    wb.close()
    return result
```

**Key concepts:**
- `read_only=True` — critical for large files; without it openpyxl loads everything into RAM
- `data_only=True` — returns cell values, not formulas
- `next(rows_iter)` pulls the first row (headers) off the iterator
- `zip(headers, row)` pairs header names with values → then `dict()` makes it a dict
- `wb.close()` — always close workbooks opened in read-only mode

---

### Using any of these — the pattern is identical regardless of source

```python
items = read_csv_to_list("jobs.csv")     # or txt, json, xlsx
for item in items:
    print(item["title"])                  # same dict access pattern
```

---

## Python Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `externally-managed-environment` | Homebrew Python blocks system pip | Use venv: `python3 -m venv venv` then activate |
| `.env` not loading / `None` values | `load_dotenv()` not called before `os.getenv()` | Add `load_dotenv()` at the top of the script before any `os.getenv()` calls |
| `SyntaxError: invalid syntax` | Missing comma or bracket on previous line | Check the line ABOVE the one the error points to |
| `DeprecationWarning` on model name | Old model string passed to API | Use `claude-sonnet-4-5` |
| `403 Forbidden` on FMP | Free tier rate limit hit | Switch to `yfinance` — free, no key needed |
| `pd.read_csv` columns shifted left by one | First column absorbed as DataFrame index | Add `index_col=False` to `pd.read_csv()` |
| `groupby()` returns wrong values (symbols instead of account names) | Symptom of the column-shift above | Diagnose with `df[["col1","col2"]].to_string()`, then fix `read_csv` |
| Package not found after installing | venv not activated | Run `source venv/bin/activate` first |
| `ModuleNotFoundError` | Library not installed in active venv | `pip install <package>` with venv active |

---

## Classes, Dataclasses & Decorators

### Type Hints — Labels, Not Enforcement

```python
def parse_news_item(raw: dict) -> NewsItem | None:
```

Type hints are **passive annotations** — Python ignores them at runtime.
They exist to communicate intent to humans and tools like VS Code autocomplete.

| Hint | Meaning |
|---|---|
| `param: str` | This parameter should be a string |
| `param: dict` | This parameter should be a dictionary |
| `-> str` | This function returns a string |
| `-> list[str]` | Returns a list where every item is a string |
| `-> NewsItem \| None` | Returns either a NewsItem object or None |

The `|` means "or" — called a **union type**. Common for functions that
might not always have something valid to return.

Removing all type hints doesn't change behavior — only readability:
```python
def parse_news_item(raw):   # identical behavior, less self-documenting
```

---

### `@dataclass` — Auto-Generated Classes

```python
from dataclasses import dataclass

@dataclass
class NewsItem:
    title:     str
    published: str
    link:      str
```

A `class` is a blueprint for a custom data type — an object that bundles
related pieces of data together. Without `@dataclass` you'd write boilerplate
by hand:
```python
# What @dataclass generates automatically:
class NewsItem:
    def __init__(self, title, published, link):
        self.title     = title
        self.published = published
        self.link      = link
```

**Creating and using an instance:**
```python
item = NewsItem(title="NVDA Surges", published="2026-06-15", link="https://...")
print(item.title)      # "NVDA Surges"
```

**Why a dataclass instead of a plain dict?**
- VS Code autocompletes `item.title` — it knows the field names exist
- Harder to misspell a key name than with `item["titel"]`
- Reads cleaner: `item.title` vs `item["title"]`

---

### Decorators — The `@` Syntax

A decorator wraps a function or class and adds behavior to it automatically.
The `@` symbol is always the signal.

```python
@dataclass          # ← decorator
class NewsItem:
    ...
```

`@dataclass` is Python's built-in decorator that auto-generates class setup
code. You'll also see `@staticmethod`, `@classmethod`, `@property`, and
custom decorators in libraries. Recognize the pattern: "this class/function
has been enhanced by something" — you don't need to know how it works
internally to use it correctly.

---

### Dunder Methods — `__init__`, `__name__`, etc.

**Dunder** = "double underscore" on both sides. Python calls these
automatically in response to built-in operations — you don't call them
directly yourself.

| Dunder | Triggered by | What it does |
|---|---|---|
| `__init__` | `MyClass(...)` | Initializes a new instance — the constructor |
| `__str__` | `print(obj)` or `str(obj)` | How to display the object as a string |
| `__len__` | `len(obj)` | What to return for the object's length |
| `__eq__` | `obj1 == obj2` | How to compare two objects for equality |
| `__repr__` | In the REPL or debugger | Developer-readable representation |

**`__init__` — the constructor:**
```python
class NewsItem:
    def __init__(self, title, published, link):
        self.title     = title    # store input as instance attribute
        self.published = published
        self.link      = link

# Python calls __init__ automatically — you never call it directly:
item = NewsItem("NVDA Surges", "2026-06-15", "https://...")
#               ↑ triggers __init__ with these three values
```

**`__name__` — the module identity variable:**
```python
if __name__ == "__main__":
    main()
```
When Python runs a script **directly** (`python3 script.py`), it sets
`__name__` to `"__main__"`. When a script is **imported** by another script,
`__name__` is set to the module's filename instead.

This guard means: "only run `main()` if this file is run directly, not if
it's imported." All your scripts have this at the bottom.

**General rule:** when you see `__something__`, ask "what built-in operation
triggers this?" not "how do I call this?"

---

### Variable Scope — Parameters vs Arguments

**Parameters** are the names defined inside a function signature.
**Arguments** are the actual values passed in by the caller. The names
on each side are completely independent — only position matters.

```python
# "raw" is the PARAMETER — chosen by the function author
def parse_news_item(raw: dict) -> NewsItem | None:
    content = raw.get("content") or {}

# "raw_news" is the ARGUMENT — chosen by the caller
raw_news = {"title": "NVDA Surges", ...}
item = parse_news_item(raw_news)
```

When called, Python binds the argument to the parameter name behind the
scenes:
```python
raw = raw_news   # happens automatically
```

The caller could name their variable anything — `abc_news`, `my_data`, `x`
— and inside the function it's still accessed as `raw`, because that's
what the function defined.

```
CALLER SIDE          │  FUNCTION SIDE
─────────────────────┼──────────────────
raw_news  ──────────►│  raw
abc_news  ──────────►│  raw     (same thing)
my_data   ──────────►│  raw     (same thing)
```

**Scope** means variables inside a function only exist inside that function
— they don't leak out, and outside variables don't leak in.

**Analogy:** a vending machine doesn't care if you call your dollar "my
crumpled bill" or "the one in my pocket." Inside the machine it's just
"input currency."

---

### `or` as a Value Selector (not just True/False)

Python's `or` returns the **first truthy value it finds**, or the last
value if none are truthy — not just `True`/`False`.

```python
None  or "hello"        # → "hello"
""    or "hello"        # → "hello"
"hi"  or "hello"        # → "hi"   (first truthy wins)
None  or None  or ""   # → ""    (last value if all falsy)
```

**Used as a waterfall of fallbacks:**
```python
title = (
    content.get("title")    # try here first
    or raw.get("title")     # fall back to here
    or ""                   # final default
).strip()
```

**Used as a safe default:**
```python
content = raw.get("content") or {}   # if None, use empty dict instead
```

**Truthiness** — these are all falsy (evaluate to False in an `if`):
```python
None, "", 0, 0.0, [], {}, set()
```
Everything else is truthy — why `if line.strip()` works as an emptiness
check without `if line.strip() != ""`.

---

### Early Return / Guard Clause

Check for bad/invalid input at the top of a function and bail out
immediately rather than letting bad data flow deeper into the code.

```python
def parse_news_item(raw: dict) -> NewsItem | None:
    content = raw.get("content") or {}
    title = (content.get("title") or raw.get("title") or "").strip()

    if not title:
        return None    # ← early return / guard clause

    # everything below here is guaranteed to have a valid title
```

The calling code handles the `None`:
```python
for raw_item in news_list:
    item = parse_news_item(raw_item)
    if item is None:
        continue    # skip this one, move to next
    print(item.title)   # safe — we know it's a real NewsItem
```

**Why guard clauses matter:** they flatten the code. Without them you'd
have deeply nested `if/else` blocks. With them, the happy path stays at
the top level and edge cases exit early.

---

### List Comprehensions

A compact way to build a list by looping and optionally filtering — all
in one expression.

```python
# Regular for loop:
result = []
for line in lines:
    stripped = line.strip()
    if stripped:
        result.append(stripped)

# Equivalent list comprehension — same result, one line:
result = [line.strip() for line in lines if line.strip()]
```

**The structure:**
```python
[ expression   for item in iterable   if condition ]
#  ↑ output      ↑ loop                 ↑ filter (optional)
```

**Common examples:**
```python
[x * 2 for x in [1, 2, 3]]          # → [2, 4, 6]
[s for s in words if len(s) > 3]    # → keep only strings longer than 3 chars
[job["title"] for job in jobs]      # → extract one field from a list of dicts
[l.strip() for l in lines if l.strip()]   # ← used in read_text_to_list
```

Use list comprehensions when the logic is simple and fits on one line.
Use a regular for loop when the logic is complex or needs multiple steps
— readability matters more than brevity.

---

## Token Usage Tracking

Every `client.messages.create()` response includes a `usage` attribute
with token counts. This pattern is added to `portfolio_monitor.py`,
`job_assistant.py`, and `job_alert_agent.py`.

```python
# After client = anthropic.Anthropic()
token_log = {"input": 0, "output": 0}

def log_usage(response):
    """Accumulate token usage from any API response."""
    token_log["input"]  += response.usage.input_tokens
    token_log["output"] += response.usage.output_tokens

def print_token_summary():
    """Print token usage and estimated cost at end of run."""
    input_cost  = token_log["input"]  / 1_000_000 * 3.00
    output_cost = token_log["output"] / 1_000_000 * 15.00
    total       = input_cost + output_cost
    print(f"Input:  {token_log['input']:,} tokens  (${input_cost:.4f})")
    print(f"Output: {token_log['output']:,} tokens  (${output_cost:.4f})")
    print(f"Total:  ${total:.4f} this run")
```

**Call `log_usage` after every API call, `print_token_summary` at the end of `main()`:**
```python
message = client.messages.create(...)
log_usage(message)              # right after the call
return message.content[0].text

# ... at the very end of main():
print_token_summary()
```

**Where `response.usage` comes from** — the Message object has multiple
attributes; `usage` is one of them, same pattern as `content[0].text`:
```
Message
  ├── content[0].text   ← the text Claude wrote
  ├── model             ← "claude-sonnet-4-5"
  ├── stop_reason       ← why Claude stopped
  └── usage
        ├── input_tokens   ← tokens your prompt used
        └── output_tokens  ← tokens Claude's response used
```

**Pricing for `claude-sonnet-4-5`:** $3.00 / 1M input tokens,
$15.00 / 1M output tokens. Check current pricing at
`console.anthropic.com/settings/billing`.

**Discover what's on any response object:**
```python
message = client.messages.create(...)
print(message)   # prints the full object — shows all available attributes
```

---
*Last updated: 2026-06-25*
