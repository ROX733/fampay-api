import os
import json
import time
import secrets
import imaplib
import email
import re
import math
import ssl
from datetime import datetime, timezone
from email.header import decode_header, make_header
from threading import RLock
from urllib.parse import quote
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
FAMPAY_UPI = os.getenv("FAMPAY_UPI", "papai69@fam")
KEYS_FILE = "keys.json"
ORDERS_FILE = "orders.json"
PAID_FILE = "paid.json"
ORDER_EXPIRY = 300
LOCK = RLock()
IMAP_HOST = "imap.gmail.com"

HTML_PAGE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#7054e8">
<title>FamPay API Documentation</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');
:root{--p:#7054e8;--dark:#17172b;--muted:#77798d;--line:#e9e9f2;--code:#141629}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:20px}
body{margin:0;padding:22px 14px 45px;color:var(--dark);font-family:Inter,system-ui,sans-serif;background:linear-gradient(125deg,#6b5ae7,#a16bdb,#6357d8,#8d72ed);background-size:300% 300%;animation:bg 16s ease infinite;overflow-x:hidden}
@keyframes bg{0%,100%{background-position:0 50%}50%{background-position:100% 50%}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
@keyframes enter{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
.orb{position:fixed;z-index:-1;width:200px;height:200px;border-radius:50%;filter:blur(65px);opacity:.35;pointer-events:none;animation:float 8s ease-in-out infinite}
.one{background:#ff72da;top:5%;left:-100px}
.two{background:#9dd5ff;right:-100px;top:48%;animation-delay:-4s}
main{width:100%;max-width:760px;margin:auto}
.hero{position:relative;overflow:hidden;padding:32px 20px 25px;text-align:center;background:#fffffffa;border:1px solid white;border-radius:26px;box-shadow:0 22px 65px #25145a35;animation:enter .7s ease both}
.hero:before{content:"";position:absolute;top:0;left:0;right:0;height:5px;background:linear-gradient(90deg,#7054e8,#f05abb,#7054e8)}
.logo{width:58px;height:58px;margin:auto;display:grid;place-items:center;border-radius:18px;background:#eeeaff;color:var(--p);font-size:25px;font-weight:900;animation:float 4s ease-in-out infinite}
h1{font-size:clamp(27px,6vw,39px);letter-spacing:-1.5px;margin:18px 0 10px}
.gradient{background:linear-gradient(90deg,#6248da,#d54dc1,#7654e8);background-clip:text;-webkit-background-clip:text;color:transparent}
.subtitle{max-width:520px;margin:auto;color:var(--muted);font-size:13px;line-height:1.8}
.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin-top:24px}
.stat{padding:13px 4px;border:1px solid #eeebfc;background:#f8f7ff;border-radius:13px}
.stat strong{display:block;font-size:11px;margin-top:7px}
.stat small{display:block;font-size:9px;color:var(--muted);margin-top:5px}
nav{display:flex;gap:8px;overflow-x:auto;padding:17px 1px 6px;scrollbar-width:none}
nav a{flex:0 0 auto;padding:11px 14px;border:1px solid white;border-radius:50px;color:#5540b8;background:#ffffffed;text-decoration:none;font-size:11px;font-weight:800}
.card{position:relative;overflow:hidden;margin-top:18px;padding:23px 18px;border-radius:22px;border:1px solid white;background:white;box-shadow:0 15px 38px #25145a25;transition:transform .3s}
.card:before{content:"";position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#7054e8,#e54db8,#7054e8)}
.card:hover{transform:translateY(-3px)}
.reveal{opacity:0;transform:translateY(20px);transition:opacity .65s,transform .65s}
.reveal.visible{opacity:1;transform:translateY(0)}
.card-title{display:flex;align-items:center;gap:12px;font-size:19px;font-weight:900;margin:0}
.card-icon{width:44px;height:44px;flex-shrink:0;display:grid;place-items:center;border-radius:14px;background:#f0edff;font-size:21px}
.kicker{margin:7px 0 0 56px;color:#85859a;font:10px "JetBrains Mono",monospace}
.description{margin:20px 0;color:#66697d;font-size:13px;line-height:1.85}
.endpoint{padding:13px;border:1px solid #e7e5f2;border-left:4px solid var(--p);border-radius:11px;background:#f7f6fc}
.method{display:inline-block;padding:6px 9px;border-radius:7px;color:white;background:var(--p);font:800 10px "JetBrains Mono",monospace}
.endpoint code{display:block;margin-top:10px;color:#6348ca;font:11px/1.8 "JetBrains Mono",monospace;overflow-wrap:anywhere}
.label{margin:23px 0 11px;font-size:12px;font-weight:900}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:11px}
table{width:100%;min-width:350px;border-collapse:collapse;font-size:11px;text-align:left}
th,td{padding:12px 10px;border-bottom:1px solid var(--line)}
th{color:#77798c;background:#f6f6fb;text-transform:uppercase;font-size:9px;letter-spacing:.7px}
td{color:#56596c;line-height:1.6}
tr:last-child td{border-bottom:0}
td code{color:#6548cc;font-family:"JetBrains Mono",monospace}
.codebox{overflow:hidden;border-radius:13px;color:#e8eaff;background:var(--code)}
.codehead{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:12px;border-bottom:1px solid #ffffff14;color:#c3c5dc;font:10px "JetBrains Mono",monospace}
.copy{padding:7px 9px;border:1px solid #ffffff26;border-radius:7px;background:#292d49;color:white;font-size:10px;font-weight:800;cursor:pointer}
pre{margin:0;padding:16px 13px;overflow-x:auto;color:#e9eaff;font:11px/1.85 "JetBrains Mono",monospace;white-space:pre;scrollbar-width:thin}
.note{margin-top:13px;padding:12px;border:1px solid #e8e1ff;border-radius:10px;background:#f7f4ff;color:#65539b;font-size:11px;line-height:1.75}
.badge{display:inline-block;padding:4px 7px;border-radius:6px;background:#e9e7ff;color:#6548cc;font-size:9px;font-weight:800}
footer{padding:27px 8px 0;text-align:center;color:white;font-size:11px;line-height:1.9}
.backtop{position:fixed;right:17px;bottom:18px;width:43px;height:43px;border:1px solid #ffffff80;border-radius:14px;background:#6247d9;color:white;font-size:20px;box-shadow:0 8px 25px #25145a40;opacity:0;pointer-events:none;transform:translateY(10px);transition:.25s;cursor:pointer}
.backtop.show{opacity:1;pointer-events:auto;transform:translateY(0)}
@media(min-width:600px){body{padding:35px 20px 55px}.hero{padding:40px 32px 30px}.card{padding:27px 25px}pre{padding:19px;font-size:12px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
</style>
</head>
<body>
<div class="orb one"></div><div class="orb two"></div>
<main id="top">
<header class="hero">
<div class="logo">&lt;/&gt;</div>
<h1>FamPay <span class="gradient">API Docs</span></h1>
<p class="subtitle">Payment order creation and Gmail payment-email matching. Integrate using JSON API endpoints.</p>
<div class="stats">
<div class="stat"><span>🟢</span><strong>API Service</strong><small>Documentation</small></div>
<div class="stat"><span>⚡</span><strong>REST API</strong><small>JSON responses</small></div>
<div class="stat"><span>🔐</span><strong>API Key</strong><small>Key-based access</small></div>
</div>
</header>
<nav>
<a href="#create-key">🔑 Create Key</a>
<a href="#create-order">▦ Create Order</a>
<a href="#verify">✓ Verify Payment</a>
<a href="#health">♥ Health</a>
</nav>

<section class="card reveal" id="create-key">
<h2 class="card-title"><span class="card-icon">🔑</span><span>1. Create API Key</span></h2>
<div class="kicker">POST · AUTHENTICATION</div>
<p class="description">Register Gmail and a Google App Password. Never use your normal Gmail password.</p>
<div class="endpoint"><span class="method">POST</span><code>/create_key</code></div>
<div class="label">REQUEST BODY</div>
<div class="codebox"><div class="codehead"><span>JSON</span><button class="copy" data-copy="keyreq">COPY</button></div>
<pre id="keyreq">{
  "gmail": "your-email@gmail.com",
  "gpass": "your16charapppass",
  "mobile": "9876543210"
}</pre></div>
<div class="label">SUCCESS RESPONSE</div>
<div class="codebox"><div class="codehead"><span>JSON</span><button class="copy" data-copy="keyres">COPY</button></div>
<pre id="keyres">{
  "status": "success",
  "api_key": "FAM_generated_api_key",
  "gmail": "your-email@gmail.com"
}</pre></div>
<div class="note">Keep API keys and App Passwords private. This demo stores credentials in a local JSON file; do not use as-is for a public production payment service.</div>
</section>

<section class="card reveal" id="create-order">
<h2 class="card-title"><span class="card-icon">▦</span><span>2. Create Payment Order</span></h2>
<div class="kicker">GET / POST · PAYMENT REQUEST</div>
<p class="description">Create an order and receive its ID, UPI link, QR-code URL and expiry time.</p>
<div class="endpoint"><span class="method">GET</span><code>/fam_create?amount=10&amp;api_key=YOUR_API_KEY</code></div>
<div class="label">RESPONSE EXAMPLE</div>
<div class="codebox"><div class="codehead"><span>JSON</span><button class="copy" data-copy="orderres">COPY</button></div>
<pre id="orderres">{
  "status": "success",
  "data": {
    "order_id": "FAMPAY_GENERATED_ORDER_ID",
    "amount": 10.0,
    "upi": "your-configured-upi",
    "upi_link": "upi://pay?...",
    "qr_code": "https://api.qrserver.com/...",
    "expires_in": 300
  }
}</pre></div>
<div class="note">Examples are illustrative. A UPI link or QR code does not itself confirm payment.</div>
</section>

<section class="card reveal" id="verify">
<h2 class="card-title"><span class="card-icon">✓</span><span>3. Verify Payment</span></h2>
<div class="kicker">GET / POST · EMAIL MATCH</div>
<p class="description">Searches the registered Gmail inbox for a recent email matching the order ID and transaction reference.</p>
<div class="endpoint"><span class="method">GET</span><code>/fam_verify?order_id=ORDER_ID&amp;api_key=YOUR_API_KEY</code></div>
<div class="label">SUCCESS RESPONSE</div>
<div class="codebox"><div class="codehead"><span>JSON</span><button class="copy" data-copy="verifyres">COPY</button></div>
<pre id="verifyres">{
  "status": "success",
  "data": {
    "order_id": "FAMPAY_GENERATED_ORDER_ID",
    "transaction_id": "123456789012",
    "utr": "123456789012",
    "amount": 10.0
  }
}</pre></div>
<div class="note">Gmail email matching is not authoritative proof of payment. For real transactions, verify with a trusted payment provider or bank API before crediting money or releasing goods.</div>
</section>

<section class="card reveal" id="health">
<h2 class="card-title"><span class="card-icon">♥</span><span>4. Health Check</span></h2>
<div class="kicker">GET · SERVICE STATUS</div>
<p class="description">Check whether the API server is responding.</p>
<div class="endpoint"><span class="method">GET</span><code>/health</code></div>
<div class="label">RESPONSE EXAMPLE</div>
<div class="codebox"><div class="codehead"><span>JSON</span><button class="copy" data-copy="healthres">COPY</button></div>
<pre id="healthres">{"ok":true,"imap_host":"imap.gmail.com","upi_configured":true,"total_keys":0,"total_orders":0}</pre></div>
</section>
<footer><strong>FamPay Payment API</strong><br>API Documentation · Built for integration</footer>
</main>
<button class="backtop" id="backtop" aria-label="Back to top">↑</button>
<script>
(function(){
var cards=document.querySelectorAll(".reveal");
if("IntersectionObserver" in window){
 var ob=new IntersectionObserver(function(es){
  es.forEach(function(e){
   if(e.isIntersecting){e.target.classList.add("visible");ob.unobserve(e.target);}
  });
 },{threshold:.08});
 cards.forEach(function(c){ob.observe(c);});
}else{cards.forEach(function(c){c.classList.add("visible");});}
document.querySelectorAll("[data-copy]").forEach(function(b){
 b.addEventListener("click",async function(){
  var t=document.getElementById(b.dataset.copy);
  if(!t)return;
  var old=b.textContent;
  try{
   if(navigator.clipboard&&window.isSecureContext){
    await navigator.clipboard.writeText(t.innerText);
   }else{
    var a=document.createElement("textarea");
    a.value=t.innerText;a.style.position="fixed";a.style.opacity="0";
    document.body.appendChild(a);a.select();
    var ok=document.execCommand("copy");a.remove();
    if(!ok)throw Error("copy failed");
   }
   b.textContent="COPIED ✓";b.style.background="#14835f";
  }catch(e){b.textContent="COPY FAILED";}
  setTimeout(function(){b.textContent=old;b.style.background="";},1500);
 });
});
var bt=document.getElementById("backtop");
window.addEventListener("scroll",function(){
 bt.classList.toggle("show",window.scrollY>300);
},{passive:true});
bt.addEventListener("click",function(){window.scrollTo({top:0,behavior:"smooth"});});
})();
</script>
</body>
</html>
"""


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            value = json.load(f)
        return value if isinstance(value, type(default)) else default
    except (OSError, ValueError, TypeError):
        return default


def save_json(path, value):
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
    os.replace(temp, path)


BotKeys = load_json(KEYS_FILE, {})
Orders = load_json(ORDERS_FILE, {})
PaidRecords = load_json(PAID_FILE, {})


def amount_value(value):
    try:
        amount = float(str(value).replace("₹", "").replace(",", "").strip())
        if not math.isfinite(amount) or amount <= 0 or amount > 100000:
            return None
        return round(amount, 2)
    except (TypeError, ValueError):
        return None


def decode_mime(value):
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return str(value)


def extract_email_text(msg):
    parts = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition", "").lower().startswith("attachment"):
                continue
            if part.get_content_type() not in ("text/plain", "text/html"):
                continue
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    parts.append(payload.decode(charset, errors="replace"))
            except (LookupError, UnicodeError, TypeError):
                continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                parts.append(payload.decode(charset, errors="replace"))
            else:
                raw = msg.get_payload()
                if isinstance(raw, str):
                    parts.append(raw)
        except (LookupError, UnicodeError, TypeError):
            pass
    return "\n".join(parts)


def normalize_text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def get_api_key():
    key = request.args.get("api_key") or request.headers.get("X-API-Key")
    if not key and request.is_json:
        body = request.get_json(silent=True) or {}
        key = body.get("api_key")
    return key


def json_error(message, code=400):
    return jsonify({"status": "error", "message": message}), code


def find_amount(text):
    patterns = [
        r"(?:amount|received|credited|paid|payment of|INR|Rs\.?|₹)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
        r"₹\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = amount_value(match.group(1))
            if amount is not None:
                return amount
    return None


def find_transaction_id(text):
    patterns = [
        r"\bUTR(?:\s*(?:No|Number|ID|Ref(?:erence)?))?\s*[:#\-]?\s*([A-Z0-9]{8,30})\b",
        r"\btransaction(?:\s*(?:ID|Reference|Ref|No|Number))?\s*[:#\-]?\s*([A-Z0-9]{8,30})\b",
        r"\bUPI\s*(?:Ref(?:erence)?|Txn(?:\s*ID)?)\s*[:#\-]?\s*([A-Z0-9]{8,30})\b"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def check_gmail_payment(key_record, order):
    gmail = str(key_record.get("gmail", "")).strip()
    gpass = str(key_record.get("gpass", "")).replace(" ", "").strip()
    order_id = str(order.get("order_id", ""))
    expected_amount = amount_value(order.get("amount"))

    if not gmail or not gpass:
        return None, "Gmail credentials are not configured."

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

            for message_id in reversed(data[0].split()[-100:]):
                status, fetched = mail.fetch(message_id, "(RFC822)")
                if status != "OK" or not fetched:
                    continue

                raw = next(
                    (
                        item[1] for item in fetched
                        if isinstance(item, tuple) and len(item) > 1
                    ),
                    None
                )
                if not raw:
                    continue

                try:
                    msg = email.message_from_bytes(raw)
                except Exception:
                    continue

                subject = decode_mime(msg.get("Subject", ""))
                sender = decode_mime(msg.get("From", ""))
                body = normalize_text(
                    subject + " " + extract_email_text(msg)
                )

                if order_id.lower() not in body.lower():
                    continue

                detected_amount = find_amount(body)

                if (
                    expected_amount is not None
                    and detected_amount is not None
                    and abs(detected_amount - expected_amount) > 0.009
                ):
                    continue

                txn_id = find_transaction_id(body)
                if not txn_id:
                    continue

                return {
                    "order_id": order_id,
                    "transaction_id": txn_id,
                    "utr": txn_id,
                    "amount": (
                        detected_amount
                        if detected_amount is not None
                        else expected_amount
                    ),
                    "payment_time": msg.get("Date", ""),
                    "sender_name": sender,
                    "email_subject": subject,
                    "verified_at": datetime.now(timezone.utc).isoformat()
                }, None

        return None, "No matching payment email found yet."

    except imaplib.IMAP4.error:
        return None, (
            "Gmail login failed. Check Gmail address, "
            "App Password and IMAP access."
        )
    except (OSError, TimeoutError):
        app.logger.exception("Gmail connection failed")
        return None, "Could not connect to Gmail. Try again later."
    except Exception:
        app.logger.exception("Email verification error")
        return None, "Email verification failed unexpectedly."


@app.get("/")
def index():
    return render_template_string(HTML_PAGE)


@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "imap_host": IMAP_HOST,
        "upi_configured": bool(FAMPAY_UPI),
        "total_keys": len(BotKeys),
        "total_orders": len(Orders)
    })


@app.route("/create_key", methods=["POST"])
def create_key():
    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        return json_error("Send a JSON request body.")

    gmail = str(body.get("gmail", "")).strip().lower()
    gpass = str(body.get("gpass", "")).replace(" ", "").strip()
    mobile = str(body.get("mobile", "")).strip()

    if not re.fullmatch(r"[^@\s]+@gmail\.com", gmail, re.IGNORECASE):
        return json_error("A valid Gmail address is required.")

    if len(gpass) < 12 or not gpass.isalnum():
        return json_error("Use a valid Google App Password.")

    if mobile and not re.fullmatch(r"[0-9+\-\s]{7,20}", mobile):
        return json_error("Invalid mobile number.")

    api_key = "FAM_" + secrets.token_urlsafe(32)

    with LOCK:
        BotKeys[api_key] = {
            "gmail": gmail,
            "gpass": gpass,
            "mobile": mobile,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        save_json(KEYS_FILE, BotKeys)

    return jsonify({
        "status": "success",
        "api_key": api_key,
        "gmail": gmail
    }), 201


@app.route("/register_key", methods=["POST"])
def register_key():
    return create_key()


@app.route("/fam_create", methods=["GET", "POST"])
def fam_create():
    api_key = get_api_key()

    if not api_key or api_key not in BotKeys:
        return json_error("Invalid or missing API key.", 401)

    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        raw_amount = body.get("amount")
    else:
        raw_amount = request.args.get("amount")

    amount = amount_value(raw_amount)

    if amount is None:
        return json_error(
            "Amount must be greater than 0 and no more than 100000."
        )

    order_id = "FAMPAY_" + secrets.token_hex(12).upper()
    now = int(time.time())
    expires_at = now + ORDER_EXPIRY

    upi_link = (
        "upi://pay?pa=" + quote(FAMPAY_UPI, safe="")
        + "&pn=FamPay%20Payment&am=" + format(amount, ".2f")
        + "&cu=INR&tn=" + quote(order_id, safe="")
    )

    qr_code = (
        "https://api.qrserver.com/v1/create-qr-code/"
        "?size=250x250&data=" + quote(upi_link, safe="")
    )

    order = {
        "order_id": order_id,
        "api_key": api_key,
        "amount": amount,
        "upi": FAMPAY_UPI,
        "upi_link": upi_link,
        "qr_code": qr_code,
        "created_at": now,
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
            "upi": FAMPAY_UPI,
            "upi_link": upi_link,
            "qr_code": qr_code,
            "expires_in": ORDER_EXPIRY,
            "expires_at": expires_at
        }
    }), 201


@app.route("/fam_verify", methods=["GET", "POST"])
def fam_verify():
    api_key = get_api_key()

    if not api_key or api_key not in BotKeys:
        return json_error("Invalid or missing API key.", 401)

    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        order_id = str(body.get("order_id", "")).strip()
    else:
        order_id = str(request.args.get("order_id", "")).strip()

    if not order_id:
        return json_error("order_id is required.")

    with LOCK:
        order = Orders.get(order_id)

        if not isinstance(order, dict):
            return json_error("Order not found.", 404)

        if order.get("api_key") != api_key:
            return json_error(
                "This order does not belong to this API key.", 403
            )

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

    result, error_message = check_gmail_payment(
        BotKeys[api_key], order
    )

    if not result:
        return jsonify({
            "status": "pending",
            "message": error_message,
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
