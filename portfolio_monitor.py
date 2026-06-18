import os
import anthropic # type: ignore
import yfinance as yf # type: ignore
from dotenv import load_dotenv # type: ignore
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
        "shares": 1928,
        "cost_basis": None,
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
    "SOFI": {"name": "SoFi Technologies",     "shares": 150, "cost_basis": 9.30},
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


def color_for_value(val):
    """Return green or red hex color based on positive/negative."""
    if val is None:
        return "#666666"
    return "#16a34a" if val >= 0 else "#dc2626"


def get_stock_data(ticker):
    """Fetch all data for one ticker using yfinance."""
    try:
        t    = yf.Ticker(ticker)
        info = t.info

        price = (
            info.get("currentPrice") or
            info.get("regularMarketPrice") or
            info.get("previousClose")
        )
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        change     = (price - prev_close) if price and prev_close else None
        change_pct = ((change / prev_close) * 100) if change and prev_close else None

        return {
            "price":        price,
            "change":       change,
            "change_pct":   change_pct,
            "prev_close":   prev_close,
            "day_low":      info.get("dayLow") or info.get("regularMarketDayLow"),
            "day_high":     info.get("dayHigh") or info.get("regularMarketDayHigh"),
            "mkt_cap":      info.get("marketCap"),
            "target_mean":  info.get("targetMeanPrice"),
            "target_high":  info.get("targetHighPrice"),
            "target_low":   info.get("targetLowPrice"),
            "target_med":   info.get("targetMedianPrice"),
            "recommend":    info.get("recommendationKey", "N/A").upper(),
            "num_analysts": info.get("numberOfAnalystOpinions"),
            "earnings_ts":  info.get("earningsTimestamp"),
            "news":         t.news[:3] if t.news else [],
        }
    except Exception as e:
        print(f"  ⚠️  Error fetching {ticker}: {e}")
        return None


def build_plain_summary(ticker, pos, data):
    """Plain text version for saving to file."""
    lines = [f"\n{'='*60}", f"  {ticker} — {pos['name']}", f"{'='*60}"]
    if not data:
        lines.append("  ⚠️  Could not fetch data")
        return "\n".join(lines)

    price      = data["price"]
    change_pct = data["change_pct"]
    change     = data["change"]

    lines.append(f"  Price:        {format_currency(price)}  ({format_pct(change_pct)}, {format_currency(change)} today)")
    lines.append(f"  Day Range:    {format_currency(data['day_low'])} – {format_currency(data['day_high'])}")
    if data["mkt_cap"]:
        lines.append(f"  Market Cap:   ${data['mkt_cap']/1e9:.2f}B")
    if data["earnings_ts"]:
        try:
            ed = datetime.fromtimestamp(data["earnings_ts"]).strftime("%B %d, %Y")
            lines.append(f"  Earnings:     {ed}")
        except Exception:
            pass

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
            lines.append(f"  Cost Basis:   {format_currency(cost)}/share (total: {format_currency(total_cost)})")
            lines.append(f"  Gain / Loss:  {format_currency(gain)}  ({format_pct(gain_pct)})")
        elif note:
            lines.append(f"  Note:         {note}")

    if data["recommend"] and data["recommend"] != "N/A":
        lines.append(f"\n  ANALYST VIEW:  {data['recommend']}  ({data['num_analysts']} analysts)")
    if data["target_mean"]:
        lines.append(f"  Price Targets: Mean {format_currency(data['target_mean'])}  "
                     f"High {format_currency(data['target_high'])}  "
                     f"Low {format_currency(data['target_low'])}")
        if price and data["target_mean"]:
            upside = ((data["target_mean"] - price) / price) * 100
            lines.append(f"  Upside to mean: {format_pct(upside)}")

    if data["news"]:
        lines.append(f"\n  RECENT NEWS:")
        for item in data["news"]:
            try:
                content = item.get("content", {})
                title   = content.get("title") or item.get("title", "No title")
                pub_raw = content.get("pubDate") or item.get("providerPublishTime", "")
                pub     = datetime.fromtimestamp(pub_raw).strftime("%Y-%m-%d") if isinstance(pub_raw, int) else str(pub_raw)[:10]
                lines.append(f"  [{pub}] {title[:80]}")
            except Exception:
                pass

    return "\n".join(lines)


def build_html_card(ticker, pos, data):
    """Build an HTML card for one stock."""
    if not data:
        return f"""
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;
                    padding:20px;margin-bottom:16px;">
            <h3 style="margin:0;color:#111">{ticker} — {pos['name']}</h3>
            <p style="color:#dc2626">⚠️ Could not fetch data</p>
        </div>"""

    price      = data["price"]
    change     = data["change"]
    change_pct = data["change_pct"]
    shares     = pos["shares"]
    cost       = pos.get("cost_basis")
    note       = pos.get("note")

    price_color  = color_for_value(change)
    change_arrow = "▲" if (change or 0) >= 0 else "▼"

    # Position block
    position_html = ""
    if price:
        mkt_value = price * shares
        if cost:
            total_cost = cost * shares
            gain       = mkt_value - total_cost
            gain_pct   = (gain / total_cost) * 100
            gain_color = color_for_value(gain)
            position_html = f"""
            <div style="background:#f9fafb;border-radius:8px;padding:12px;margin:12px 0;">
                <div style="font-size:12px;font-weight:600;color:#6b7280;
                            text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;">
                    Your Position — {shares:,} shares
                </div>
                <div style="display:flex;gap:24px;flex-wrap:wrap;">
                    <div>
                        <div style="font-size:11px;color:#9ca3af">Market Value</div>
                        <div style="font-weight:600;color:#111">{format_currency(mkt_value)}</div>
                    </div>
                    <div>
                        <div style="font-size:11px;color:#9ca3af">Cost Basis</div>
                        <div style="font-weight:600;color:#111">{format_currency(cost)}/sh
                            <span style="font-weight:400;color:#6b7280;font-size:12px;">
                                (total {format_currency(total_cost)})</span></div>
                    </div>
                    <div>
                        <div style="font-size:11px;color:#9ca3af">Gain / Loss</div>
                        <div style="font-weight:600;color:{gain_color}">
                            {format_currency(gain)} ({change_arrow} {abs(gain_pct):.2f}%)</div>
                    </div>
                </div>
            </div>"""
        elif note:
            position_html = f"""
            <div style="background:#f9fafb;border-radius:8px;padding:12px;margin:12px 0;">
                <div style="font-size:12px;font-weight:600;color:#6b7280;
                            text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;">
                    Your Position — {shares:,} shares
                </div>
                <div style="font-size:13px;color:#6b7280">{note}</div>
                <div style="font-weight:600;color:#111;margin-top:4px;">
                    Market Value: {format_currency(mkt_value)}</div>
            </div>"""

    # Analyst block
    analyst_html = ""
    if data["recommend"] and data["recommend"] != "N/A":
        rec_colors = {
            "STRONG_BUY": "#16a34a", "BUY": "#16a34a",
            "HOLD": "#d97706", "UNDERPERFORM": "#dc2626",
            "SELL": "#dc2626", "STRONG_SELL": "#dc2626"
        }
        rec_color = rec_colors.get(data["recommend"], "#6b7280")
        upside_html = ""
        if price and data["target_mean"]:
            upside     = ((data["target_mean"] - price) / price) * 100
            up_color   = color_for_value(upside)
            upside_html = f"""<div>
                        <div style="font-size:11px;color:#9ca3af">Upside to Mean</div>
                        <div style="font-weight:600;color:{up_color}">{format_pct(upside)}</div>
                    </div>"""

        analyst_html = f"""
            <div style="margin:12px 0;">
                <div style="font-size:12px;font-weight:600;color:#6b7280;
                            text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;">
                    Analyst View
                    <span style="font-weight:400;color:#9ca3af;font-size:11px;">
                        — {data['num_analysts'] or 'N/A'} analysts</span>
                </div>
                <div style="display:flex;gap:24px;flex-wrap:wrap;align-items:flex-start;">
                    <div>
                        <div style="font-size:11px;color:#9ca3af">Consensus</div>
                        <div style="font-weight:700;color:{rec_color}">{data['recommend']}</div>
                    </div>
                    <div>
                        <div style="font-size:11px;color:#9ca3af">Mean Target</div>
                        <div style="font-weight:600;color:#111">{format_currency(data['target_mean'])}</div>
                    </div>
                    <div>
                        <div style="font-size:11px;color:#9ca3af">High / Low</div>
                        <div style="font-weight:600;color:#111">
                            {format_currency(data['target_high'])} / {format_currency(data['target_low'])}</div>
                    </div>
                    {upside_html}
                </div>
            </div>"""

    # Earnings
    earnings_html = ""
    if data["earnings_ts"]:
        try:
            ed = datetime.fromtimestamp(data["earnings_ts"]).strftime("%B %d, %Y")
            earnings_html = f"""<span style="background:#fef3c7;color:#92400e;font-size:11px;
                font-weight:600;padding:2px 8px;border-radius:10px;margin-left:8px;">
                📅 Earnings {ed}</span>"""
        except Exception:
            pass

    # News
    news_html = ""
    if data["news"]:
        news_items = ""
        for item in data["news"]:
            try:
                content = item.get("content", {})
                title   = content.get("title") or item.get("title", "No title")
                pub_raw = content.get("pubDate") or item.get("providerPublishTime", "")
                pub     = datetime.fromtimestamp(pub_raw).strftime("%b %d") if isinstance(pub_raw, int) else str(pub_raw)[:10]
                link    = content.get("canonicalUrl", {}).get("url") or item.get("link", "#")
                news_items += f"""<div style="padding:6px 0;border-top:1px solid #f3f4f6;font-size:13px;">
                    <span style="color:#9ca3af;font-size:11px;">[{pub}]</span>
                    <a href="{link}" style="color:#1d4ed8;text-decoration:none;margin-left:4px;">
                        {title[:90]}</a></div>"""
            except Exception:
                pass
        if news_items:
            news_html = f"""
            <div style="margin-top:12px;">
                <div style="font-size:12px;font-weight:600;color:#6b7280;
                            text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;">
                    Recent News</div>
                {news_items}
            </div>"""

    # Market cap
    mktcap_html = ""
    if data["mkt_cap"]:
        mktcap_html = f"""<span style="font-size:12px;color:#9ca3af;margin-left:8px;">
            Mkt Cap ${data['mkt_cap']/1e9:.2f}B</span>"""

    return f"""
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;
                padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.06);">
        <div style="display:flex;justify-content:space-between;
                    align-items:flex-start;flex-wrap:wrap;gap:8px;">
            <div>
                <span style="font-size:18px;font-weight:700;color:#111">{ticker}</span>
                <span style="font-size:14px;color:#6b7280;margin-left:6px;">{pos['name']}</span>
                {earnings_html}
            </div>
            <div style="text-align:right;">
                <div style="font-size:22px;font-weight:700;color:#111">
                    {format_currency(price)}</div>
                <div style="font-size:13px;font-weight:600;color:{price_color}">
                    {change_arrow} {format_currency(abs(change) if change else None)}
                    ({abs(change_pct):.2f}% today)</div>
                {mktcap_html}
            </div>
        </div>
        <div style="font-size:12px;color:#9ca3af;margin-top:4px;">
            Day Range: {format_currency(data['day_low'])} – {format_currency(data['day_high'])}
        </div>
        {position_html}
        {analyst_html}
        {news_html}
    </div>"""


def build_html_email(all_cards, portfolio_cost, portfolio_value, ai_analysis):
    """Assemble the full HTML email."""
    date_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

    # Portfolio totals block
    if portfolio_cost > 0:
        total_gain     = portfolio_value - portfolio_cost
        total_gain_pct = (total_gain / portfolio_cost) * 100
        gain_color     = color_for_value(total_gain)
        totals_html = f"""
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;
                    padding:20px;margin-bottom:24px;">
            <div style="font-size:13px;font-weight:600;color:#166534;
                        text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px;">
                Portfolio Totals — excl. NTAP mixed lots
            </div>
            <div style="display:flex;gap:56px;flex-wrap:wrap;">
                <div>
	            <div style="min-width:100px;padding:8px 24px 8px 0;margin-right:24px;border-right:1px solid #bbf7d0;">
                    <div style="font-size:11px;color:#16a34a;margin-bottom:6px">Total Invested</div>
                    <div style="font-size:20px;font-weight:700;color:#111">
                        {format_currency(portfolio_cost)}</div>
                </div>
                <div>
	            <div style="min-width:100px;padding:8px 24px 8px 0;margin-right:24px;border-right:1px solid #bbf7d0;">
                    <div style="font-size:11px;color:#16a34a;margin-bottom:6px">Current Value</div>
                    <div style="font-size:20px;font-weight:700;color:#111;gap:10px">
                        {format_currency(portfolio_value)}</div>
                </div>
                <div>
	            <div style="min-width:100px;padding:8px 24px 8px 0;margin-right:24px;border-right:1px solid #bbf7d0;">
                    <div style="font-size:11px;color:#16a34a;margin-bottom:6px">Total Gain / Loss</div>
                    <div style="font-size:20px;font-weight:700;color:{gain_color}">
                        {format_currency(total_gain)}
                        <span style="font-size:14px;">({format_pct(total_gain_pct)})</span>
                    </div>
                </div>
            </div>
            <div style="font-size:12px;color:#6b7280;margin-top:10px;">
                NTAP: See Etrade — $266,912 est. market value across all ESPP/RSU lots
            </div>
        </div>"""
    else:
        totals_html = ""

    # AI analysis block — convert newlines to HTML
    ai_html = ai_analysis.replace("\n", "<br>")

    cards_html = "\n".join(all_cards)

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,
             'Segoe UI',Roboto,sans-serif;">
    <div style="max-width:680px;margin:0 auto;padding:24px 16px;">

        <!-- Header -->
        <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);
                    border-radius:12px;padding:24px;margin-bottom:24px;color:#fff;">
            <div style="font-size:22px;font-weight:700;">📈 Portfolio Report</div>
            <div style="font-size:14px;opacity:.8;margin-top:4px;">{date_str}</div>
            <div style="font-size:13px;opacity:.7;margin-top:2px;">Adam Haywood · 13 positions</div>
        </div>

        <!-- Portfolio Totals -->
        {totals_html}

        <!-- AI Analysis -->
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;
                    padding:20px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,.06);">
            <div style="font-size:13px;font-weight:600;color:#6b7280;
                        text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px;">
                🤖 AI Analysis
            </div>
            <div style="font-size:14px;color:#374151;line-height:1.7;">{ai_html}</div>
        </div>

        <!-- Individual Stock Cards -->
        <div style="font-size:13px;font-weight:600;color:#6b7280;
                    text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px;">
            Individual Positions
        </div>
        {cards_html}

        <!-- Footer -->
        <div style="text-align:center;font-size:12px;color:#9ca3af;margin-top:24px;padding:16px;">
            Generated by Portfolio Monitor · Data via Yahoo Finance<br>
            Not financial advice — for informational purposes only
        </div>
    </div>
</body>
</html>"""


def send_email_report(html_content, plain_text):
    """Email the portfolio report to Gmail."""
    gmail_address  = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_password:
        print("  ⚠️  Gmail credentials not found in .env — skipping email")
        return

    print("\n📧 Sending HTML report to Gmail...")
    msg            = MIMEMultipart("alternative")
    msg["Subject"] = f"📈 Portfolio Report — {datetime.now().strftime('%A, %B %d, %Y')}"
    msg["From"]    = gmail_address
    msg["To"]      = gmail_address

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, gmail_address, msg.as_string())
        print("  ✅ HTML report sent to Gmail")
    except Exception as e:
        print(f"  ⚠️  Email failed: {e}")


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


def main():
    print(f"\n🤖 Portfolio Monitor — Adam Haywood")
    print(f"   {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}")
    print(f"   Tracking {len(POSITIONS)} positions\n")

    all_cards      = []
    all_plain      = []
    portfolio_cost  = 0
    portfolio_value = 0

    for ticker, pos in POSITIONS.items():
        print(f"  Fetching {ticker}...", end="", flush=True)
        data = get_stock_data(ticker)

        # Build both formats
        all_cards.append(build_html_card(ticker, pos, data))
        all_plain.append(build_plain_summary(ticker, pos, data))
        print(" ✓")

        # Running totals — exclude NTAP
        if data and data.get("price") and pos.get("cost_basis"):
            portfolio_cost  += pos["cost_basis"] * pos["shares"]
            portfolio_value += data["price"]     * pos["shares"]

    # Plain text report for terminal + file
    full_plain = "\n".join(all_plain)
    print(full_plain)

    # Portfolio totals (terminal)
    print(f"\n{'='*60}")
    print(f"  PORTFOLIO TOTALS  (excl. NTAP mixed lots)")
    print(f"{'='*60}")
    if portfolio_cost > 0:
        total_gain     = portfolio_value - portfolio_cost
        total_gain_pct = (total_gain / portfolio_cost) * 100
        print(f"  Total Invested:  {format_currency(portfolio_cost)}")
        print(f"  Current Value:   {format_currency(portfolio_value)}")
        print(f"  Total Gain/Loss: {format_currency(total_gain)} ({format_pct(total_gain_pct)})")
    print(f"  NTAP Value:      See Etrade — $266,912 est. across all lots")

    # Claude analysis
    ai_analysis = get_ai_analysis(full_plain)
    print(f"\n{'='*60}")
    print(f"  AI ANALYSIS")
    print(f"{'='*60}")
    print(ai_analysis)

    # Build HTML email
    html_email = build_html_email(all_cards, portfolio_cost, portfolio_value, ai_analysis)

    # Send email
    send_email_report(html_email, full_plain)

    # Save report
    os.makedirs("portfolio_reports", exist_ok=True)
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"portfolio_reports/report_{timestamp}.txt"
    with open(report_file, "w") as f:
        f.write(f"Portfolio Report — {datetime.now().strftime('%B %d, %Y')}\n")
        f.write(full_plain)
        f.write(f"\n\nAI ANALYSIS:\n{ai_analysis}")
    print(f"\n💾 Report saved to: {report_file}")


if __name__ == "__main__":
    main()
