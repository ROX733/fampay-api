
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

FAMPAY_UPI = os.getenv("FAMPAY_UPI")
KEYS_FILE = "keys.json"
ORDERS_FILE = "orders.json"
PAID_FILE = "paid.json"
LOCK = RLock()

HTML_PAGE = """

HTML_PAGE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#7054e8">
<title>FamPay API | Payment Documentation</title>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --purple: #7054e8;
  --purple-dark: #5237c8;
  --pink: #e84cbd;
  --ink: #17192b;
  --muted: #73768a;
  --line: #e8eaf2;
  --panel: #ffffff;
  --code: #14172a;
}

* { box-sizing: border-box; }

html {
  scroll-behavior: smooth;
  scroll-padding-top: 24px;
}

body {
  margin: 0;
  color: var(--ink);
  font-family: Inter, system-ui, sans-serif;
  background: linear-gradient(135deg,#7565ed,#8c60d9,#6554cf,#8271ed);
  background-size: 300% 300%;
  animation: gradientFlow 16s ease infinite;
  overflow-x: hidden;
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: -1;
  opacity: .22;
  background-image:
    radial-gradient(circle at 25% 25%,#fff 1px,transparent 2px),
    radial-gradient(circle at 75% 65%,#fff 1px,transparent 2px);
  background-size: 31px 31px,47px 47px;
  animation: patternDrift 25s linear infinite;
}

.glow {
  position: fixed;
  width: 240px;
  height: 240px;
  border-radius: 50%;
  filter: blur(65px);
  opacity: .28;
  pointer-events: none;
  z-index: -1;
  animation: floatGlow 12s ease-in-out infinite alternate;
}

.glow.one { background: #ff70d4; top: 12%; left: -110px; }
.glow.two { background: #91a9ff; right: -110px; top: 52%; animation-delay: -5s; }

@keyframes gradientFlow {
  0%,100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}
@keyframes patternDrift {
  from { background-position: 0 0,0 0; }
  to { background-position: 90px 120px,-70px 80px; }
}
@keyframes floatGlow {
  from { transform: translate3d(0,0,0) scale(.9); }
  to { transform: translate3d(45px,-35px,0) scale(1.2); }
}
@keyframes riseIn {
  from { opacity: 0; transform: translateY(25px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes shine {
  0% { background-position: 180% 0; }
  100% { background-position: -180% 0; }
}
@keyframes pulse {
  0%,100% { box-shadow: 0 0 0 0 #7255e833; }
  50% { box-shadow: 0 0 0 8px #7255e800; }
}
@keyframes iconFloat {
  0%,100% { transform: translateY(0) rotate(0); }
  50% { transform: translateY(-5px) rotate(-3deg); }
}

.page {
  width: min(760px,100%);
  margin: auto;
  padding: 24px 15px 65px;
}

.hero {
  position: relative;
  overflow: hidden;
  background: rgba(255,255,255,.97);
  border: 1px solid #ffffff;
  border-radius: 27px;
  padding: 32px 23px 27px;
  text-align: center;
  box-shadow: 0 22px 65px #32207135;
  animation: riseIn .8s cubic-bezier(.2,.7,.2,1) both;
}

.hero::after {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 5px;
  background: linear-gradient(90deg,#6d52e8,#e34db8,#6d52e8);
  background-size: 200% 100%;
  animation: shine 5s linear infinite;
}

.hero-icon {
  display: inline-grid;
  place-items: center;
  width: 58px;
  height: 58px;
  border-radius: 19px;
  color: var(--purple);
  background: #f0edff;
  font-size: 28px;
  font-weight: 900;
  animation: iconFloat 3.5s ease-in-out infinite;
}

h1 {
  margin: 18px 0 12px;
  font-size: clamp(27px,6vw,39px);
  letter-spacing: -1.8px;
  line-height: 1.16;
}

.gradient-text {
  color: #7252df;
  background: linear-gradient(100deg,#6147db,#a344d3,#e348ac,#6147db);
  background-size: 250% auto;
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: shine 7s linear infinite;
}

.subtitle {
  max-width: 520px;
  margin: 0 auto;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.8;
}

.stats {
  display: grid;
  grid-template-columns: repeat(3,minmax(0,1fr));
  gap: 9px;
  margin-top: 25px;
}

.stat {
  border-radius: 13px;
  padding: 12px 5px;
  background: #f7f6ff;
  border: 1px solid #efedfc;
}

.stat-icon { font-size: 17px; }
.stat strong { display: block; margin-top: 5px; font-size: 12px; }
.stat small { display: block; margin-top: 4px; font-size: 10px; color: var(--muted); }

.nav {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 17px 2px 5px;
  margin: 5px 0 10px;
  scrollbar-width: none;
  animation: riseIn .9s .1s both;
}
.nav::-webkit-scrollbar { display:none; }

.nav a {
  flex: 0 0 auto;
  text-decoration: none;
  background: #ffffffed;
  border: 1px solid #ffffff;
  border-radius: 100px;
  padding: 10px 14px;
  font-size: 11px;
  font-weight: 800;
  color: #5540bb;
  transition: .25s ease;
}
.nav a:hover {
  color: white;
  background: var(--purple);
  transform: translateY(-3px);
  box-shadow: 0 7px 18px #30208035;
}

.doc-card {
  position: relative;
  background: var(--panel);
  border: 1px solid #ffffff;
  border-radius: 23px;
  padding: 23px 19px;
  margin-top: 18px;
  box-shadow: 0 14px 38px #34217626;
  overflow: hidden;
  transition: transform .3s ease, box-shadow .3s ease;
}

.doc-card::before {
  content: "";
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
  background: linear-gradient(90deg,#7354e9,#df49b9,#7354e9);
  background-size: 200% 100%;
}

.doc-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 42px #34217635;
}

.reveal {
  opacity: 0;
  transform: translateY(22px);
  transition: opacity .65s ease,transform .65s cubic-bezier(.2,.7,.2,1);
}
.reveal.visible { opacity: 1; transform: translateY(0); }

.card-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  font-size: clamp(16px,4vw,20px);
  font-weight: 900;
  letter-spacing: -.5px;
}

.card-icon {
  flex: 0 0 43px;
  height: 43px;
  display: grid;
  place-items: center;
  border-radius: 13px;
  background: #f0edff;
  color: var(--purple);
  font-size: 20px;
}

.kicker {
  margin-top: 5px;
  font-family: "JetBrains Mono",monospace;
  color: #85849b;
  font-size: 10px;
  letter-spacing: .5px;
}

.description {
  margin: 19px 0;
  font-size: 13px;
  color: #65687b;
  line-height: 1.8;
}

.endpoint {
  border: 1px solid #e2e4ef;
  border-left: 4px solid var(--purple);
  border-radius: 12px;
  padding: 13px;
  background: linear-gradient(135deg,#f8f8fc,#f2f3fa);
  overflow-wrap: anywhere;
}

.method {
  display: inline-block;
  padding: 6px 10px;
  color: white;
  background: linear-gradient(135deg,#8058f0,#5d3ed1);
  border-radius: 7px;
  box-shadow: 0 3px 9px #7054e844;
  font: 800 10px "JetBrains Mono",monospace;
}

.endpoint code {
  display: block;
  margin-top: 10px;
  color: #6046c8;
  font: 500 11px/1.8 "JetBrains Mono",monospace;
  overflow-wrap: anywhere;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 22px 0 12px;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: .35px;
}

.section-label span { color: #7152dc; font-size: 16px; }

.table-wrap {
  overflow-x: auto;
  border: 1px solid #ececf4;
  border-radius: 12px;
}

table {
  border-collapse: collapse;
  width: 100%;
  min-width: 390px;
  font-size: 11px;
  text-align: left;
}

th {
  background: #f5f6fb;
  color: #797c90;
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

th,td { padding: 13px 11px; border-bottom: 1px solid #ececf4; }
tr:last-child td { border-bottom: 0; }
td { color: #55596d; line-height: 1.65; }
td code { color: #6248c8; font-family: "JetBrains Mono",monospace; }

.tag {
  display: inline-block;
  padding: 4px 7px;
  border-radius: 6px;
  font-size: 9px;
  font-weight: 800;
  white-space: nowrap;
}
.required { color: #c52d50; background: #ffe6ec; }
.optional { color: #315fca; background: #e7edff; }

.code-box {
  position: relative;
  overflow: hidden;
  border-radius: 14px;
  background: var(--code);
  color: #e8eaff;
  box-shadow: inset 0 0 0 1px #ffffff0b;
}

.code-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid #ffffff12;
  color: #b7bbd2;
  font: 10px "JetBrains Mono",monospace;
}

.dots { display: flex; gap: 5px; }
.dots i { width: 7px; height: 7px; border-radius: 50%; background: #ff6b80; }
.dots i:nth-child(2) { background: #ffd166; }
.dots i:nth-child(3) { background: #4bdfa0; }

.copy {
  border: 1px solid #ffffff25;
  border-radius: 7px;
  padding: 7px 9px;
  background: #292d49;
  color: #fff;
  font: 700 10px Inter,sans-serif;
  cursor: pointer;
  transition: .2s ease;
}
.copy:hover { background: #7655e9; transform: scale(1.04); }
.copy:active { transform: scale(.96); }

pre {
  margin: 0;
  padding: 17px 15px;
  overflow-x: auto;
  white-space: pre;
  font: 11px/1.85 "JetBrains Mono",monospace;
  color: #e4e7ff;
  scrollbar-width: thin;
}

.json-key { color: #bba3ff; }
.json-string { color: #ffe080; }
.json-number { color: #71e6bd; }

.note {
  margin-top: 12px;
  padding: 12px 13px;
  border: 1px solid #e6e0ff;
  border-radius: 10px;
  background: #f7f4ff;
  color: #66549c;
  font-size: 11px;
  line-height: 1.7;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 6px;
  border-radius: 50%;
  background: #20c982;
  animation: pulse 2s infinite;
}

.footer {
  color: #ffffffde;
  text-align: center;
  padding: 26px 10px 0;
  font-size: 11px;
  line-height: 1.9;
}
.footer strong { color: #fff; }

.back-top {
  position: fixed;
  right: 17px;
  bottom: 18px;
  width: 43px;
  height: 43px;
  border: 1px solid #ffffff70;
  border-radius: 14px;
  color: white;
  background: #6247d9;
  box-shadow: 0 8px 25px #2b17654a;
  cursor: pointer;
  opacity: 0;
  pointer-events: none;
  transform: translateY(10px);
  transition: .25s ease;
  font-size: 18px;
}
.back-top.show { opacity: 1; pointer-events: auto; transform: translateY(0); }

@media (min-width:600px) {
  .page { padding: 38px 20px 70px; }
  .hero { padding: 42px 36px 32px; }
  .doc-card { padding: 27px 26px; }
  .description { font-size: 14px; }
  pre { font-size: 12px; padding: 20px; }
}

@media (prefers-reduced-motion: reduce) {
  *,*::before,*::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: .01ms !important;
  }
}
</style>
</head>

<body>
<div class="glow one"></div>
<div class="glow two"></div>

<main class="page" id="top">
  <header class="hero">
    <div class="hero-icon">&lt;/&gt;</div>
    <h1>API <span class="gradient-text">Documentation</span></h1>
    <p class="subtitle">
      Integrate FamPay payment verification into your applications
      with fast API requests and automatic Gmail payment-email matching.
    </p>

    <div class="stats">
      <div class="stat">
        <span class="stat-icon">🟢</span>
        <strong>API Service</strong>
        <small><span class="status-dot"></span>Available</small>
      </div>
      <div class="stat">
        <span class="stat-icon">⚡</span>
        <strong>REST API</strong>
        <small>JSON responses</small>
      </div>
      <div class="stat">
        <span class="stat-icon">🔐</span>
        <strong>API Key</strong>
        <small>Key-based access</small>
      </div>
    </div>
  </header>

  <nav class="nav" aria-label="Documentation navigation">
    <a href="#create-key">🔑 API Key</a>
    <a href="#create-order">▦ Create Order</a>
    <a href="#verify">✓ Verify Payment</a>
    <a href="#health">♥ Health</a>
  </nav>

  <section class="doc-card reveal" id="create-key">
    <h2 class="card-title">
      <span class="card-icon">🔑</span>
      <span>1. Generate API Key</span>
    </h2>
    <div class="kicker">POST · AUTHENTICATION</div>
    <p class="description">
      Register your Gmail account to generate an API key.
      Use a Google App Password, not your normal Gmail password.
    </p>

    <div class="endpoint">
      <span class="method">POST</span>
      <code>/create_key</code>
    </div>

    <div class="section-label"><span>☷</span> REQUEST HEADERS</div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Header</th><th>Value</th></tr></thead>
        <tbody>
          <tr><td><code>Content-Type</code></td><td>application/json</td></tr>
        </tbody>
      </table>
    </div>

    <div class="section-label"><span>⌘</span> REQUEST BODY</div>
    <div class="code-box">
      <div class="code-head">
        <span>JSON · Request</span>
        <button class="copy" data-copy="key-request">▣ COPY</button>
      </div>
      <pre id="key-request">{
  "gmail": "your-email@gmail.com",
  "gpass": "your16charapppass",
  "mobile": "9876543210"
}</pre>
    </div>

    <div class="section-label"><span>⟨/⟩</span> SUCCESS RESPONSE</div>
    <div class="code-box">
      <div class="code-head">
        <span>JSON · 201 Created</span>
        <button class="copy" data-copy="key-response">▣ COPY</button>
      </div>
      <pre id="key-response">{
  "status": "success",
  "api_key": "FAM_your_generated_api_key",
  "gmail": "your-email@gmail.com"
}</pre>
    </div>

    <div class="note">⚠️ Keep your API key and Gmail App Password private. The example above uses placeholder values.</div>
  </section>

  <section class="doc-card reveal" id="create-order">
    <h2 class="card-title">
      <span class="card-icon">▦</span>
      <span>2. Create Payment Order</span>
    </h2>
    <div class="kicker">GET / POST · PAYMENT REQUEST</div>
    <p class="description">
      Generate a unique UPI payment order. The response includes the order
      ID, UPI link, QR-code URL and expiry information.
    </p>

    <div class="endpoint">
      <span class="method">GET</span>
      <code>/fam_create?amount=10&amp;api_key=YOUR_API_KEY</code>
    </div>

    <div class="section-label"><span>☷</span> REQUEST PARAMETERS</div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
        <tbody>
          <tr>
            <td><code>api_key</code></td>
            <td><span class="tag required">Required</span></td>
            <td>Your generated API key.</td>
          </tr>
          <tr>
            <td><code>amount</code></td>
            <td><span class="tag required">Required</span></td>
            <td>Amount in INR, greater than 0 and at most 100000.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="section-label"><span>⟨/⟩</span> SUCCESS RESPONSE</div>
    <div class="code-box">
      <div class="code-head">
        <span>JSON · 201 Created</span>
        <button class="copy" data-copy="order-response">▣ COPY</button>
      </div>
      <pre id="order-response">{
  "status": "success",
  "data": {
    "order_id": "FAMPAY20261021120000AB12CD34",
    "amount": 10.0,
    "upi": "papai69@fam",
    "upi_link": "upi://pay?...",
    "qr_code": "https://api.qrserver.com/...",
    "expires_in": 300,
    "expires_at": 1792584300
  }
}</pre>
    </div>

    <div class="note">ℹ️ Example values are illustrative. Your server returns a newly generated order ID, QR URL and expiry timestamp for each request.</div>
  </section>

  <section class="doc-card reveal" id="verify">
    <h2 class="card-title">
      <span class="card-icon">✓</span>
      <span>3. Verify Payment</span>
    </h2>
    <div class="kicker">GET / POST · PAYMENT VERIFICATION</div>
    <p class="description">
      Check the Gmail inbox linked to your API key for a matching payment
      email containing the order ID, amount and transaction reference.
    </p>

    <div class="endpoint">
      <span class="method">GET</span>
      <code>/fam_verify?order_id=ORDER_ID&amp;api_key=YOUR_API_KEY</code>
    </div>

    <div class="section-label"><span>☷</span> REQUEST PARAMETERS</div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Parameter</th><th>Type</th><th>Description</th></tr></thead>
        <tbody>
          <tr>
            <td><code>api_key</code></td>
            <td><span class="tag required">Required</span></td>
            <td>The API key that owns the order.</td>
          </tr>
          <tr>
            <td><code>order_id</code></td>
            <td><span class="tag required">Required</span></td>
            <td>The order ID returned by the create-order endpoint.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="section-label"><span>⟨/⟩</span> VERIFIED RESPONSE</div>
    <div class="code-box">
      <div class="code-head">
        <span>JSON · Success</span>
        <button class="copy" data-copy="verify-response">▣ COPY</button>
      </div>
      <pre id="verify-response">{
  "status": "success",
  "data": {
    "order_id": "FAMPAY20261021120000AB12CD34",
    "transaction_id": "123456789012",
    "utr": "123456789012",
    "amount": 10.0,
    "payment_time": "Payment email date",
    "sender_name": "Payment email sender"
  }
}</pre>
    </div>

    <div class="section-label"><span>◷</span> POSSIBLE STATUSES</div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Status</th><th>Meaning</th></tr></thead>
        <tbody>
          <tr><td><span class="tag optional">success</span></td><td>Payment email matched and order verified.</td></tr>
          <tr><td><span class="tag optional">pending</span></td><td>No matching payment email was found yet.</td></tr>
          <tr><td><span class="tag required">error</span></td><td>Invalid key, mismatch, review or another error.</td></tr>
        </tbody>
      </table>
    </div>

    <div class="note">⚠️ Email matching alone is not authoritative payment confirmation. For production payments, verify transactions with your payment provider or bank.</div>
  </section>

  <section class="doc-card reveal" id="health">
    <h2 class="card-title">
      <span class="card-icon">♥</span>
      <span>4. API Health Check</span>
    </h2>
    <div class="kicker">GET · SERVICE STATUS</div>
    <p class="description">
      Check whether the API service is responding and view its basic counters.
    </p>

    <div class="endpoint">
      <span class="method">GET</span>
      <code>/health</code>
    </div>

    <div class="section-label"><span>⟨/⟩</span> RESPONSE FORMAT</div>
    <div class="code-box">
      <div class="code-head">
        <span>JSON · 200 OK</span>
        <button class="copy" data-copy="health-response">▣ COPY</button>
      </div>
      <pre id="health-response">{
  "ok": true,
  "imap_host": "imap.gmail.com",
  "upi_configured": true,
  "total_keys": 0,
  "total_orders": 0
}</pre>
    </div>
  </section>

  <footer class="footer">
    <strong>FamPay API</strong> · Payment Documentation<br>
    Built for API integration · <a href="#top" style="color:white">Back to top ↑</a>
  </footer>
</main>

<button class="back-top" id="backTop" aria-label="Back to top">↑</button>

<script>
(function () {
  "use strict";

  // Smooth reveal as documentation sections enter the screen.
  const sections = document.querySelectorAll(".reveal");

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });

    sections.forEach(function (section) {
      observer.observe(section);
    });
  } else {
    sections.forEach(function (section) {
      section.classList.add("visible");
    });
  }

  // Copy the exact contents of a code sample.
  document.querySelectorAll("[data-copy]").forEach(function (button) {
    button.addEventListener("click", async function () {
      const target = document.getElementById(button.dataset.copy);
      if (!target) return;

      const original = button.textContent;
      const text = target.innerText;

      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
        } else {
          const area = document.createElement("textarea");
          area.value = text;
          area.style.position = "fixed";
          area.style.opacity = "0";
          document.body.appendChild(area);
          area.select();
          const copied = document.execCommand("copy");
          area.remove();
          if (!copied) throw new Error("Copy unavailable");
        }

        button.textContent = "✓ COPIED";
        button.style.background = "#138b68";
      } catch (error) {
        button.textContent = "SELECT & COPY";
      }

      setTimeout(function () {
        button.textContent = original;
        button.style.background = "";
      }, 1600);
    });
  });

  // Animated back-to-top button.
  const backTop = document.getElementById("backTop");

  window.addEventListener("scroll", function () {
    backTop.classList.toggle("show", window.scrollY > 350);
  }, { passive: true });

  backTop.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  // Smooth navigation with a reduced-motion accessibility fallback.
  document.querySelectorAll('.nav a[href^="#"]').forEach(function (link) {
    link.addEventListener("click", function (event) {
      const target = document.querySelector(link.getAttribute("href"));
      if (!target) return;
      event.preventDefault();
      target.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "auto" : "smooth",
        block: "start"
      });
    });
  });
})();
</script>
</body>
</html>
"""


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
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_content_disposition() == "attachment":
                continue
            if part.get_content_type() not in (
                "text/plain", "text/html"
            ):
                continue

            payload = part.get_payload(decode=True)
            if payload is None:
                continue

            charset = part.get_content_charset() or "utf-8"
            try:
                parts.append(payload.decode(charset, errors="replace"))
            except LookupError:
                parts.append(payload.decode("utf-8", errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                parts.append(payload.decode(charset, errors="replace"))
            except LookupError:
                parts.append(payload.decode("utf-8", errors="replace"))

    text = "\n".join(parts)
    text = re.sub(
        r"(?is)<(script|style).*?>.*?</\1>", " ", text
    )
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def find_amount(text):
    patterns = [
        r"(?:amount|received|credited|payment)\s*"
        r"(?:of|:|-)?\s*(?:INR|Rs\.?|₹)\s*"
        r"([0-9,]+(?:\.[0-9]{1,2})?)",
        r"(?:INR|Rs\.?|₹)\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return amount_value(match.group(1))
    return None


def find_utr(text):
    patterns = [
        r"(?:UTR|RRN|UPI transaction ID|transaction ID|"
        r"txn ID|reference number|reference no\.?)"
        r"\s*[:#-]?\s*([A-Za-z0-9/-]{8,35})"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def read_gmail(gmail, app_password, limit=100):
    domain = gmail.rsplit("@", 1)[-1].lower()

    if domain not in ("gmail.com", "googlemail.com"):
        raise ValueError("A Gmail address is required.")

    password = str(app_password).replace(" ", "")
    if not password:
        raise ValueError("Gmail App Password is missing.")

    messages = []

    with imaplib.IMAP4_SSL(
        "imap.gmail.com",
        993,
        ssl_context=ssl.create_default_context(),
        timeout=20
    ) as imap:
        imap.login(gmail, password)

        status, _ = imap.select("INBOX", readonly=True)
        if status != "OK":
            raise RuntimeError("Cannot open Gmail inbox.")

        status, data = imap.search(None, "ALL")
        if status != "OK" or not data or not data[0]:
            return []

        ids = data[0].split()[-limit:]

        for msg_id in reversed(ids):
            status, fetched = imap.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            raw = next(
                (item[1] for item in fetched if isinstance(item, tuple)),
                None
            )
            if not raw:
                continue

            msg = email.message_from_bytes(raw)
            subject = decode_mime(msg.get("Subject", ""))
            sender = decode_mime(msg.get("From", ""))
            body = extract_email_text(msg)
            combined = subject + " " + body

            keywords = (
                "credited", "received", "payment", "upi",
                "transaction", "transfer"
            )

            if not any(word in combined.lower() for word in keywords):
                continue

            messages.append({
                "subject": subject,
                "sender": sender,
                "body": body,
                "date": msg.get("Date", ""),
                "message_id": msg.get("Message-ID", "")
            })

    return messages


def verify_email(info, order):
    try:
        messages = read_gmail(
            info.get("gmail", ""),
            info.get("gpass", "")
        )
    except Exception:
        return {
            "state": "unavailable",
            "message": (
                "Gmail check failed. Check App Password, IMAP access "
                "and hosting connectivity."
            )
        }

    order_id = order["order_id"]
    expected_amount = amount_value(order["amount"])

    for msg in messages:
        text = msg["subject"] + " " + msg["body"]

        # The email must contain this order's exact ID.
        if order_id.upper() not in text.upper():
            continue

        paid_amount = find_amount(text)
        utr = find_utr(text)

        if paid_amount is None:
            return {
                "state": "review",
                "message": "Order ID found, but email amount was not identified."
            }

        if paid_amount != expected_amount:
            return {
                "state": "mismatch",
                "message": "Email amount does not match the order."
            }

        if not utr:
            return {
                "state": "review",
                "message": "Order ID and amount found, but UTR was not identified."
            }

        return {
            "state": "matched",
            "amount": paid_amount,
            "utr": utr,
            "date": msg["date"],
            "sender": msg["sender"],
            "message_id": msg["message_id"]
        }

    return {
        "state": "pending",
        "message": "No matching payment email found."
    }


def request_data():
    data = {str(k).lower(): v for k, v in request.args.items()}
    body = request.get_json(silent=True) or {}

    for key, value in body.items():
        data.setdefault(str(key).lower(), value)

    return data


@app.route("/")
def home():
    if request.args.get("json") == "1":
        return jsonify({
            "ok": True,
            "service": "FamPay Payment API",
            "endpoints": [
                "/health",
                "/create_key",
                "/fam_create",
                "/fam_verify"
            ]
        })
    return render_template_string(HTML_PAGE)


@app.route("/health")
def health():
    return jsonify({
        "ok": True,
        "imap_host": "imap.gmail.com",
        "upi_configured": bool(FAMPAY_UPI),
        "total_keys": len(BotKeys),
        "total_orders": len(Orders)
    })


@app.route("/create_key", methods=["POST"])
def create_key():
    data = request.get_json(silent=True) or {}

    gmail = str(data.get("gmail") or data.get("email") or "").strip()
    gpass = str(
        data.get("gpass") or data.get("app_password") or ""
    ).replace(" ", "")
    mobile = str(data.get("mobile") or data.get("phone") or "")

    if not gmail.lower().endswith(("@gmail.com", "@googlemail.com")):
        return jsonify({
            "status": "error",
            "message": "A Gmail address is required."
        }), 400

    if len(gpass) != 16:
        return jsonify({
            "status": "error",
            "message": "Enter the 16-character Google App Password."
        }), 400

    api_key = "FAM_" + secrets.token_hex(16)

    with LOCK:
        BotKeys[api_key] = {
            "gmail": gmail,
            "gpass": gpass,
            "mobile": mobile,
            "created": int(time.time())
        }
        save_json(KEYS_FILE, BotKeys)

    return jsonify({
        "status": "success",
        "api_key": api_key,
        "gmail": gmail
    }), 201


@app.route("/register_key", methods=["POST"])
def register_key():
    data = request.get_json(silent=True) or {}

    api_key = str(data.get("api_key") or data.get("key") or "").strip()
    gmail = str(data.get("gmail") or data.get("email") or "").strip()
    gpass = str(
        data.get("gpass") or data.get("app_password") or ""
    ).replace(" ", "")
    mobile = str(data.get("mobile") or "")

    if not api_key or not gmail or len(gpass) != 16:
        return jsonify({
            "status": "error",
            "message": "api_key, Gmail and 16-character App Password required."
        }), 400

    if not gmail.lower().endswith(("@gmail.com", "@googlemail.com")):
        return jsonify({
            "status": "error",
            "message": "A Gmail address is required."
        }), 400

    with LOCK:
        BotKeys[api_key] = {
            "gmail": gmail,
            "gpass": gpass,
            "mobile": mobile,
            "created": int(time.time())
        }
        save_json(KEYS_FILE, BotKeys)

    return jsonify({"status": "success", "api_key": api_key}), 201


@app.route("/fam_create", methods=["GET", "POST"])
def fam_create():
    data = request_data()

    api_key = str(
        data.get("api_key") or data.get("apikey") or data.get("key") or ""
    ).strip()
    amount = amount_value(data.get("amount") or data.get("amt"))

    if not api_key:
        return jsonify({"status": "error", "message": "api_key required"}), 400

    if api_key not in BotKeys:
        return jsonify({"status": "error", "message": "Invalid api_key"}), 401

    if amount is None:
        return jsonify({
            "status": "error",
            "message": "amount must be greater than 0 and at most 100000"
        }), 400

    order_id = (
        "FAMPAY"
        + datetime.utcnow().strftime("%Y%m%d%H%M%S")
        + secrets.token_hex(4).upper()
    )

    upi_link = "upi://pay?" + urllib.parse.urlencode({
        "pa": FAMPAY_UPI,
        "am": f"{amount:.2f}",
        "cu": "INR",
        "tn": order_id
    })

    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/?"
        + urllib.parse.urlencode({
            "size": "400x400",
            "data": upi_link
        })
    )

    now = int(time.time())

    order = {
        "order_id": order_id,
        "amount": amount,
        "api_key": api_key,
        "upi": FAMPAY_UPI,
        "upi_link": upi_link,
        "qr_code": qr_url,
        "created": now,
        "expiry": now + 300,
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
            "qr_code": qr_url,
            "expires_in": 300,
            "expires_at": now + 300
        }
    }), 201


@app.route("/fam_verify", methods=["GET", "POST"])
def fam_verify():
    data = request_data()

    api_key = str(
        data.get("api_key")
        or data.get("apikey")
        or data.get("key")
        or request.headers.get("x-api-key")
        or ""
    ).strip()

    order_id = str(
        data.get("order_id")
        or data.get("orderid")
        or data.get("order")
        or data.get("id")
        or ""
    ).strip()

    if not api_key:
        return jsonify({"status": "error", "message": "api_key required"}), 400

    if api_key not in BotKeys:
        return jsonify({"status": "error", "message": "Invalid api_key"}), 401

    if not order_id:
        return jsonify({"status": "error", "message": "order_id required"}), 400

    with LOCK:
        order = Orders.get(order_id)

        if not order:
            return jsonify({
                "status": "error",
                "message": "Order not found",
                "order_id": order_id
            }), 404

        if order.get("api_key") != api_key:
            return jsonify({
                "status": "error",
                "message": "Order does not belong to this API key"
            }), 403

        if order.get("status") == "verified":
            return jsonify({
                "status": "success",
                "message": "Already verified",
                "data": {
                    "order_id": order_id,
                    "amount": order.get("amount"),
                    "utr": order.get("utr"),
                    "transaction_id": order.get("utr"),
                    "payment_time": order.get("payment_time")
                }
            })

    result = verify_email(BotKeys[api_key], order)

    if result["state"] == "unavailable":
        return jsonify({
            "status": "error",
            "message": result["message"],
            "order_id": order_id,
            "retry": True
        }), 503

    if result["state"] == "pending":
        return jsonify({
            "status": "pending",
            "message": result["message"],
            "order_id": order_id
        }), 200

    if result["state"] in ("review", "mismatch"):
        return jsonify({
            "status": "error",
            "message": result["message"],
            "order_id": order_id
        }), 409

    utr = result["utr"]

    with LOCK:
        # Prevent reusing a UTR for a different order.
        for existing_order, record in PaidRecords.items():
            if (
                str(record.get("utr", "")).casefold() == utr.casefold()
                and existing_order != order_id
            ):
                return jsonify({
                    "status": "error",
                    "message": "This UTR has already been used",
                    "order_id": order_id
                }), 409

        order = Orders[order_id]

        if order.get("status") == "verified":
            return jsonify({
                "status": "success",
                "message": "Already verified",
                "order_id": order_id
            })

        order["status"] = "verified"
        order["utr"] = utr
        order["payment_time"] = result["date"]
        order["verified_at"] = int(time.time())

        Orders[order_id] = order
        PaidRecords[order_id] = {
            "utr": utr,
            "amount": result["amount"],
            "verified_at": int(time.time()),
            "gmail": BotKeys[api_key]["gmail"]
        }

        save_json(ORDERS_FILE, Orders)
        save_json(PAID_FILE, PaidRecords)

    return jsonify({
        "status": "success",
        "data": {
            "order_id": order_id,
            "transaction_id": utr,
            "utr": utr,
            "amount": result["amount"],
            "payment_time": result["date"],
            "sender_name": result["sender"]
        }
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
    
