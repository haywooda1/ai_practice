import os
import anthropic
import yfinance as yf
# Adding for GMAIL support
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
#
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ─────────────────────────────────────────────
# YOUR PORTFOLIO — pulled from Etrade 05/28/26
# NTAP: sellable shares from NTAP_EtradeStatus
# Others: from Etrade_Positions.csv
# Note: 200 unvested NTAP RSU shares (RS100768,
#       vest Aug 2026) excluded — forfeited.
# ~82 additional NTAP ESPP shares expected
#       end of May 2026 not yet included.
# ─────────────────────────────────────────────
POSITIONS = {
    "NTAP": {
        "name": "NetApp",
        "shares": 1900,
        "cost_basis": None,  # ESPP/RSU mix — gain tracked in Etrade
        "note": "ESPP + RSU mix. Etrade shows $266,912 est. market value across lots."
    },
    "CDE":  {"name": "Coeur Mining",          "shares": 150, "cost_basis": 14.996133},
    "HIMS": {"name": "Hims & Hers Health",    "shares": 100, "cost_basis": 25.45},
    "LAC":  {"name": "Lithium Americas",      "shares": 50,  "cost_basis": 7.1558},
    "NTSK": {"name": "NetSTAKE",              "shares": 90,  "cost_basis": 21.33},
    "NVDA": {"name": "NVIDIA",                "shares": 25,  "cost_basis": 120.45},
    "NVO":  {"name": "Novo Nordisk",          "shares": 5,   "cost_basis": 147.254},
    "NVTS": {"name": "Navitas Semiconductor", "shares": 200, "cost_basis": 15.145},
    "QBTS": {"name": "D-Wave Quantum",        "shares": 168, "cost_basis": 9.517976},
    "RIOT": {"name": "Riot Platforms",        "shares": 30,  "cost_basis": 10.22},
    "RIVN": {"name": "Rivian",                "shares": 100, "cost_basis": 12.64},
    "SOFI": {"name": "SoFi Technologies",     "shares": 100, "cost_basis": 9.30},
    "ZS":   {"name": "Zscaler",               "shares": 9,   "cost_basis": 133.41},
}

client = anthropic.Anthropic()


def format_currency(val):
    if val is None:
        return "N/A"
    return f"${val:,.2f}"


def format_pct(val):
    if val is None:
        return "N/A"
    arrow = "▲" if val >= 0 else "▼"
    return f"{arrow} {abs(val):.2f}%"


def get_stock_data(ticker):
    """Fetch all data for one ticker using yfinance."""
    try:
        t    = yf.Ticker(ticker)
        info = t.info

        # Current price
        price = (
            info.get("currentPrice") or
            info.get("regularMarketPrice") or
            info.get("previousClose")
        )

        # Daily change
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        change     = (price - prev_close) if price and prev_close else None
        change_pct = ((change / prev_close) * 100) if change and prev_close else None

        # Analyst data
        target_mean  = info.get("targetMeanPrice")
        target_high  = info.get("targetHighPrice")
        target_low   = info.get("targetLowPrice")
        target_med   = info.get("targetMedianPrice")
        recommend    = info.get("recommendationKey", "N/A").upper()
        num_analysts = info.get("numberOfAnalystOpinions")

        # Market data
        day_low      = info.get("dayLow") or info.get("regularMarketDayLow")
        day_high     = info.get("dayHigh") or info.get("regularMarketDayHigh")
        mkt_cap      = info.get("marketCap")
        earnings_ts  = info.get("earningsTimestamp")

        # News
        news_items = t.news[:3] if t.news else []

        return {
            "price":        price,
            "change":       change,
            "change_pct":   change_pct,
            "prev_close":   prev_close,
            "day_low":      day_low,
            "day_high":     day_high,
            "mkt_cap":      mkt_cap,
            "target_mean":  target_mean,
            "target_high":  target_high,
            "target_low":   target_low,
            "target_med":   target_med,
            "recommend":    recommend,
            "num_analysts": num_analysts,
            "earnings_ts":  earnings_ts,
            "news":         news_items,
        }
    except Exception as e:
        print(f"  ⚠️  Error fetching {ticker}: {e}")
        return None


def build_stock_summary(ticker, pos, data):
    """Build the text summary for one stock."""
    lines = [f"\n{'='*60}", f"  {ticker} — {pos['name']}", f"{'='*60}"]

    if not data:
        lines.append("  ⚠️  Could not fetch data")
        return "\n".join(lines)

    price      = data["price"]
    change     = data["change"]
    change_pct = data["change_pct"]

    # Price & movement
    lines.append(f"  Price:        {format_currency(price)}  "
                 f"({format_pct(change_pct)}, {format_currency(change)} today)")
    lines.append(f"  Day Range:    {format_currency(data['day_low'])} "
                 f"– {format_currency(data['day_high'])}")
    if data["mkt_cap"]:
        lines.append(f"  Market Cap:   ${data['mkt_cap']/1e9:.2f}B")
    if data["earnings_ts"]:
        try:
            ed = datetime.fromtimestamp(data["earnings_ts"]).strftime("%B %d, %Y")
            lines.append(f"  Earnings:     {ed}")
        except Exception:
            pass

    # Position value & gain/loss
    shares = pos["shares"]
    cost   = pos.get("cost_basis")
    note   = pos.get("note")

    lines.append(f"\n  YOUR POSITION ({shares:,} shares):")
    if price:
        mkt_value = price * shares
        lines.append(f"  Market Value: {format_currency(mkt_value)}")
        if cost:
            total_cost = cost * shares
            gain       = mkt_value - total_cost
            gain_pct   = (gain / total_cost) * 100
            lines.append(f"  Cost Basis:   {format_currency(cost)}/share  "
                         f"(total invested: {format_currency(total_cost)})")
            lines.append(f"  Gain / Loss:  {format_currency(gain)}  ({format_pct(gain_pct)})")
        elif note:
            lines.append(f"  Note:         {note}")

    # Analyst ratings
    if data["recommend"] and data["recommend"] != "N/A":
        lines.append(f"\n  ANALYST VIEW:")
        analyst_line = f"  Consensus:    {data['recommend']}"
        if data["num_analysts"]:
            analyst_line += f"  ({data['num_analysts']} analysts)"
        lines.append(analyst_line)

    if any([data["target_mean"], data["target_high"], data["target_low"]]):
        lines.append(f"  Price Targets:")
        lines.append(f"    Mean:   {format_currency(data['target_mean'])}")
        lines.append(f"    Median: {format_currency(data['target_med'])}")
        lines.append(f"    High:   {format_currency(data['target_high'])}")
        lines.append(f"    Low:    {format_currency(data['target_low'])}")
        if price and data["target_mean"]:
            upside = ((data["target_mean"] - price) / price) * 100
            lines.append(f"    Upside to mean target: {format_pct(upside)}")

    # News
    if data["news"]:
        lines.append(f"\n  RECENT NEWS:")
        for item in data["news"]:
            try:
                content = item.get("content", {})
                title   = content.get("title") or item.get("title", "No title")
                pub_raw = content.get("pubDate") or item.get("providerPublishTime", "")
                if isinstance(pub_raw, int):
                    pub = datetime.fromtimestamp(pub_raw).strftime("%Y-%m-%d")
                else:
                    pub = str(pub_raw)[:10]
                lines.append(f"  [{pub}] {title[:80]}")
            except Exception:
                pass

    return "\n".join(lines)


def get_ai_analysis(portfolio_summary):
    """Send full portfolio to Claude for analysis."""
    print("\n🤖 Sending to Claude for analysis...")
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        system="""You are a thoughtful financial analyst helping a senior engineering
professional review their personal stock portfolio. Your job is to:

1. Identify the top 2-3 standout performers and explain why
2. Flag any positions showing significant weakness or risk
3. Note meaningful patterns (sector concentration, volatility, correlation)
4. For positions with analyst targets significantly above/below current price,
   call that out specifically
5. Flag upcoming earnings dates that could move prices significantly
6. Note any tax considerations (positions showing large gains)

Important guidelines:
- Present data and factors clearly — the investor makes their own buy/sell decisions
- Be specific and reference actual numbers from the data
- Note that NTAP gain/loss is tracked separately via Etrade ESPP/RSU lots
- Keep the tone professional but conversational — no jargon
- End with a brief overall portfolio health summary""",
        messages=[{
            "role": "user",
            "content": (f"Here is my current portfolio snapshot as of "
                        f"{datetime.now().strftime('%B %d, %Y')}:\n\n{portfolio_summary}")
        }]
    )
    return message.content[0].text
# Adding def for GMAIL
def send_email_report(report_text, ai_analysis):
    """Email the portfolio report to Gmail."""
    gmail_address  = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_password:
        print("  ⚠️  Gmail credentials not found in .env - skipping email")
        return

    print("\n📧 Sending report to Gmail...")

    # Build email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📈 Portfolio Report - {datetime.now().strftime('%A, %B %d, %Y')}"
    msg["From"]    = gmail_address
    msg["To"]      = gmail_address

    # Plain text version
    body = f"""PORTFOLIO REPORT
{datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}

{report_text}

{'='*60}
AI ANALYSIS
{'='*60}
{ai_analysis}
"""
    msg.attach(MIMEText(body, "plain"))

    # Send it
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, gmail_address, msg.as_string())
        print("  ✅ Report sent to Gmail")
    except Exception as e:
        print(f"  ⚠️  Email failed: {e}")
#
#

def main():
    print(f"\n🤖 Portfolio Monitor — Adam Haywood")
    print(f"   {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}")
    print(f"   Tracking {len(POSITIONS)} positions\n")

    all_summaries   = []
    portfolio_cost  = 0
    portfolio_value = 0

    for ticker, pos in POSITIONS.items():
        print(f"  Fetching {ticker}...", end="", flush=True)
        data    = get_stock_data(ticker)
        summary = build_stock_summary(ticker, pos, data)
        all_summaries.append(summary)
        print(" ✓")

        # Running totals — exclude NTAP (no single cost basis)
        if data and data.get("price") and pos.get("cost_basis"):
            portfolio_cost  += pos["cost_basis"] * pos["shares"]
            portfolio_value += data["price"]     * pos["shares"]

    # Print all summaries
    full_report = "\n".join(all_summaries)
    print(full_report)

    # Portfolio totals
    print(f"\n{'='*60}")
    print(f"  PORTFOLIO TOTALS  (excl. NTAP mixed lots)")
    print(f"{'='*60}")
    if portfolio_cost > 0:
        total_gain     = portfolio_value - portfolio_cost
        total_gain_pct = (total_gain / portfolio_cost) * 100
        print(f"  Total Invested:  {format_currency(portfolio_cost)}")
        print(f"  Current Value:   {format_currency(portfolio_value)}")
        print(f"  Total Gain/Loss: {format_currency(total_gain)} "
              f"({format_pct(total_gain_pct)})")
    print(f"  NTAP Value:      See Etrade — $266,912 est. across all lots")

    # Claude analysis
    ai_analysis = get_ai_analysis(full_report)
    print(f"\n{'='*60}")
    print(f"  AI ANALYSIS")
    print(f"{'='*60}")
    print(ai_analysis)
#
# EMAIL Send
    send_email_report(full_report, ai_analysis)
#
    # Save report
    os.makedirs("portfolio_reports", exist_ok=True)
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"portfolio_reports/report_{timestamp}.txt"
    with open(report_file, "w") as f:
        f.write(f"Portfolio Report — {datetime.now().strftime('%B %d, %Y')}\n")
        f.write(full_report)
        f.write(f"\n\nAI ANALYSIS:\n{ai_analysis}")

    print(f"\n💾 Report saved to: {report_file}")


if __name__ == "__main__":
    main()
