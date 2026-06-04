#!/usr/bin/env python3
"""
net_worth_snapshot.py
---------------------
Daily net worth snapshot combining:
  - Live taxable brokerage positions (via yfinance)
  - Fidelity IRA / 401(k) positions (via exported CSV)

Emails an HTML report similar to portfolio_monitor.py.

Usage:
  python net_worth_snapshot.py

Scheduled via cron (example — 8:30am weekdays):
  30 8 * * 1-5 /path/to/venv/bin/python /path/to/net_worth_snapshot.py

Dependencies:
  pip install yfinance python-dotenv

Environment variables (in .env):
  GMAIL_ADDRESS    - Gmail address used to send/receive
  GMAIL_PASSWORD   - Gmail App Password (not your account password)
  RECIPIENT_EMAIL  - Where to send the report (can be same as EMAIL_ADDRESS)
  FIDELITY_CSV     - Full path to your Fidelity CSV export
                     e.g. /Users/Adam/DEV_Space/ai_practice/fidelity_export.csv

Notes:
  - Download your Fidelity CSV from: Accounts > Portfolio > Positions > Download
  - Re-download it whenever you want fresh IRA/401k data (weekly or monthly works fine)
  - The script reads whatever CSV path is in FIDELITY_CSV — just re-download and
    save to the same path each time, no script changes needed.
"""

import os
import io
import smtplib
import datetime
import yfinance as yf
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# CONFIG — Your taxable brokerage positions
# Update shares whenever you buy / sell
# ─────────────────────────────────────────────
TAXABLE_POSITIONS = {
    "CDE":  {"name": "Coeur Mining",          "shares": 150, "note": ""},
    "HIMS": {"name": "Hims & Hers Health",    "shares": 100, "note": ""},
    "LAC":  {"name": "Lithium Americas",      "shares": 50,  "note": ""},
    "NTSK": {"name": "NetSTAKE",              "shares": 90,  "note": ""},
    "NVDA": {"name": "NVIDIA",                "shares": 25,  "note": ""},
    "NVO":  {"name": "Novo Nordisk",          "shares": 5,   "note": ""},
    "NVTS": {"name": "Navitas Semiconductor", "shares": 200, "note": ""},
    "QBTS": {"name": "D-Wave Quantum",        "shares": 168, "note": ""},
    "RIOT": {"name": "Riot Platforms",        "shares": 30,  "note": ""},
    "RIVN": {"name": "Rivian",                "shares": 100, "note": ""},
    "SOFI": {"name": "SoFi Technologies",     "shares": 100, "note": ""},
    "ZS":   {"name": "Zscaler",               "shares": 9,   "note": ""},
    "NTAP":  {"name": "NetApp", "shares": 1928,   "note": ""},
    # Add / remove tickers as needed
}

# ─────────────────────────────────────────────
# EMAIL CONFIG
# ─────────────────────────────────────────────
#EMAIL_ADDRESS   = os.getenv("GMAIL_ADDRESS")
#EMAIL_PASSWORD  = os.getenv("GMAIL_PASSWORD")
#RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", EMAIL_ADDRESS)
FIDELITY_CSV    = os.getenv("FIDELITY_CSV", "")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def clean_currency(value_str):
    """Convert Fidelity dollar strings like '$93,192.07' or '($0.09)' to float."""
    if pd.isna(value_str) or str(value_str).strip() in ("", "--", "N/A"):
        return 0.0
    s = str(value_str).strip()
    negative = s.startswith("(") and s.endswith(")")
    s = s.replace("(", "").replace(")", "").replace("$", "").replace(",", "").strip()
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return 0.0


def parse_fidelity_csv(csv_path):
    """
    Parse a Fidelity portfolio CSV export.
    Returns a dict: { account_name: { 'holdings': [...], 'total': float } }

    Fidelity CSVs have a disclaimer block at the bottom — this strips it.
    """
    if not csv_path or not os.path.exists(csv_path):
        return {}

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    # Strip disclaimer footer: everything after the first blank/comma-only row
    data_lines = []
    for line in content.strip().split("\n"):
        stripped = line.strip().replace(",", "")
        if stripped == "" or "provided to you solely" in line or \
           "Brokerage services" in line or "Date downloaded" in line:
            break
        data_lines.append(line)

    if not data_lines:
        return {}

    df = pd.read_csv(io.StringIO("\n".join(data_lines)))

    # Normalize column names (strip whitespace)
    df.columns = [c.strip() for c in df.columns]

    # Drop rows where Account Name is missing
    df = df.dropna(subset=["Account Name"])

    accounts = {}
    for account_name, group in df.groupby("Account Name"):
        holdings = []
        total = 0.0
        for _, row in group.iterrows():
            symbol      = str(row.get("Symbol", "")).strip()
            description = str(row.get("Description", "")).strip()
            qty         = row.get("Quantity", None)
            price       = clean_currency(row.get("Last Price", 0))
            value       = clean_currency(row.get("Current Value", 0))
            day_gain    = clean_currency(row.get("Today's Gain/Loss Dollar", 0))
            total_gain  = clean_currency(row.get("Total Gain/Loss Dollar", 0))
            cost_basis  = clean_currency(row.get("Cost Basis Total", 0))

            total += value
            holdings.append({
                "symbol":      symbol,
                "description": description,
                "quantity":    qty,
                "price":       price,
                "value":       value,
                "day_gain":    day_gain,
                "total_gain":  total_gain,
                "cost_basis":  cost_basis,
            })
        accounts[account_name] = {"holdings": holdings, "total": total}

    return accounts


def fetch_taxable_positions(positions):
    """Fetch live prices for taxable positions via yfinance."""
    tickers = list(positions.keys())
    if not tickers:
        return []

    data = yf.download(tickers, period="2d", auto_adjust=True, progress=False)

    results = []
    for ticker, meta in positions.items():
        shares = meta["shares"]
        note   = meta.get("note", "")
        try:
            closes = data["Close"][ticker].dropna()
            price_today = float(closes.iloc[-1])
            price_prev  = float(closes.iloc[-2]) if len(closes) >= 2 else price_today
            day_change  = price_today - price_prev
            value       = price_today * shares
            day_gain    = day_change * shares
        except Exception:
            price_today = price_prev = day_change = value = day_gain = 0.0

        results.append({
            "ticker":     ticker,
            "shares":     shares,
            "price":      price_today,
            "day_change": day_change,
            "value":      value,
            "day_gain":   day_gain,
            "note":       note,
        })

    results.sort(key=lambda x: x["value"], reverse=True)
    return results


# ─────────────────────────────────────────────
# HTML REPORT BUILDER
# ─────────────────────────────────────────────

def color(val):
    if val > 0:  return "#22c55e"   # green
    if val < 0:  return "#ef4444"   # red
    return "#94a3b8"                # neutral gray


def fmt_dollar(val):
    if val >= 0:
        return f"${val:,.2f}"
    return f"(${abs(val):,.2f})"


def fmt_change(val):
    sign = "▲" if val > 0 else ("▼" if val < 0 else "–")
    return f"{sign} ${abs(val):,.2f}"


def build_html(taxable_rows, fidelity_accounts, report_date):
    taxable_total   = sum(r["value"]    for r in taxable_rows)
    taxable_day_gain = sum(r["day_gain"] for r in taxable_rows)
    fidelity_total  = sum(a["total"] for a in fidelity_accounts.values())
    grand_total     = taxable_total + fidelity_total

    # ── Taxable table rows ──
    taxable_html = ""
    for r in taxable_rows:
        if r["shares"] == 0 and r["value"] == 0:
            continue  # skip zero-share placeholders
        dc_color = color(r["day_change"])
        dg_color = color(r["day_gain"])
        note_span = f'<br><span style="font-size:11px;color:#94a3b8;">{r["note"]}</span>' if r["note"] else ""
        taxable_html += f"""
        <tr>
          <td style="padding:10px 14px;font-weight:600;color:#e2e8f0;">{r['ticker']}{note_span}</td>
          <td style="padding:10px 14px;color:#94a3b8;">{r['shares']:,}</td>
          <td style="padding:10px 14px;color:#e2e8f0;">${r['price']:,.2f}</td>
          <td style="padding:10px 14px;color:{dc_color};font-weight:500;">{fmt_change(r['day_change'])}</td>
          <td style="padding:10px 14px;color:#e2e8f0;font-weight:600;">{fmt_dollar(r['value'])}</td>
          <td style="padding:10px 14px;color:{dg_color};font-weight:500;">{fmt_change(r['day_gain'])}</td>
        </tr>"""

    # ── Fidelity account sections ──
    fidelity_html = ""
    for account_name, acct in fidelity_accounts.items():
        icon = "🏦" if "401" in account_name else "📈"
        fidelity_html += f"""
        <tr>
          <td colspan="6" style="padding:18px 14px 6px;font-size:13px;font-weight:700;
              color:#94a3b8;text-transform:uppercase;letter-spacing:0.08em;border-top:1px solid #334155;">
            {icon} {account_name}
          </td>
        </tr>"""
        for h in acct["holdings"]:
            dg_color = color(h["day_gain"])
            tg_color = color(h["total_gain"])
            qty_str  = f"{h['quantity']:,.3f}" if pd.notna(h["quantity"]) else "–"
            price_str = f"${h['price']:,.2f}" if h["price"] else "–"
            fidelity_html += f"""
        <tr>
          <td style="padding:8px 14px 8px 28px;color:#e2e8f0;">
            <span style="font-weight:600;font-size:13px;">{h['symbol']}</span><br>
            <span style="font-size:11px;color:#94a3b8;">{h['description']}</span>
          </td>
          <td style="padding:8px 14px;color:#94a3b8;font-size:13px;">{qty_str}</td>
          <td style="padding:8px 14px;color:#e2e8f0;font-size:13px;">{price_str}</td>
          <td style="padding:8px 14px;color:{dg_color};font-size:13px;">{fmt_change(h['day_gain'])}</td>
          <td style="padding:8px 14px;color:#e2e8f0;font-weight:600;font-size:13px;">{fmt_dollar(h['value'])}</td>
          <td style="padding:8px 14px;color:{tg_color};font-size:13px;">{fmt_change(h['total_gain'])}</td>
        </tr>"""

        fidelity_html += f"""
        <tr style="background:#1e293b;">
          <td colspan="4" style="padding:8px 14px 12px 28px;color:#94a3b8;font-size:13px;">
            {account_name} Total
          </td>
          <td colspan="2" style="padding:8px 14px 12px;color:#f8fafc;font-weight:700;font-size:15px;">
            {fmt_dollar(acct['total'])}
          </td>
        </tr>"""

    # ── Summary cards ──
    fidelity_csv_note = ""
    if FIDELITY_CSV:
        csv_date = datetime.datetime.fromtimestamp(
            os.path.getmtime(FIDELITY_CSV)
        ).strftime("%b %d, %Y %I:%M %p")
        fidelity_csv_note = f'<p style="color:#94a3b8;font-size:12px;text-align:center;margin:6px 0 0;">Fidelity data from CSV exported {csv_date}</p>'

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:24px;background:#0f172a;font-family:'Segoe UI',Arial,sans-serif;">

  <div style="max-width:760px;margin:0 auto;">

    <!-- Header -->
    <div style="text-align:center;margin-bottom:28px;">
      <h1 style="color:#f8fafc;font-size:26px;margin:0 0 4px;">💼 Net Worth Snapshot</h1>
      <p style="color:#64748b;font-size:14px;margin:0;">{report_date} &nbsp;·&nbsp; Market data via yfinance</p>
    </div>

    <!-- Summary Cards -->
    <div style="display:flex;gap:16px;margin-bottom:28px;flex-wrap:wrap;">

      <div style="flex:1;min-width:180px;background:#1e293b;border-radius:12px;padding:20px;text-align:center;border:1px solid #334155;">
        <div style="color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">Total Net Worth</div>
        <div style="color:#f8fafc;font-size:28px;font-weight:700;">{fmt_dollar(grand_total)}</div>
      </div>

      <div style="flex:1;min-width:150px;background:#1e293b;border-radius:12px;padding:20px;text-align:center;border:1px solid #334155;">
        <div style="color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">Taxable Brokerage</div>
        <div style="color:#e2e8f0;font-size:20px;font-weight:700;">{fmt_dollar(taxable_total)}</div>
        <div style="color:{color(taxable_day_gain)};font-size:13px;margin-top:4px;">{fmt_change(taxable_day_gain)} today</div>
      </div>

      <div style="flex:1;min-width:150px;background:#1e293b;border-radius:12px;padding:20px;text-align:center;border:1px solid #334155;">
        <div style="color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">IRA + 401(k)</div>
        <div style="color:#e2e8f0;font-size:20px;font-weight:700;">{fmt_dollar(fidelity_total)}</div>
        <div style="color:#64748b;font-size:12px;margin-top:4px;">From CSV export</div>
      </div>

    </div>

    <!-- Positions Table -->
    <div style="background:#1e293b;border-radius:12px;overflow:hidden;border:1px solid #334155;">

      <!-- Table Header -->
      <div style="padding:16px 14px 10px;border-bottom:1px solid #334155;">
        <span style="color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;">
          📊 Taxable Brokerage Positions
        </span>
      </div>

      <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
        <thead>
          <tr style="background:#0f172a;">
            <th style="padding:10px 14px;text-align:left;color:#64748b;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;">Ticker</th>
            <th style="padding:10px 14px;text-align:left;color:#64748b;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;">Shares</th>
            <th style="padding:10px 14px;text-align:left;color:#64748b;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;">Price</th>
            <th style="padding:10px 14px;text-align:left;color:#64748b;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;">Day Δ</th>
            <th style="padding:10px 14px;text-align:left;color:#64748b;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;">Value</th>
            <th style="padding:10px 14px;text-align:left;color:#64748b;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.05em;">Day Gain</th>
          </tr>
        </thead>
        <tbody>
          {taxable_html}

          <!-- Taxable Total Row -->
          <tr style="background:#0f172a;border-top:2px solid #475569;">
            <td colspan="4" style="padding:12px 14px;color:#94a3b8;font-weight:600;">Taxable Total</td>
            <td style="padding:12px 14px;color:#f8fafc;font-weight:700;font-size:16px;">{fmt_dollar(taxable_total)}</td>
            <td style="padding:12px 14px;color:{color(taxable_day_gain)};font-weight:600;">{fmt_change(taxable_day_gain)}</td>
          </tr>

          <!-- Fidelity Accounts -->
          {fidelity_html}

          <!-- Grand Total -->
          <tr style="background:#020617;border-top:2px solid #6366f1;">
            <td colspan="4" style="padding:16px 14px;color:#a5b4fc;font-weight:700;font-size:15px;">
              🏆 Grand Total
            </td>
            <td colspan="2" style="padding:16px 14px;color:#a5b4fc;font-weight:800;font-size:20px;">
              {fmt_dollar(grand_total)}
            </td>
          </tr>

        </tbody>
      </table>
    </div>

    <!-- Footer -->
    <div style="text-align:center;margin-top:20px;">
      <p style="color:#475569;font-size:12px;">
        Market prices are live via yfinance. Not financial advice.
      </p>
      {fidelity_csv_note}
    </div>

  </div>
</body>
</html>
"""
    return html


# ─────────────────────────────────────────────
# EMAIL SENDER
# ─────────────────────────────────────────────

def send_email(subject, html_body):
    gmail_address  = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    if not gmail_address or not gmail_password:
        print("⚠️  Gmail credentials not found in .env - skipping email")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_address
    msg["To"]      = gmail_address
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, gmail_address, msg.as_string())
        print(f"✅ Report sent to {gmail_address}")
    except Exception as e:
        print(f"⚠️  Email failed: {e}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    report_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
    print(f"📊 Generating net worth snapshot — {report_date}")

    # 1. Live taxable positions
    print("🔄 Fetching live stock prices...")
    taxable_rows = fetch_taxable_positions(TAXABLE_POSITIONS)
    taxable_total = sum(r["value"] for r in taxable_rows)
    print(f"   Taxable brokerage: {fmt_dollar(taxable_total)}")

    # 2. Fidelity CSV (IRA + 401k)
    fidelity_accounts = {}
    if FIDELITY_CSV:
        print(f"📂 Parsing Fidelity CSV: {FIDELITY_CSV}")
        fidelity_accounts = parse_fidelity_csv(FIDELITY_CSV)
        for name, acct in fidelity_accounts.items():
            print(f"   {name}: {fmt_dollar(acct['total'])}")
    else:
        print("⚠️  FIDELITY_CSV not set in .env — skipping retirement accounts")

    fidelity_total = sum(a["total"] for a in fidelity_accounts.values())
    grand_total    = taxable_total + fidelity_total
    print(f"💰 Grand Total: {fmt_dollar(grand_total)}")

    # 3. Build + send report
    html = build_html(taxable_rows, fidelity_accounts, report_date)
    subject = f"💼 Net Worth Snapshot — {fmt_dollar(grand_total)} — {datetime.datetime.now().strftime('%b %d, %Y')}"
    send_email(subject, html)


if __name__ == "__main__":
    main()
