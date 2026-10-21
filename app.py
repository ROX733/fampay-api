
import os
import json
import time
import secrets
import urllib.parse
import imaplib
import email
import re
import ssl
import math
from datetime import datetime
from email.header import decode_header, make_header
from threading import RLock
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

FAMPAY_UPI = os.getenv("FAMPAY_UPI", "papai69@fam")
KEYS_FILE = "keys.json"
ORDERS_FILE = "orders.json"
PAID_FILE = "paid.json"
LOCK = RLock()

# ============================================================
# ANIMATED DOCUMENTATION UI
# Keep all HTML, CSS and JavaScript inside this string.
# ============================================================

HTML_PAGE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#7054e8">
<title>FamPay API Documentation</title>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --purple:#7054e8;
  --dark:#17172b;
  --muted:#77798d;
  --line:#e9e9f2;
  --code:#141629;
}

* { box-sizing:border-box; }

html {
  scroll-behavior:smooth;
  scroll-padding-top:20px;
}

body {
  margin:0;
  padding:20px 14px 45px;
  color:var(--dark);
  font-family:Inter,system-ui,sans-serif;
  background:linear-gradient(125deg,#6b5ae7,#a16bdb,#6357d8,#8d72ed);
  background-size:300% 300%;
  animation:gradientMove 16s ease infinite;
  overflow-x:hidden;
}

@keyframes gradientMove {
  0%,100% { background-position:0% 50%; }
  50% { background-position:100% 50%; }
}

@keyframes float {
  0%,100% { transform:translateY(0); }
  50% { transform:translateY(-12px); }
}

@keyframes enter {
  from { opacity:0; transform:translateY(22px); }
  to { opacity:1; transform:translateY(0); }
}

@keyframes shine {
  0% { background-position:180% 0; }
  100% { background-position:-180% 0; }
}

.orb {
  position:fixed;
  z-index:-1;
  width:220px;
  height:220px;
  border-radius:50%;
  filter:blur(65px);
  opacity:.35;
  pointer-events:none;
  animation:float 8s ease-in-out infinite;
}

.orb.one { background:#ff72da; top:5%; left:-100px; }
.orb.two { background:#9dd5ff; right:-100px; top:48%; animation-delay:-4s; }

main { width:100%; max-width:760px; margin:auto; }

.hero {
  position:relative;
  overflow:hidden;
  padding:32px 20px 25px;
  text-align:center;
  background:#fffffffa;
  border:1px solid #ffffff;
  border-radius:26px;
  box-shadow:0 22px 65px #25145a35;
  animation:enter .7s ease both;
}

.hero:before {
  content:"";
  position:absolute;
  top:0; left:0; right:0;
  height:5px;
  background:linear-gradient(90deg,#7054e8,#f05abb,#7054e8);
  background-size:200% 100%;
  animation:shine 5s linear infinite;
}

.logo {
  width:58px;
  height:58px;
  margin:auto;
  display:grid;
  place-items:center;
  border-radius:18px;
  background:#eeeaff;
  color:#7054e8;
  font-size:25px;
  font-weight:900;
  animation:float 4s ease-in-out infinite;
}

h1 {
  font-size:clamp(27px,6vw,39px);
  letter-spacing:-1.5px;
  margin:18px 0 10px;
}

.gradient {
  background:linear-gradient(90deg,#6248da,#d54dc1,#7654e8);
  background-clip:text;
  -webkit-background-clip:text;
  color:transparent;
}

.subtitle {
  max-width:520px;
  margin:0 auto;
  color:var(--muted);
  font-size:13px;
  line-height:1.8;
}

.stats {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:9px;
  margin-top:24px;
}

.stat {
  padding:13px 4px;
  border:1px solid #eeebfc;
  background:#f8f7ff;
  border-radius:13px;
}

.stat .emoji { font-size:18px; }
.stat strong { display:block; font-size:11px; margin-top:7px; }
.stat small { display:block; font-size:9px; color:var(--muted); margin-top:5px; }

nav {
  display:flex;
  gap:8px;
  overflow-x:auto;
  padding:17px 1px 6px;
  scrollbar-width:none;
}

nav::-webkit-scrollbar { display:none; }

nav a {
  flex:0 0 auto;
  padding:11px 14px;
  border:1px solid #ffffff;
  border-radius:50px;
  color:#5540b8;
  background:#ffffffed;
  text-decoration:none;
  font-size:11px;
  font-weight:800;
  transition:transform .25s,background .25s,color .25s;
}

nav a:hover {
  transform:translateY(-3px);
  color:#fff;
  background:#5e43d2;
}

.card {
  position:relative;
  overflow:hidden;
  margin-top:18px;
  padding:23px 18px;
  border-radius:22px;
  border:1px solid #fff;
  background:#fff;
  box-shadow:0 15px 38px #25145a25;
  transition:transform .3s,box-shadow .3s;
}

.card:before {
  content:"";
  position:absolute;
  top:0; left:0; right:0;
  height:4px;
  background:linear-gradient(90deg,#7054e8,#e54db8,#7054e8);
}

.card:hover {
  transform:translateY(-4px);
  box-shadow:0 21px 45px #25145a38;
}

.reveal {
  opacity:0;
  transform:translateY(20px);
  transition:opacity .65s ease,transform .65s ease;
}

.reveal.visible { opacity:1; transform:translateY(0); }

.card-title {
  display:flex;
  align-items:center;
  gap:12px;
  font-size:19px;
  font-weight:900;
  margin:0;
}

.card-icon {
  width:44px;
  height:44px;
  flex-shrink:0;
  display:grid;
  place-items:center;
  border-radius:14px;
  background:#f0edff;
  font-size:21px;
}

.kicker {
  margin:7px 0 0 56px;
  color:#85859a;
  font:10px "JetBrains Mono",monospace;
  letter-spacing:.4px;
}

.description {
  margin:20px 0;
  color:#66697d;
  font-size:13px;
  line-height:1.85;
}

.endpoint {
  padding:13px;
  border:1px solid #e7e5f2;
  border-left:4px solid #7054e8;
  border-radius:11px;
  background:#f7f6fc;
}

.method {
  display:inline-block;
  padding:6px 9px;
  border-radius:7px;
  color:#fff;
  background:#7054e8;
  font:800 10px "JetBrains Mono",monospace;
}

.endpoint code {
  display:block;
  margin-top:10px;
  color:#6348ca;
  font:11px/1.8 "JetBrains Mono",monospace;
  overflow-wrap:anywhere;
}

.label {
  margin:23px 0 11px;
  font-size:12px;
  font-weight:900;
}

.label span { color:#7054e8; margin-right:6px; }

.table-wrap {
  overflow-x:auto;
  border:1px solid var(--line);
  border-radius:11px;
}

table {
  width:100%;
  min-width:350px;
  border-collapse:collapse;
  font-size:11px;
  text-align:left;
}

th,td {
  padding:12px 10px;
  border-bottom:1px solid var(--line);
}

th {
  color:#77798c;
  background:#f6f6fb;
  text-transform:uppercase;
  font-size:9px;
  letter-spacing:.7px;
}

td { color:#56596c; line-height:1.6; }
tr:last-child td { border-bottom:0; }
td code { color:#6548cc; font-family:"JetBrains Mono",monospace; }

.codebox {
  overflow:hidden;
  border-radius:13px;
  color:#e8eaff;
  background:var(--code);
  box-shadow:inset 0 0 0 1px #ffffff0b;
}

.codehead {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:8px;
  padding:12px;
  border-bottom:1px solid #ffffff14;
  color:#c3c5dc;
  font:10px "JetBrains Mono",monospace;
}

.windowdots { display:flex; gap:5px; }
.windowdots i { width:7px; height:7px; border-radius:50%; background:#ff697e; }
.windowdots i:nth-child(2) { background:#ffca60; }
.windowdots i:nth-child(3) { background:#40d9a0; }

.copy {
  padding:7px 9px;
  border:1px solid #ffffff26;
  border-radius:7px;
  background:#292d49;
  color:#fff;
  font-size:10px;
  font-weight:800;
  cursor:pointer;
  transition:background .2s,transform .2s;
}

.copy:hover { background:#7054e8; transform:scale(1.04); }

pre {
  margin:0;
  padding:16px 13px;
  overflow-x:auto;
  color:#e9eaff;
  font:11px/1.85 "JetBrains Mono",monospace;
  white-space:pre;
  scrollbar-width:thin;
}

.note {
  margin-top:13px;
  padding:12px;
  border:1px solid #e8e1ff;
  border-radius:10px;
  background:#f7f4ff;
  color:#65539b;
  font-size:11px;
  line-height:1.75;
}

.badge {
  display:inline-block;
  padding:4px 7px;
  border-radius:6px;
  background:#e9e7ff;
  color:#6548cc;
  font-size:9px;
  font-weight:800;
}

footer {
  padding:27px 8px 0;
  text-align:center;
  color:#fff;
  font-size:11px;
  line-height:1.9;
}

.backtop {
  position:fixed;
  right:17px;
  bottom:18px;
  width:43px;
  height:43px;
  border:1px solid #ffffff80;
  border-radius:14px;
  background:#6247d9;
  color:#fff;
  font-size:20px;
  box-shadow:0 8px 25px #25145a40;
  opacity:0;
  pointer-events:none;
  transform:translateY(10px);
  transition:.25s;
  cursor:pointer;
}

.backtop.show {
  opacity:1;
  pointer-events:auto;
  transform:translateY(0);
}

@media(min-width:600px) {
  body { padding:35px 20px 55px; }
  .hero { padding:40px 32px 30px; }
  .card { padding:27px 25px; }
  pre { padding:19px; font-size:12px; }
}

@media(prefers-reduced-motion:reduce) {
  *,*::before,*::after {
    animation:none !important;
    transition:none !important;
    scroll-behavior:auto !important;
  }
}
</style>
</head>

<body>
<div class="orb one"></div>
<div class="orb two"></div>

<main id="top">
  <header class="hero">
    <div class="logo">&lt;/&gt;</div>
    <h1>FamPay <span class="gradient">API Docs</span></h1>
    <p class="subtitle">
      Simple payment order creation and Gmail payment-email matching.
      Integrate the API into your application using JSON responses.
    </p>

    <div class="stats">
      <div class="stat">
        <span class="emoji">🟢</span>
        <strong>API Service</strong>
        <small>Documentation</small>
      </div>
      <div class="stat">
        <span class="emoji">⚡</span>
        <strong>REST API</strong>
        <small>JSON responses</small>
      </div>
      <div class="stat">
        <span class="emoji">🔐</span>
        <strong>API Key</strong>
        <small>Key-based access</small>
      </div>
    </div>
  </header>

  <nav>
    <a href="#create-key">🔑 Create Key</a>
    <a href="#create-order">▦ Create Order</a>
    <a href="#verify">✓ Verify Payment</a>
    <a href="#health">♥ Health</a>
  </nav>

  <section class="card reveal" id="create-key">
    <h2 class="card-title">
      <span class="card-icon">🔑</span>
      <span>1. Create API Key</span>
    </h2>
    <div class="kicker">POST · AUTHENTICATION</div>
    <p class="description">
      Register your Gmail account and generate your private API key.
      Use a Google App Password, not your normal Gmail password.
    </p>

    <div class="endpoint">
      <span class="method">POST</span>
      <code>/create_key</code>
    </div>

    <div class="label"><span>⌘</span> REQUEST BODY</div>
    <div class="codebox">
      <div class="codehead">
        <span>JSON · Request</span>
        <button class="copy" data-copy="keyreq">COPY</button>
      </div>
      <pre id="keyreq">{
  "gmail": "your-email@gmail.com",
  "gpass": "your16charapppass",
  "mobile": "9876543210"
}</pre>
    </div>

    <div class="label"><span>⟨/⟩</span> SUCCESS RESPONSE</div>
    <div class="codebox">
      <div class="codehead">
        <span>JSON · 201 Created</span>
        <button class="copy" data-copy="keyres">COPY</button>
      </div>
      <pre id="keyres">{
  "status": "success",
  "api_key": "FAM_generated_api_key",
  "gmail": "your-email@gmail.com"
}</pre>
    </div>

    <div class="note">
      🔐 Keep your API key and App Password private.
      Never share these credentials publicly.
    </div>
  </section>

  <section class="card reveal" id="create-order">
    <h2 class="card-title">
      <span class="card-icon">▦</span>
      <span>2. Create Payment Order</span>
    </h2>
    <div class="kicker">GET / POST · PAYMENT REQUEST</div>
    <p class="description">
      Create a unique payment order and receive its order ID,
      UPI payment link, QR-code URL and expiry time.
    </p>

    <div class="endpoint">
      <span class="method">GET</span>
      <code>/fam_create?amount=10&amp;api_key=YOUR_API_KEY</code>
    </div>

    <div class="label"><span>☷</span> PARAMETERS</div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Parameter</th><th>Required</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td><code>api_key</code></td><td><span class="badge">Yes</span></td><td>Your generated API key.</td></tr>
          <tr><td><code>amount</code></td><td><span class="badge">Yes</span></td><td>INR amount greater than 0, up to 100000.</td></tr>
        </tbody>
      </table>
    </div>

    <div class="label"><span>⟨/⟩</span> RESPONSE EXAMPLE</div>
    <div class="codebox">
      <div class="codehead">
        <span>JSON · 201 Created</span>
        <button class="copy" data-copy="orderres">COPY</button>
      </div>
      <pre id="orderres">{
  "status": "success",
  "data": {
    "order_id": "FAMPAY_GENERATED_ORDER_ID",
    "amount": 10.0,
    "upi": "your-configured-upi",
    "upi_link": "upi://pay?...",
    "qr_code": "https://api.qrserver.com/...",
    "expires_in": 300,
    "expires_at": 1792584300
  }
}</pre>
    </div>
    <div class="note">
      ℹ️ Example values are illustrative. Your API generates a new
      order ID and expiry timestamp for each order.
    </div>
  </section>

  <section class="card reveal" id="verify">
    <h2 class="card-title">
      <span class="card-icon">✓</span>
      <span>3. Verify Payment</span>
    </h2>
    <div class="kicker">GET / POST · VERIFICATION</div>
    <p class="description">
      Check the Gmail inbox associated with your API key for a matching
      payment email containing the order ID, amount and transaction reference.
    </p>

    <div class="endpoint">
      <span class="method">GET</span>
      <code>/fam_verify?order_id=ORDER_ID&amp;api_key=YOUR_API_KEY</code>
    </div>

    <div class="label"><span>☷</span> PARAMETERS</div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Parameter</th><th>Required</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td><code>api_key</code></td><td><span class="badge">Yes</span></td><td>API key that owns the order.</td></tr>
          <tr><td><code>order_id</code></td><td><span class="badge">Yes</span></td><td>Order ID returned by the create-order endpoint.</td></tr>
        </tbody>
      </table>
    </div>

    <div class="label"><span>⟨/⟩</span> SUCCESS RESPONSE</div>
    <div class="codebox">
      <div class="codehead">
        <span>JSON · Success</span>
        <button class="copy" data-copy="verifyres">COPY</button>
      </div>
      <pre id="verifyres">{
  "status": "success",
  "data": {
    "order_id": "FAMPAY_GENERATED_ORDER_ID",
    "transaction_id": "123456789012",
    "utr": "123456789012",
    "amount": 10.0,
    "payment_time": "Payment email date",
    "sender_name": "Payment email sender"
  }
}</pre>
    </div>

    <div class="label"><span>◷</span> POSSIBLE STATUS</div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Status</th><th>Meaning</th></tr></thead>
        <tbody>
          <tr><td><span class="badge">success</span></td><td>Matching email found and order verified.</td></tr>
          <tr><td><span class="badge">pending</span></td><td>No matching email found yet.</td></tr>
          <tr><td><span class="badge">error</span></td><td>Invalid key, amount mismatch or review needed.</td></tr>
        </tbody>
      </table>
    </div>

    <div class="note">
      ⚠️ Gmail email matching is not authoritative proof of payment.
      For production use, confirm transactions through your payment provider
      or bank's trusted verification service.
    </div>
  </section>

  <section class="card reveal" id="health">
    <h2 class="card-title">
      <span class="card-icon">♥</span>
      <span>4. Health Check</span>
    </h2>
    <div class="kicker">GET · SERVICE STATUS</div>
    <p class="description">
      Check whether the API server is responding.
    </p>

    <div class="endpoint">
      <span class="method">GET</span>
      <code>/health</code>
    </div>

    <div class="label"><span>⟨/⟩</span> RESPONSE EXAMPLE</div>
    <div class="codebox">
      <div class="codehead">
        <span>JSON · 200 OK</span>
        <button class="copy" data-copy="healthres">COPY</button>
      </div>
      <pre id="healthres">{
  "ok": true,
  "imap_host": "imap.gmail.com",
  "upi_configured": true,
  "total_keys": 0,
  "total_orders": 0
}</pre>
    </div>
  </section>

  <footer>
    <strong>FamPay Payment API</strong><br>
    API Documentation · Built for integration
  </footer>
</main>

<button class="backtop" id="backtop" aria-label="Back to top">↑</button>

<script>
(function () {
  "use strict";

  // Scroll reveal animation.
  var cards = document.querySelectorAll(".reveal");

  if ("IntersectionObserver" in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });

    cards.forEach(function (card) {
      observer.observe(card);
    });
  } else {
    cards.forEach(function (card) {
      card.classList.add("visible");
    });
  }

  // Copy code examples.
  document.querySelectorAll("[data-copy]").forEach(function (button) {
    button.addEventListener("click", async function () {
      var target = document.getElementById(button.dataset.copy);
      if (!target) return;

      var original = button.textContent;

      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(target.innerText);
        } else {
          var area = document.createElement("textarea");
          area.value = target.innerText;
          area.style.position = "fixed";
          area.style.opacity = "0";
          document.body.appendChild(area);
          area.select();

          var copied = document.execCommand("copy");
          area.remove();

          if (!copied) throw new Error("Copy failed");
        }

        button.textContent = "COPIED ✓";
        button.style.background = "#14835f";
      } catch (error) {
        button.textContent = "COPY FAILED";
      }

      setTimeout(function () {
        button.textContent = original;
        button.style.background = "";
      }, 1500);
    });
  });

  // Back-to-top button.
  var topButton = document.getElementById("backtop");

  window.addEventListener("scroll", function () {
    topButton.classList.toggle("show", window.scrollY > 300);
  }, { passive: true });

  topButton.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
})();
</script>
</body>
</html>
"""


# ============================================================
# JSON STORAGE
# ============================================================

def load_json(filename, default):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return default


def save_json(filename, data):
    temp = filename + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp, filename)


BotKeys = load_json(KEYS_FILE, {})
Orders = load_json(ORDERS_FILE, {})
PaidRecords = load_json(PAID_FILE, {})

if not isinstance(BotKeys, dict):
    BotKeys = {}
if not isinstance(Orders, dict):
    Orders = {}
if not isinstance(PaidRecords, dict):
    PaidRecords = {}


# ============================================================
# PAYMENT EMAIL HELPERS
# ============================================================

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
            if part.get_content_maintype() ==
