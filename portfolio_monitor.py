import os
import anthropic
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ─────────────────────────────────────────────
# YOUR PORTFOLIO — pulled from Etrade 05/28/26
# NTAP: sellable shares from NTAP_EtradeStatus
# Others: from Etrade_Positions.csv
# Note: 200 unvested NTAP RSU shares (RS100768,
#       vest Aug 2026) are excluded — forfeited.
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
    "CDE": {
        "name": "Coeur Mining",
        "shares": 150,
        "cost_basis": 14.996133
    },
    "HIMS": {
        "name": "Hims & Hers Health",
        "shares": 100,
        "cost_basis": 25.45
    },
    "LAC": {
        "name": "Lithium Americas",
        "shares": 50,
        "cost_basis": 7.1558
    },
    "NTSK": {
        "name": "NetSTAKE",
        "shares": 90,
        "cost_basis": 21.33
    },
    "NVDA": {
        "name": "NVIDIA",
        "shares": 25,
        "cost_basis": 120.45
    },
    "NVO": {
        "name": "Novo Nordisk",
        "shares": 5,
        "cost_basis": 147.254
    },
    "NVTS": {
        "name": "Navitas Semiconductor",
        "shares": 200,
        "cost_basis": 15.145
    },
    "QBTS": {
        "name": "D-Wave Quantum",
        "shares": 168,
        "cost_basis": 9.517976
    },
    "RIOT": {
        "name": "Riot Platforms",
        "shares": 30,
        "cost_basis": 10.22
    },
    "RIVN": {
        "name": "Rivian",
        "shares": 100,
        "cost_basis": 12.64
    },
    "SOFI": {
        "name": "SoFi Technologies",
        "shares": 100,
        "cost_basis": 9.30
    },
    "ZS": {
        "name": "Zscaler",
        "shares": 9,
        "cost_basis": 133.41
    },
}

FMP_API_KEY = os.getenv("FMP_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def fetch_fmp(endpoint: str) -> dict | list | None:
    """Fetch data from FMP API."""
    import urllib.request
    import json
    url = f"https://financialmodelingprep.com/api/v3/{endpoint}&apikey={FMP_API_KEY}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  ⚠️  FMP error for {endpoint}: {e}")
        return None


def get_quote(ticker: str) -> dict | None:
    data = fetch_fmp(f"quote/{ticker}?")
    return data[0] if data else None


def get_analyst_rating(ticker: str) -> dict | None:
    data = fetch_fmp(f"analyst-stock-recommendations/{ticker}?limit=1&")
    return data[0] if data else None


def get_price_target(ticker: str) -> dict | None:
    data = fetch_fmp(f"price-target-consensus/{ticker}?")
    return data[0] if data else None


def get_news(ticker: str) -> list:
    data = fetch_fmp(f"stock_news?tickers={ticker}&limit=3&")
    return data if data else []


def format_currency(val: float) -> str:
    if val is None:
        return "N/A"
    return f"${val:,.2f}"


def format_pct(val: float) -> str:
    if val is None:
        return "N/A"
    arrow = "▲" if val >= 0 else "▼"
    return f"{arrow} {abs(val):.2f}%"


def build_stock_summary(ticker: str, pos: dict) -> str:
    """Fetch all data for one ticker and build a summary string."""
    quote = get_quote(ticker)
    rating = get_analyst_rating(ticker)
    target = get_price_target(ticker)
    news = get_news(ticker)

    lines = [f"\n{'='*60}", f"  {ticker} — {pos['name']}", f"{'='*60}"]

    if quote:
        price = quote.get("price")
        change = quote.get("change")
        change_pct = quote.get("changesPercentage")
        day_low = quote.get("dayLow")
        day_high = quote.get("dayHigh")
        mkt_cap = quote.get("marketCap")

        lines.append(f"  Price:        {format_currency(price)}  "
                     f"({format_pct(change_pct)}, {format_currency(change)} today)")
        lines.append(f"  Day Range:    {format_currency(day_low)} – {format_currency(day_high)}")
        if mkt_cap:
            lines.append(f"  Market Cap:   ${mkt_cap/1e9:.2f}B")

        # Position value & gain/loss
        shares = pos["shares"]
        cost = pos.get("cost_basis")
        note = pos.get("note")

        if price:
            mkt_value = price * shares
            lines.append(f"\n  YOUR POSITION ({shares:,} shares):")
            lines.append(f"  Market Value: {format_currency(mkt_value)}")

            if cost:
                total_cost = cost * shares
                gain = mkt_value - total_cost
                gain_pct = (gain / total_cost) * 100
                lines.append(f"  Cost Basis:   {format_currency(cost)}/share  "
                             f"(total: {format_currency(total_cost)})")
                lines.append(f"  Gain / Loss:  {format_currency(gain)}  ({format_pct(gain_pct)})")
            elif note:
                lines.append(f"  Note:         {note}")
    else:
        lines.append("  ⚠️  Could not fetch quote data")

    # Analyst ratings
    if rating:
        lines.append(f"\n  ANALYST CONSENSUS:")
        lines.append(f"  Strong Buy: {rating.get('strongBuy', 0)}  "
                     f"Buy: {rating.get('buy', 0)}  "
                     f"Hold: {rating.get('hold', 0)}  "
                     f"Sell: {rating.get('sell', 0)}  "
                     f"Strong Sell: {rating.get('strongSell', 0)}")

    if target:
        lines.append(f"\n  PRICE TARGETS:")
        lines.append(f"  Consensus:  {format_currency(target.get('targetConsensus'))}")
        lines.append(f"  High:       {format_currency(target.get('targetHigh'))}")
        lines.append(f"  Low:        {format_currency(target.get('targetLow'))}")
        lines.append(f"  Median:     {format_currency(target.get('targetMedian'))}")

    # News
    if news:
        lines.append(f"\n  RECENT NEWS:")
        for item in news[:3]:
            pub = item.get("publishedDate", "")[:10]
            title = item.get("title", "")[:80]
            lines.append(f"  [{pub}] {title}")

    return "\n".join(lines)


def get_ai_analysis(portfolio_summary: str) -> str:
    """Send full portfolio to Claude for analysis."""
    print("\n🤖 Getting AI analysis of your full portfolio...")
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        system="""You are a thoughtful financial analyst helping a senior engineering 
professional review their personal stock portfolio. Your job is to:
1. Identify the top 2-3 standout performers and explain why
2. Flag any positions showing significant weakness or risk
3. Note any meaningful patterns (sector concentration, volatility exposure, etc.)
4. For each position, list 2-3 key factors the investor should watch
5. Surface any upcoming earnings dates that could move prices significantly

Important guidelines:
- Present data and factors clearly — the investor makes their own buy/sell decisions
- Be specific and reference actual numbers from the data
- Flag tax considerations where relevant (short-term vs long-term gains)
- Keep the tone professional but plain — no jargon
- Note that NTAP gain/loss is tracked separately via Etrade ESPP/RSU lots""",
        messages=[{
            "role": "user",
            "content": f"Here is my current portfolio snapshot as of {datetime.now().strftime('%B %d, %Y')}:\n\n{portfolio_summary}"
        }]
    )
    return message.content[0].text


def main():
    print(f"\n🤖 Portfolio Monitor — Adam Haywood")
    print(f"   {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}")
    print(f"   Tracking {len(POSITIONS)} positions\n")

    if not FMP_API_KEY:
        print("❌ FMP_API_KEY not found in .env — please add it and try again.")
        return

    # Fetch data for all positions
    all_summaries = []
    portfolio_cost = 0
    portfolio_value = 0

    for ticker, pos in POSITIONS.items():
        print(f"  Fetching {ticker}...", end="", flush=True)
        summary = build_stock_summary(ticker, pos)
        all_summaries.append(summary)
        print(" ✓")

        # Running portfolio totals (exclude NTAP from cost calc — mixed lots)
        quote = get_quote(ticker)
        if quote and quote.get("price") and pos.get("cost_basis"):
            portfolio_cost += pos["cost_basis"] * pos["shares"]
            portfolio_value += quote["price"] * pos["shares"]

    # Print individual stock summaries
    full_report = "\n".join(all_summaries)
    print(full_report)

    # Portfolio totals
    print(f"\n{'='*60}")
    print(f"  PORTFOLIO TOTALS (excl. NTAP mixed lots)")
    print(f"{'='*60}")
    if portfolio_cost > 0:
        total_gain = portfolio_value - portfolio_cost
        total_gain_pct = (total_gain / portfolio_cost) * 100
        print(f"  Total Invested:  {format_currency(portfolio_cost)}")
        print(f"  Current Value:   {format_currency(portfolio_value)}")
        print(f"  Total Gain/Loss: {format_currency(total_gain)} ({format_pct(total_gain_pct)})")
    print(f"  NTAP Value:      See Etrade — $266,912 est. across all lots")

    # AI analysis
    ai_analysis = get_ai_analysis(full_report)
    print(f"\n{'='*60}")
    print(f"  AI ANALYSIS")
    print(f"{'='*60}")
    print(ai_analysis)

    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"portfolio_reports/report_{timestamp}.txt"
    os.makedirs("portfolio_reports", exist_ok=True)
    with open(report_file, "w") as f:
        f.write(f"Portfolio Report — {datetime.now().strftime('%B %d, %Y')}\n")
        f.write(full_report)
        f.write(f"\n\nAI ANALYSIS:\n{ai_analysis}")
    print(f"\n💾 Report saved to: {report_file}")


if __name__ == "__main__":
    main()
