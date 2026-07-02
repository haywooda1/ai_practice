# Prep Guide: AWS Bedrock Fluency + AI Code Review Skills
*For the FMI / Jericho Cruz conversation*

---

## PART 1: AWS Bedrock — What It Is and How to Talk About It

### The one-sentence version
Bedrock is AWS's managed layer for calling foundation models (Claude, Llama, Nova, etc.) through one consistent API, with AWS-native security, logging, and governance wrapped around it — so a company doesn't have to build that plumbing themselves.

### The five building blocks (this is the map Jericho will expect you to know)

| Block | What it does | Why FMI would use it |
|---|---|---|
| **Model access** | One API (the "Converse" API) to call Claude, Llama, Nova, Mistral, etc. — same request shape, same IAM role, same logging, regardless of model | Lets FMI pick Claude (or swap models later) without rebuilding the app |
| **Knowledge Bases** | Managed RAG — ingests FMI's documents (S3), chunks/embeds them, handles retrieval, answers with citations | This is *the* mechanism for "internal safe LLM for field consultants" — it's how consultants query FMI's own content instead of the model's general knowledge |
| **Guardrails** | Policy layer: content filters, PII redaction, denied topics, hallucination/grounding checks, prompt-injection defense | This is the "safe" in "safe LLM" — it's a configurable, auditable control layer, not just a system prompt asking the model to behave |
| **Agents / AgentCore** | Lets a model take multi-step actions — call internal APIs, look things up, execute a workflow | Relevant if this grows beyond Q&A into "do something for me" (e.g., pull a project spec, draft an estimate) |
| **Governance/observability** | IAM roles, KMS encryption, CloudWatch logs, CloudTrail audit trail | This is what a CIO actually gets evaluated on — who can access what, what was asked, what was answered |

### The critical fact to know cold
**AWS Bedrock does not send your prompts or data back to the model provider.** When FMI calls Claude through Bedrock, Anthropic never sees the traffic, never logs it, never trains on it. This is *the* answer to "is this actually safe" — data stays inside FMI's AWS account/VPC, governed by their own IAM and KMS keys. If Jericho asks "how is this different from just using ChatGPT," this is your answer.

### How this maps directly to FMI's use case
"Internal safe LLM for field consultants" is almost certainly this architecture:

```
Field consultant question
    → Guardrails check input (block PII leakage, off-topic, prompt injection)
    → Knowledge Base retrieves relevant FMI documents (project data, standards, past reports)
    → Claude generates an answer grounded in those documents
    → Guardrails check output (contextual grounding — did it stay faithful to the source, or hallucinate?)
    → Answer returned, logged to CloudWatch for audit
```

That's a RAG chatbot pattern — the most common, most "boring," most provably-safe Bedrock deployment. You don't need to know how to build it yourself. You need to be able to describe this flow fluently and ask the right ownership questions.

### Talk track — phrases that signal fluency without overclaiming depth
- "The core question with Bedrock isn't really 'can the model answer the question' — it's whether the Knowledge Base retrieval is grounded correctly and whether Guardrails are configured tightly enough that you're not just trusting a system prompt."
- "Since Bedrock keeps the data in FMI's own AWS account, the security story is really an IAM and access-control story more than a model story — that's familiar territory for me from platform governance."
- "I'd want to know: is this single-tenant per consultant group, or one shared knowledge base? That changes how you think about document permissions."

### Smart questions to ask Jericho (shows ownership thinking, not just curiosity)
1. "Is the plan to use Bedrock's managed Knowledge Bases, or a custom vector store — and who's currently accountable for what goes into the document corpus?"
2. "What's driving the vendor selection — Bedrock specifically, or is that still open? Have you looked at Guardrails configurations yet, or is that still greenfield?"
3. "When you say 'own delivery and manage vendors' — is there already an AWS or SI partner engaged, or would I be building that relationship from scratch?"
4. "What does 'safe' mean to FMI specifically — is it data residency/compliance-driven, hallucination risk, or both?"

These questions do double duty: they show Bedrock fluency *and* they're the exact questions a delivery owner should be asking on day one.

---

## PART 2: Reading AI-Generated Code Like a Reviewer, Not a User

You've built four working agents — that's real, relevant experience. The gap Jericho is describing isn't "can you write Python," it's "can you catch what a junior engineer's AI tool quietly got wrong." That's a different skill: pattern recognition, not syntax fluency. Below is the actual checklist experienced reviewers use.

### The core mental shift
AI-generated code almost always **looks correct and runs on the happy path**. The failure modes show up at the edges: bad input, network hiccups, concurrent access, scale. Your job in review isn't "does this work" — it's "what happens when it doesn't."

### The 8 failure patterns to scan for every time

**1. Swallowed exceptions (the #1 AI code smell)**
```python
# Red flag — hides every possible failure
try:
    result = call_api(data)
except Exception:
    pass
```
Ask: *"What happens when this fails — do we know it failed, or does it just silently do nothing?"* Good code catches specific exceptions and either logs, retries, or re-raises.

**2. Mutable default arguments**
```python
# Red flag — the list persists across calls, causing bugs that appear "randomly"
def add_item(item, items=[]):
    items.append(item)
    return items
```
This is a classic AI-generated bug because it's syntactically valid and works fine in a single test run. Ask: *"Did you test this function called twice in a row?"*

**3. No input validation at the boundary**
AI code often assumes inputs are well-formed. Look for functions that immediately index into a dict, parse a date, or divide, with no check that the value exists or is the expected shape.
```python
# Red flag
def get_price(response):
    return response['data']['price']  # KeyError waiting to happen
```
Ask: *"What does this do if the API returns an error payload instead of the expected shape?"*

**4. Hardcoded secrets or credentials pasted into code**
AI assistants will happily generate `api_key = "sk-..."` if that's what the prompt implied. Scan every new file for literal keys, tokens, connection strings.

**5. No idempotency / retry safety**
```python
# Red flag — if this runs twice (retry, cron overlap), you double-charge/double-send
def process_payment(order_id):
    charge_customer(order_id)
    send_confirmation_email(order_id)
```
Ask: *"If this function runs twice for the same input — network retry, duplicate cron trigger — what breaks?"* This is especially relevant given your own cron-scheduled agents; you already have instincts here even if you haven't named it "idempotency" before.

**6. Blocking calls inside loops with no rate-limit awareness**
```python
# Red flag — no backoff, no rate limit handling, will get throttled or banned
for item in large_list:
    response = requests.get(api_url + item)
```
Ask: *"What's the rate limit on this API, and what happens to this loop when we hit it?"*

**7. Resource leaks — files, connections, sessions not closed**
```python
# Red flag
f = open("data.txt")
data = f.read()
# no f.close(), no context manager
```
Should be `with open(...) as f:`. AI-generated code frequently skips context managers, especially in longer generated blocks where the "close" step gets dropped.

**8. Overconfident comments / docstrings that don't match the code**
AI tools often generate a docstring describing what the function *should* do, which silently drifts from what it *actually* does after a human edits the body. This is a real tell — read the docstring, then read the code, and check they still agree.

### The 5 questions that catch AI-generated code in review (use these live)
1. "Walk me through what happens if this input is empty / null / malformed."
2. "What happens if this runs twice, or two of these run at the same time?"
3. "Where does this fail silently vs. loudly — and is that intentional?"
4. "Did you write this, or did a tool generate it — and if a tool, what did you change?" (Not gotcha — normalizes disclosure, which is what you actually want as a manager.)
5. "Show me the test for the failure case, not just the success case."

### Why this framing works for the FMI conversation specifically
Jericho told you he's spending 75% of his time correcting AI output. That means his real pain isn't "the model writes bad code" — it's "nobody on the team has a systematic way to catch it before it reaches him." You coaching junior engineers to internalize the 8 patterns above *is* the fix to his stated problem. That's a stronger pitch than claiming deep hands-on coding chops you don't have: you're offering a review discipline and a coaching framework, which is a leadership skill, not a syntax skill.

---

## Quick-reference: What to say if asked directly about your depth
- **On Bedrock:** "I haven't built a Bedrock deployment myself, but I understand the architecture — Knowledge Bases for RAG, Guardrails for the safety layer, and the fact that your data never leaves your AWS account when you call a model through it. I'd want to pair with an AWS SA or SI partner on the initial build, but I can own the delivery, the vendor relationship, and the governance model."
- **On code review:** "My own hands-on Python is function-level — I've built and run four working AI agents on cron schedules. Where I add value isn't writing production code myself, it's the review discipline: knowing the failure patterns AI-generated code tends to hide, and asking the questions that surface them before they reach production."

Both of these are honest, and both reframe "gap" as "exactly the leadership role you're hiring for."
