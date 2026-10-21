
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
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FamPay Payment API</title>
<style>
*{box-sizing:border-box;font-family:system-ui,sans-serif}
body{margin:0;padding:16px;background:linear-gradient(135deg,#7b61ff,#9b6bff,#6a5cff)}
main{max-width:650px;margin:auto}
.card{background:white;border-radius:18px;padding:20px;margin:12px 0;box-shadow:0 8px 25px #0002}
h1{text-align:center}.muted{color:#666}
.code{background:#111;color:#00ff88;padding:12px;border-radius:10px;overflow-wrap:anywhere}
</style>
</head>
<body><main>
<div class="card">
<h1>FamPay Payment API</h1>
<p class="muted">UPI orders and Gmail payment-email matching.</p>
</div>
<div class="card"><b>Create API Key</b><p class="code">POST /create_key</p><p>JSON: gmail, gpass, mobile</p></div>
<div class="card"><b>Create Order</b><p class="code">GET /fam_create?amount=10&amp;api_key=YOUR_KEY</p></div>
<div class="card"><b>Verify Payment</b><p class="code">GET /fam_verify?order_id=ORDER_ID&amp;api_key=YOUR_KEY</p></div>
<div class="card"><b>Health</b><p class="code">GET /health</p></div>
</main></body></html>
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
    
