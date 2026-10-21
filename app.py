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
<title>FamPay API Documentation</title>
<style>
*{box-sizing:border-box}
body{margin:0;padding:22px 14px;font:15px system-ui;
background:linear-gradient(130deg,#6756e8,#a56bd8,#6558d9);color:#202039}
main{max-width:760px;margin:auto}
.card{background:white;border-radius:20px;padding:22px;margin:16px 0;
box-shadow:0 15px 40px #24124b30}
h1{font-size:32px;margin:8px 0}
h2{font-size:20px}
p{line-height:1.65;color:#68687c}
.tag{display:inline-block;background:#7054e8;color:white;padding:5px 9px;
border-radius:7px;font-size:12px;font-weight:bold}
pre{background:#17172b;color:#eeeefb;padding:15px;border-radius:12px;
overflow:auto;font-size:12px}
.note{background:#f3efff;padding:12px;border-radius:10px;
color:#594a92;font-size:13px}
</style>
</head>
<body>
<main>
<section class="card">
<h1>FamPay <span style="color:#7054e8">API Docs</span></h1>
<p>Merchant-wise UPI IDs, API keys, payment order creation and Gmail email matching.</p>
<p><b>Endpoints:</b> POST /create_key · POST /register_key ·
GET/POST /fam_create · GET/POST /fam_verify · GET /health</p>
</section>

<section class="card">
<h2>1. Create Merchant API Key</h2>
<span class="tag">POST /create_key</span>
<p>Register the merchant's Gmail, Google App Password, mobile and UPI ID.</p>
<pre>{
  "gmail": "merchant@gmail.com",
  "gpass": "google_app_password",
  "mobile": "9876543210",
  "upi": "merchant@upi"
}</pre>
<p>Success response:</p>
<pre>{
  "status": "success",
  "api_key": "FAM_generated_key",
  "upi": "merchant@upi"
}</pre>
</section>

<section class="card">
<h2>2. Create Payment Order</h2>
<span class="tag">GET /fam_create</span>
<pre>/fam_create?amount=100&amp;api_key=YOUR_API_KEY</pre>
<p>Returns the order ID, merchant's registered UPI ID, UPI link, QR URL and expiry.</p>
</section>

<section class="card">
<h2>3. Verify Payment Email</h2>
<span class="tag">GET /fam_verify</span>
<pre>/fam_verify?order_id=ORDER_ID&amp;api_key=YOUR_API_KEY</pre>
<p class="note">Gmail email matching is not authoritative payment confirmation.
Use a trusted payment provider or bank verification API before crediting funds.</p>
</section>

<section class="card">
<h2>4. Health Check</h2>
<span class="tag">GET /health</span>
<pre>{"ok":true,"total_keys":0,"total_orders":0}</pre>
</section>
</main>
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
