import os
import json
import time
import secrets
import re
import math
import ssl
import imaplib
import email
from datetime import datetime, timezone
from email.header import decode_header, make_header
from threading import RLock
from urllib.parse import quote
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_FILE = os.path.join(BASE_DIR, "keys.json")
ORDERS_FILE = os.path.join(BASE_DIR, "orders.json")
PAID_FILE = os.path.join(BASE_DIR, "paid.json")

ORDER_EXPIRY = 300
IMAP_HOST = "imap.gmail.com"
LOCK = RLock()


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            value = json.load(f)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def save_json(path, value):
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
    os.replace(temp, path)


BotKeys = load_json(KEYS_FILE)
Orders = load_json(ORDERS_FILE)
PaidRecords = load_json(PAID_FILE)


HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FamPay API | Payment Documentation</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:linear-gradient(180deg,#7C6CF6 0%,#8B7CF8 35%,#A78BFA 100%);min-height:100vh;padding:16px 14px 90px;color:#111827}
a{color:inherit}
.container{max-width:680px;margin:0 auto}

/* Cards like video */
.card{background:#fff;border-radius:20px;padding:22px 18px;margin-bottom:16px;box-shadow:0 12px 32px rgba(37,20,97,0.14)}
.center{text-align:center}

/* Header */
.logo-wrap{width:58px;height:58px;background:linear-gradient(135deg,#7C6CF6,#5B4FE8);border-radius:16px;display:flex;align-items:center;justify-content:center;margin:0 auto 12px;box-shadow:0 8px 18px rgba(124,108,246,0.35)}
.badge-top{display:inline-block;background:#EDE9FF;color:#6D5DF6;font-size:10px;font-weight:800;letter-spacing:1.2px;padding:5px 12px;border-radius:20px;margin-bottom:10px}
.h1{font-size:26px;font-weight:800;line-height:1.1}
.h1 span{color:#7C6CF6}
.btn-dark{display:inline-flex;background:#111827;color:#fff;border:none;padding:11px 20px;border-radius:999px;font-weight:700;font-size:13px;margin-top:16px;cursor:pointer;align-items:center;gap:6px}
.sub{color:#6B7280;font-size:13px;line-height:1.6;margin-top:12px}
.stats{display:flex;justify-content:space-between;margin-top:20px;border-top:1px solid #F3F4F6;padding-top:16px}
.stat{flex:1;text-align:center}
.stat-icon{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 6px;font-size:14px}
.stat b{display:block;font-size:12px;color:#111827}
.stat span{font-size:11px;color:#6B7280}

/* Section */
.sec-head{display:flex;align-items:center;gap:12px;margin-bottom:8px}
.sec-num{width:36px;height:36px;background:#EDE9FF;color:#7C6CF6;border-radius:10px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px}
.sec-title{font-size:16px;font-weight:800}
.sec-type{font-size:10px;font-weight:700;letter-spacing:0.6px;color:#6B7280;margin-top:2px}
.sec-desc{font-size:13px;color:#4B5563;line-height:1.6;margin:8px 0 14px}

/* Endpoint pill - like video */
.endpoint{background:#F5F7FF;border:1px solid #DDE3FF;border-radius:12px;padding:10px 12px;display:flex;gap:10px;align-items:flex-start;overflow:auto;margin:12px 0}
.method{background:#7C6CF6;color:#fff;font-size:11px;font-weight:800;padding:4px 8px;border-radius:6px;flex-shrink:0}
.endpoint code{font-family:'JetBrains Mono',monospace;font-size:11px;color:#4338CA;word-break:break-all;line-height:1.5}

/* Table */
.req-title{font-size:11px;font-weight:800;letter-spacing:0.8px;color:#111827;margin:18px 0 10px;display:flex;align-items:center;gap:6px}
.table{border:1px solid #F3F4F6;border-radius:12px;overflow:hidden}
.t-head{display:grid;grid-template-columns:90px 90px 1fr;background:#F9FAFB;padding:9px 12px;font-size:10px;font-weight:800;color:#6B7280;letter-spacing:0.6px}
.t-row{display:grid;grid-template-columns:90px 90px 1fr;padding:12px 12px;font-size:12px;border-top:1px solid #F3F4F6;align-items:center;gap:8px}
.t-row b{font-family:'JetBrains Mono',monospace;font-size:12px}
.tag-req{background:#FEE2E2;color:#DC2626;font-size:10px;font-weight:700;padding:3px 8px;border-radius:20px;display:inline-block}
.tag-opt{background:#DBEAFE;color:#2563EB;font-size:10px;font-weight:700;padding:3px 8px;border-radius:20px;display:inline-block}

/* Code block - dark like video */
.code-wrap{position:relative;background:#0F172A;border-radius:14px;margin-top:12px;overflow:hidden;border:1px solid #1E293B}
.code-head{display:flex;justify-content:space-between;align-items:center;padding:10px 12px;background:#111C34;border-bottom:1px solid #1E293B}
.code-label{font-size:11px;font-weight:700;color:#94A3B8}
.copy{background:#7C6CF6;color:#fff;border:none;padding:6px 12px;border-radius:8px;font-size:11px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:4px}
.code-wrap pre{margin:0;padding:14px;color:#E2E8F0;font-family:'JetBrains Mono',monospace;font-size:11px;line-height:1.7;overflow:auto;white-space:pre-wrap;word-break:break-word}

/* Yellow tip */
.pro-tip{background:#FFFBEB;border:1px solid #FDE68A;border-radius:12px;padding:11px 12px;font-size:11.5px;color:#92400E;line-height:1.5;margin-top:14px;display:flex;gap:8px}
.pro-tip b{white-space:nowrap}

/* Why choose */
.features{display:grid;gap:12px;margin-top:14px}
.feat{background:#fff;border:1px solid #F3F4F6;border-radius:16px;padding:18px;text-align:center}
.feat-icon{width:46px;height:46px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 8px;font-size:20px}
.feat h4{font-size:13px;font-weight:800}
.feat p{font-size:11px;color:#6B7280;margin-top:4px;line-height:1.5}

/* Footer */
.footer{margin-top:20px;text-align:center}
.dot{display:inline-block;width:6px;height:6px;background:#7C6CF6;border-radius:50%;margin-right:6px}
.footer-links{display:flex;justify-content:center;gap:14px;margin-top:10px;font-size:11px;color:#fff;opacity:0.9}
</style>
</head>
<body>
<div class="container">

<!-- TOP HEADER - EXACT LIKE VIDEO -->
<div class="card center" style="padding:30px 18px">
  <div class="logo-wrap">⚡</div>
  <div class="badge-top">FamPay DevPortal</div>
  <div style="font-size:10px;font-weight:800;letter-spacing:1.2px;color:#6B7280;margin-top:-6px;margin-bottom:6px">AUTOMATED UPI SOLUTIONS</div>
  <h1 class="h1">FamPay <span>DevPortal</span></h1>
  <button class="btn-dark" onclick="document.getElementById('create-key').scrollIntoView({behavior:'smooth'})">● GET API KEY</button>
  <p class="sub">Merchant-wise automated payment verification with Gmail matching.</p>
</div>

<!-- API DOCUMENTATION INTRO - LIKE VIDEO -->
<div class="card center">
  <div style="width:54px;height:54px;background:#EEF2FF;border-radius:14px;display:flex;align-items:center;justify-content:center;margin:0 auto 12px;font-size:24px">📄</div>
  <h2 style="font-size:20px;font-weight:800">API <span style="color:#7C6CF6">Documentation</span></h2>
  <p class="sub">Integrate FamPay automatic payment verification into your applications with lightning-fast speed and military-grade security.</p>
  <div class="stats">
    <div class="stat"><div class="stat-icon" style="background:#ECFDF5">✔</div><b>99.9% Uptime</b></div>
    <div class="stat"><div class="stat-icon" style="background:#FEF3C7">⚡</div><b>&lt;200ms Response</b></div>
    <div class="stat"><div class="stat-icon" style="background:#DBEAFE">🔒</div><b>SSL Encrypted</b></div>
  </div>
</div>

<!-- 1. CREATE KEY -->
<div class="card" id="create-key">
  <div class="sec-head">
    <div class="sec-num">1</div>
    <div><div class="sec-title">Create Merchant API Key</div><div class="sec-type">POST API Key Generation</div></div>
  </div>
  <div class="sec-desc">Register merchant Gmail, App Password, mobile and UPI ID to get your personal API key.</div>

  <div class="endpoint"><span class="method">POST</span><code>/create_key</code></div>

  <div class="req-title">◍ REQUEST PARAMETERS</div>
  <div class="table">
    <div class="t-head"><span>PARAMETER</span><span>TYPE</span><span>DESCRIPTION</span></div>
    <div class="t-row"><b>gmail</b><span class="tag-req">Required</span><span>Merchant Gmail (must be @gmail.com)</span></div>
    <div class="t-row"><b>gpass</b><span class="tag-req">Required</span><span>16-char Google App Password</span></div>
    <div class="t-row"><b>upi</b><span class="tag-req">Required</span><span>Merchant UPI ID e.g. name@upi</span></div>
    <div class="t-row"><b>mobile</b><span class="tag-opt">Optional</span><span>Merchant mobile number</span></div>
  </div>

  <div class="code-wrap">
    <div class="code-head"><span class="code-label">REQUEST BODY</span><button class="copy" onclick="copyCode(this)">◍ COPY</button></div>
    <pre>{
  "gmail": "merchant@gmail.com",
  "gpass": "abcd efgh ijkl mnop",
  "mobile": "9876543210",
  "upi": "merchant@upi"
}</pre>
  </div>

  <div class="code-wrap">
    <div class="code-head"><span class="code-label" style="color:#86EFAC">✔ SUCCESS RESPONSE</span><button class="copy" onclick="copyCode(this)">◍ COPY</button></div>
    <pre>{
  "status": "success",
  "api_key": "FAM_xxxxxxxx",
  "upi": "merchant@upi"
}</pre>
  </div>

  <div class="pro-tip">💡 <span><b>Pro Tip:</b> Save api_key securely. It is mapped to your Gmail & UPI and used for all orders.</span></div>
</div>

<!-- 2. CREATE ORDER -->
<div class="card">
  <div class="sec-head">
    <div class="sec-num">2</div>
    <div><div class="sec-title">Generate QR Code</div><div class="sec-type">POST Payment Request</div></div>
  </div>
  <div class="sec-desc">Generate a dynamic UPI QR code for receiving instant payments with automatic verification. Uses the UPI registered with your API key.</div>

  <div class="endpoint"><span class="method">GET</span><code>/fam_create?amount=AMOUNT&api_key=YOUR_API_KEY</code></div>

  <div class="req-title">◍ REQUEST PARAMETERS</div>
  <div class="table">
    <div class="t-head"><span>PARAMETER</span><span>TYPE</span><span>DESCRIPTION</span></div>
    <div class="t-row"><b>amount</b><span class="tag-req">Required</span><span>Payment Amount (1 - 100000). Example: 100</span></div>
    <div class="t-row"><b>api_key</b><span class="tag-req">Required</span><span>Your personal API key from /create_key</span></div>
  </div>

  <div class="req-title" style="margin-top:16px">&lt;/&gt; RESPONSE FORMAT</div>
  <div class="code-wrap">
    <div class="code-head"><span class="code-label">JSON</span><button class="copy" onclick="copyCode(this)">◍ COPY</button></div>
    <pre>{
  "status": "success",
  "data": {
    "order_id": "FAMPAY_A1B2C3D4E5F6",
    "amount": 100,
    "upi": "merchant@upi",
    "upi_link": "upi://pay?pa=merchant@upi...",
    "qr_code": "https://api.qrserver.com/...",
    "expires_in": 300,
    "expires_at": 1713800000
  }
}</pre>
  </div>

  <div class="pro-tip">💡 <span><b>Pro Tip:</b> QR codes expire after 5 minutes for security. Save the order_id for payment verification.</span></div>
</div>

<!-- 3. VERIFY -->
<div class="card">
  <div class="sec-head">
    <div class="sec-num">3</div>
    <div><div class="sec-title">Verify Payment Status</div><div class="sec-type">Check Transaction Completion</div></div>
  </div>
  <div class="sec-desc">Verify if payment has been successfully received using the unique Order ID with real-time Gmail verification.</div>

  <div class="endpoint"><span class="method">GET</span><code>/fam_verify?order_id=ORDER_ID&api_key=YOUR_API_KEY</code></div>

  <div class="req-title">◍ REQUEST PARAMETERS</div>
  <div class="table">
    <div class="t-head"><span>PARAMETER</span><span>TYPE</span><span>DESCRIPTION</span></div>
    <div class="t-row"><b>order_id</b><span class="tag-req">Required</span><span>The unique order ID received from QR generation endpoint</span></div>
    <div class="t-row"><b>api_key</b><span class="tag-req">Required</span><span>Your authentication key (Get from /create_key)</span></div>
  </div>

  <div class="req-title" style="margin-top:16px">&lt;/&gt; RESPONSE EXAMPLES</div>

  <div class="code-wrap" style="border:1px solid #A7F3D0">
    <div class="code-head" style="background:#ECFDF5"><span class="code-label" style="color:#065F46">✔ PAYMENT SUCCESS</span><button class="copy" onclick="copyCode(this)">◍ COPY</button></div>
    <pre>{
  "status": "success",
  "data": {
    "order_id": "FAMPAY2028...",
    "transaction_id": "UTR12345678",
    "utr": "UTR12345678",
    "amount": 100,
    "payment_time": "Mon, 22 Apr 2024...",
    "verified_at": "2024-04-22T..."
  }
}</pre>
  </div>

  <div class="code-wrap" style="border:1px solid #FECACA;margin-top:10px">
    <div class="code-head" style="background:#FEF2F2"><span class="code-label" style="color:#991B1B">✕ PAYMENT FAILED / PENDING</span><button class="copy" onclick="copyCode(this)">◍ COPY</button></div>
    <pre>{
  "status": "pending",
  "message": "No matching payment email found yet.",
  "data": {
    "order_id": "FAMPAY2028...",
    "amount": 100
  }
}</pre>
  </div>

  <div class="pro-tip" style="background:#EFF6FF;border-color:#BFDBFE;color:#1E40AF">ℹ️ <span><b>Important:</b> Keep your api_key confidential. Never expose it in client-side code or public repositories. Gmail verification is not authoritative bank proof.</span></div>
</div>

<!-- WHY CHOOSE -->
<div class="card">
  <h3 style="font-size:16px;font-weight:800;text-align:center;margin-bottom:14px">⭐ Why Choose FamPay API?</h3>
  <div class="features">
    <div class="feat"><div class="feat-icon" style="background:#EDE9FF">🚀</div><h4>Lightning Fast</h4><p>Instant payment verification with &lt;200ms response time</p></div>
    <div class="feat"><div class="feat-icon" style="background:#D1FAE5">🛡️</div><h4>Bank-Grade Security</h4><p>End-to-end encryption with SSL/TLS protocols + Gmail OAuth secure</p></div>
    <div class="feat"><div class="feat-icon" style="background:#EDE9FF"> &lt;/&gt; </div><h4>Developer Friendly</h4><p>Simple REST API with comprehensive documentation</p></div>
  </div>
</div>

<div class="footer">
  <div style="background:#fff;border-radius:20px;padding:16px">
    <div style="font-size:10px;font-weight:800;letter-spacing:1.2px;color:#6B7280"><span class="dot"></span>OFFICIAL API INFRASTRUCTURE</div>
    <div class="footer-links" style="color:#111827;margin-top:10px;font-weight:600">
      <span>🔷 API v2.0</span><span>● 24/7 Active</span><span>🌐 Global Access</span>
    </div>
  </div>
</div>

</div>

<script>
function copyCode(btn){
  const pre = btn.closest('.code-wrap').querySelector('pre');
  navigator.clipboard.writeText(pre.innerText);
  const old = btn.innerHTML;
  btn.innerHTML = '✓ COPIED';
  btn.style.background = '#10B981';
  setTimeout(()=>{btn.innerHTML = old; btn.style.background='#7C6CF6'},1500);
}
</script>
</body>
</html>
"""


def error(message, status=400):
    return jsonify({"status": "error", "message": message}), status


def amount_value(value):
    try:
        amount = float(
            str(value).replace("₹", "").replace(",", "").strip()
        )
        if not math.isfinite(amount) or amount <= 0 or amount > 100000:
            return None
        return round(amount, 2)
    except (TypeError, ValueError):
        return None


def get_api_key():
    key = request.args.get("api_key") or request.headers.get("X-API-Key")

    if not key and request.is_json:
        body = request.get_json(silent=True) or {}
        key = body.get("api_key")

    return key


def decode_mime(value):
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return str(value or "")


def extract_text(msg):
    parts = []

    message_parts = msg.walk() if msg.is_multipart() else [msg]

    for part in message_parts:
        if part.get_content_maintype() == "multipart":
            continue

        if part.get_content_type() not in ("text/plain", "text/html"):
            continue

        if part.get("Content-Disposition", "").lower().startswith("attachment"):
            continue

        try:
            payload = part.get_payload(decode=True)

            if payload:
                parts.append(
                    payload.decode(
                        part.get_content_charset() or "utf-8",
                        errors="replace"
                    )
                )
            elif isinstance(part.get_payload(), str):
                parts.append(part.get_payload())

        except Exception:
            pass

    text = " ".join(parts)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def find_transaction_id(text):
    patterns = [
        r"\bUTR(?:\s*(?:No|Number|ID|Ref(?:erence)?))?\s*[:#\-]?\s*([A-Z0-9]{8,30})\b",
        r"\btransaction(?:\s*(?:ID|Reference|Ref|No|Number))?\s*[:#\-]?\s*([A-Z0-9]{8,30})\b",
        r"\bUPI\s*(?:Ref(?:erence)?|Txn(?:\s*ID)?)\s*[:#\-]?\s*([A-Z0-9]{8,30})\b"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)

    return None


def find_amount(text):
    patterns = [
        r"(?:amount|received|credited|paid|payment of|INR|Rs\.?|₹)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
        r"₹\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.I)

        if match:
            value = amount_value(match.group(1))
            if value is not None:
                return value

    return None


def check_gmail_payment(record, order):
    gmail = str(record.get("gmail", "")).strip()
    gpass = str(record.get("gpass", "")).replace(" ", "").strip()

    try:
        context = ssl.create_default_context()

        with imaplib.IMAP4_SSL(
            IMAP_HOST, 993, ssl_context=context
        ) as mail:

            mail.login(gmail, gpass)

            status, _ = mail.select("INBOX", readonly=True)

            if status != "OK":
                return None, "Could not open Gmail inbox."

            status, data = mail.search(None, "ALL")

            if status != "OK" or not data or not data[0]:
                return None, "No inbox messages found."

            # Inspect the latest 100 messages.
            for message_id in reversed(data[0].split()[-100:]):
                status, fetched = mail.fetch(message_id, "(RFC822)")

                if status != "OK":
                    continue

                raw = next(
                    (
                        item[1]
                        for item in fetched
                        if isinstance(item, tuple) and len(item) > 1
                    ),
                    None
                )

                if not raw:
                    continue

                msg = email.message_from_bytes(raw)

                subject = decode_mime(msg.get("Subject", ""))
                body = subject + " " + extract_text(msg)

                # Email must contain this specific order ID.
                if order["order_id"].lower() not in body.lower():
                    continue

                detected_amount = find_amount(body)
                expected_amount = amount_value(order.get("amount"))

                if (
                    detected_amount is not None
                    and expected_amount is not None
                    and abs(detected_amount - expected_amount) > 0.009
                ):
                    continue

                transaction_id = find_transaction_id(body)

                if not transaction_id:
                    continue

                return {
                    "order_id": order["order_id"],
                    "transaction_id": transaction_id,
                    "utr": transaction_id,
                    "amount": (
                        detected_amount
                        if detected_amount is not None
                        else expected_amount
                    ),
                    "payment_time": msg.get("Date", ""),
                    "email_subject": subject,
                    "verified_at": datetime.now(timezone.utc).isoformat()
                }, None

        return None, "No matching payment email found yet."

    except imaplib.IMAP4.error:
        return None, (
            "Gmail login failed. Check Gmail address, Google App Password "
            "and IMAP access."
        )

    except (OSError, TimeoutError):
        app.logger.exception("Gmail connection failed")
        return None, "Could not connect to Gmail. Try again later."

    except Exception:
        app.logger.exception("Email verification failed")
        return None, "Email verification failed unexpectedly."


@app.get("/")
def index():
    return render_template_string(HTML)


@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "imap_host": IMAP_HOST,
        "total_keys": len(BotKeys),
        "total_orders": len(Orders)
    })


# =====================================================
# CREATE MERCHANT API KEY
# =====================================================
@app.route("/create_key", methods=["POST"])
def create_key():
    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        return error("Send a JSON request body.")

    gmail = str(body.get("gmail", "")).strip().lower()
    gpass = str(body.get("gpass", "")).replace(" ", "").strip()
    mobile = str(body.get("mobile", "")).strip()
    upi = str(body.get("upi", "")).strip()

    if not re.fullmatch(r"[^@\s]+@gmail\.com", gmail, re.I):
        return error("A valid Gmail address is required.")

    if len(gpass) != 16 or not gpass.isalnum():
        return error(
            "Use the 16-character Google App Password, without spaces."
        )

    if mobile and not re.fullmatch(r"[0-9+\-\s]{7,20}", mobile):
        return error("Invalid mobile number.")

    if not re.fullmatch(
        r"[A-Za-z0-9.\-_]{2,256}@[A-Za-z0-9]{2,64}", upi
    ):
        return error("Enter a valid UPI ID, for example name@upi.")

    api_key = "FAM_" + secrets.token_urlsafe(32)

    with LOCK:
        BotKeys[api_key] = {
            "gmail": gmail,
            "gpass": gpass,
            "mobile": mobile,
            "upi": upi,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        save_json(KEYS_FILE, BotKeys)

    return jsonify({
        "status": "success",
        "api_key": api_key,
        "gmail": gmail,
        "upi": upi
    }), 201


@app.route("/register_key", methods=["POST"])
def register_key():
    return create_key()


# =====================================================
# CREATE PAYMENT ORDER USING THAT MERCHANT'S UPI
# =====================================================
@app.route("/fam_create", methods=["GET", "POST"])
def fam_create():
    api_key = get_api_key()

    if not api_key or api_key not in BotKeys:
        return error("Invalid or missing API key.", 401)

    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        raw_amount = body.get("amount")
    else:
        raw_amount = request.args.get("amount")

    amount = amount_value(raw_amount)

    if amount is None:
        return error(
            "Amount must be greater than 0 and no more than 100000."
        )

    merchant_upi = str(BotKeys[api_key].get("upi", "")).strip()

    if not merchant_upi:
        return error(
            "No UPI ID registered for this API key. "
            "Register the key again with upi."
        )

    order_id = "FAMPAY_" + secrets.token_hex(12).upper()
    expires_at = int(time.time()) + ORDER_EXPIRY

    upi_link = (
        "upi://pay?pa=" + quote(merchant_upi, safe="")
        + "&pn=Merchant"
        + "&am=" + format(amount, ".2f")
        + "&cu=INR"
        + "&tn=" + quote(order_id, safe="")
    )

    qr_code = (
        "https://api.qrserver.com/v1/create-qr-code/"
        "?size=250x250&data=" + quote(upi_link, safe="")
    )

    order = {
        "order_id": order_id,
        "api_key": api_key,
        "amount": amount,
        "upi": merchant_upi,
        "upi_link": upi_link,
        "qr_code": qr_code,
        "created_at": int(time.time()),
        "expires_at": expires_at,
        "status": "pending"
    }

    with LOCK:
        Orders[order_id] = order
        save_json(ORDERS_FILE, Orders)

    return jsonify({
        "status": "success",
        "data": {
            "order_id": order_id,
            "amount": amount,
            "upi": merchant_upi,
            "upi_link": upi_link,
            "qr_code": qr_code,
            "expires_in": ORDER_EXPIRY,
            "expires_at": expires_at
        }
    }), 201


# =====================================================
# VERIFY PAYMENT EMAIL FOR THE SAME MERCHANT
# =====================================================
@app.route("/fam_verify", methods=["GET", "POST"])
def fam_verify():
    api_key = get_api_key()

    if not api_key or api_key not in BotKeys:
        return error("Invalid or missing API key.", 401)

    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        order_id = str(body.get("order_id", "")).strip()
    else:
        order_id = str(request.args.get("order_id", "")).strip()

    if not order_id:
        return error("order_id is required.")

    with LOCK:
        order = Orders.get(order_id)

        if not isinstance(order, dict):
            return error("Order not found.", 404)

        if order.get("api_key") != api_key:
            return error("This order does not belong to this API key.", 403)

        paid = PaidRecords.get(order_id)

    if paid:
        return jsonify({"status": "success", "data": paid})

    if int(time.time()) > int(order.get("expires_at", 0)):
        return jsonify({
            "status": "pending",
            "message": "Order has expired.",
            "data": {
                "order_id": order_id,
                "amount": order.get("amount")
            }
        })

    result, message = check_gmail_payment(BotKeys[api_key], order)

    if not result:
        return jsonify({
            "status": "pending",
            "message": message,
            "data": {
                "order_id": order_id,
                "amount": order.get("amount")
            }
        })

    with LOCK:
        PaidRecords[order_id] = result
        order["status"] = "email_match"
        Orders[order_id] = order

        save_json(PAID_FILE, PaidRecords)
        save_json(ORDERS_FILE, Orders)

    return jsonify({"status": "success", "data": result})


@app.errorhandler(404)
def not_found(_error):
    return jsonify({
        "status": "error",
        "message": "Endpoint not found."
    }), 404


@app.errorhandler(405)
def method_not_allowed(_error):
    return jsonify({
        "status": "error",
        "message": "Method not allowed."
    }), 405


@app.errorhandler(500)
def internal_error(_error):
    app.logger.exception("Internal server error")
    return jsonify({
        "status": "error",
        "message": "Internal server error."
    }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000"))
    )
