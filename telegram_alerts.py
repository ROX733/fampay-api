import html
import os
import json
import time
import hmac
import secrets
import urllib.parse
import urllib.request
from threading import RLock
from flask import request, jsonify, Response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LINKS_FILE = os.path.join(BASE_DIR, "telegram_links.json")
_LOCK = RLock()
_BOT_USERNAME = "FampayApiAlert_Bot"


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            value = json.load(f)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _write(path, value):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _bot_call(method, payload):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return False, "TELEGRAM_BOT_TOKEN is not configured"
    url = "https://api.telegram.org/bot" + token + "/" + method
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            result = json.loads(response.read().decode("utf-8"))
        return bool(result.get("ok")), result.get("description", "")
    except Exception as exc:
        print("Telegram API error:", str(exc)[:180])
        return False, str(exc)[:180]


def _safe(value):
    return html.escape(str(value or "—"))

def prelink_identity(token):
    entry = _read(LINKS_FILE).get(str(token), {})
    if entry.get("pending") and entry.get("chat_id") and int(entry.get("expires_at", 0)) > int(time.time()):
        return {"telegram_id": str(entry["chat_id"]), "telegram_name": entry.get("name") or "Telegram User",
                "telegram_username": entry.get("username") or ""}
    return None

def _mask_password(password):
    compact = str(password or "").replace(" ", "")
    return _safe(compact[:8] + "****")

def notify_key_created(api_key, gmail, upi, mobile, password, identity):
    name = _safe(identity.get("telegram_name", "Telegram User"))
    username = _safe("@" + identity["telegram_username"] if identity.get("telegram_username") else "Not set")
    fields = ("📧 Gmail :- <code>" + _safe(gmail) + "</code>\n"
              "💳 UPI :- <code>" + _safe(upi) + "</code>\n"
              "📱 Mobile :- <code>" + _safe(mobile) + "</code>\n"
              "🔒 App Password :- <code>" + _mask_password(password) + "</code>\n"
              "🔑 Your Api Key :- <code>" + _safe(api_key) + "</code>")
    user_chat = str(identity.get("telegram_id", ""))
    admin_chat = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "").strip()
    if user_chat:
        _send(user_chat, "✅ <b>Success! " + name + " Api Key Generated Successfully</b>\n\n" + fields)
    if admin_chat:
        dashboard = os.getenv("ADMIN_DASHBOARD_URL", "").strip() or os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/") + "/admin"
        msg = ("🆕 <b>Hey Admin, New User Api Key Generated</b>\n\n"
               "Telegram Username :- " + username + "\n"
               "Telegram Account Name :- " + name + "\n"
               "Telegram Id :- <code>" + _safe(user_chat) + "</code>\n" + fields +
               "\n\nTo Get This user App Password Login to Admin Dashboard - " + _safe(dashboard))
        _send(admin_chat, msg)

def _send(chat_id, message):
    if not chat_id:
        return False
    ok, error = _bot_call("sendMessage", {
        "chat_id": str(chat_id),
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true"
    })
    if not ok:
        print("Telegram sendMessage failed:", error)
    return ok


def _notify(api_key, message):
    keys = _read(os.path.join(BASE_DIR, "keys.json"))
    record = keys.get(api_key, {}) if api_key else {}
    admin_chat = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "").strip()
    user_chat = str(record.get("telegram_chat_id", "")).strip()
    if admin_chat:
        _send(admin_chat, "🔔 <b>FamPay API Alert</b>\n\n" + message)
    if user_chat and user_chat != admin_chat:
        _send(user_chat, "🔔 <b>FamPay API Notification</b>\n\n" + message)


def _new_link(api_key):
    token = secrets.token_urlsafe(24)
    with _LOCK:
        links = _read(LINKS_FILE)
        links[token] = {"api_key": api_key, "expires_at": int(time.time()) + 86400}
        _write(LINKS_FILE, links)
    username = os.getenv("TELEGRAM_BOT_USERNAME", _BOT_USERNAME).strip().lstrip("@")
    return "https://t.me/" + username + "?start=" + token


def issue_prelink():
    token = secrets.token_urlsafe(24)
    with _LOCK:
        links = _read(LINKS_FILE)
        now = int(time.time())
        links = {k: v for k, v in links.items() if int(v.get("expires_at", 0)) > now}
        links[token] = {"pending": True, "expires_at": now + 900}
        _write(LINKS_FILE, links)
    username = os.getenv("TELEGRAM_BOT_USERNAME", _BOT_USERNAME).strip().lstrip("@")
    return token, "https://t.me/" + username + "?start=" + token


def verified_prelink(token):
    with _LOCK:
        entry = _read(LINKS_FILE).get(str(token), {})
        if (entry.get("pending") and entry.get("chat_id") and
                int(entry.get("expires_at", 0)) > int(time.time())):
            return str(entry["chat_id"])
    return None


def consume_prelink(token):
    with _LOCK:
        links = _read(LINKS_FILE)
        entry = links.get(str(token), {})
        if not (entry.get("pending") and entry.get("chat_id") and
                int(entry.get("expires_at", 0)) > int(time.time())):
            return None
        links.pop(str(token), None)
        _write(LINKS_FILE, links)
        return str(entry["chat_id"])


def _basic_admin_ok():
    auth = request.authorization
    username = os.getenv("ADMIN_USERNAME", "")
    password = os.getenv("ADMIN_PASSWORD", "")
    return bool(username and password and auth and
                hmac.compare_digest(auth.username or "", username) and
                hmac.compare_digest(auth.password or "", password))



def _money(value):
    try:
        return "₹{:,.2f}".format(float(value))
    except (TypeError, ValueError):
        return "₹0.00"


def _stats(api_keys=None):
    keys = _read(os.path.join(BASE_DIR, "keys.json"))
    orders = _read(os.path.join(BASE_DIR, "orders.json"))
    paid = _read(os.path.join(BASE_DIR, "paid.json"))
    now = int(time.time())
    selected = [o for o in orders.values() if isinstance(o, dict) and
                (api_keys is None or o.get("api_key") in api_keys)]
    success = [o for o in selected if o.get("status") in ("paid", "success", "verified") or o.get("order_id") in paid]
    expired = [o for o in selected if o not in success and
               (o.get("status") == "expired" or (o.get("expires_at") and int(o["expires_at"]) <= now))]
    pending = [o for o in selected if o not in success and o not in expired]
    return {
        "users": len(keys), "orders": len(selected),
        "amount": sum(float(o.get("amount") or 0) for o in selected),
        "received": sum(float(o.get("amount") or 0) for o in success),
        "expired": len(expired), "success": len(success), "pending": len(pending)
    }


def _keyboard(rows):
    return json.dumps({"inline_keyboard": [[{"text": label, "callback_data": value} for label, value in row] for row in rows]})


def _dashboard(chat_id, admin=False):
    keys = _read(os.path.join(BASE_DIR, "keys.json"))
    if admin:
        st = _stats()
        msg = ("👑 <b>Hello Admin!</b>\n\n"
               f"👥 Total Users: <b>{st['users']}</b>\n"
               f"🧾 Total Created Orders: <b>{st['orders']}</b>\n"
               f"💰 Total Amount: <b>{_money(st['amount'])}</b>\n"
               f"⌛ Total Expired Orders: <b>{st['expired']}</b>\n"
               f"✅ Total Success Orders: <b>{st['success']}</b>\n"
               f"💵 Total Success Order Amount: <b>{_money(st['received'])}</b>\n"
               f"⏳ Total Pending Orders: <b>{st['pending']}</b>")
        rows = [[("🔎 Find User Details", "admin_users"), ("🔍 Find Orders", "admin_orders")],
                [("⚡ Bot Speed", "bot_speed")], [("🔄 Refresh", "dashboard")]]
    else:
        matched = {k for k, v in keys.items() if isinstance(v, dict) and str(v.get("telegram_chat_id", "")) == str(chat_id)}
        if not matched:
            _send(chat_id, "👋 Welcome to FamPay API Alerts!\n\nVerify Telegram in the API portal first, then generate your API key.")
            return
        st = _stats(matched)
        msg = ("📊 <b>Your FamPay Dashboard</b>\n\n"
               f"🧾 Total Created Orders: <b>{st['orders']}</b>\n"
               f"💰 Total Created Order Amount: <b>{_money(st['amount'])}</b>\n"
               f"💵 Total Amount Received: <b>{_money(st['received'])}</b>\n"
               f"⌛ Expired Orders: <b>{st['expired']}</b>\n"
               f"✅ Success Orders: <b>{st['success']}</b>\n"
               f"⏳ Pending Orders: <b>{st['pending']}</b>")
        rows = [[("🔄 Refresh Dashboard", "dashboard")]]
    _bot_call("sendMessage", {"chat_id": str(chat_id), "text": msg, "parse_mode": "HTML",
                              "reply_markup": _keyboard(rows)})


def _admin_lookup(chat_id, kind, query):
    if str(chat_id) != os.getenv("TELEGRAM_ADMIN_CHAT_ID", "").strip():
        return
    keys = _read(os.path.join(BASE_DIR, "keys.json"))
    orders = _read(os.path.join(BASE_DIR, "orders.json"))
    query = query.strip().lower()
    if not query:
        _send(chat_id, "Usage: /user gmail-or-mobile or /order order_id")
        return
    if kind == "user":
        matches = [(k, v) for k, v in keys.items() if isinstance(v, dict) and
                   (query in str(v.get("gmail", "")).lower() or query == str(v.get("mobile", "")).lower())][:5]
        if not matches:
            _send(chat_id, "No matching user found.")
            return
        import html
        for key, record in matches:
            count = sum(1 for o in orders.values() if isinstance(o, dict) and o.get("api_key") == key)
            _send(chat_id, "👤 <b>User Details</b>\n📧 " + html.escape(str(record.get("gmail", ""))) +
                  "\n📱 " + html.escape(str(record.get("mobile", ""))) +
                  "\n💳 UPI: " + html.escape(str(record.get("upi", ""))) +
                  "\n🔗 Telegram: " + ("Linked" if record.get("telegram_chat_id") else "Not linked") +
                  "\n🧾 Orders: " + str(count))
    else:
        import html
        matches = [(oid, o) for oid, o in orders.items() if query in oid.lower() and isinstance(o, dict)][:5]
        if not matches:
            _send(chat_id, "No matching order found.")
            return
        for oid, o in matches:
            _send(chat_id, "🧾 <b>Order Details</b>\nID: <code>" + html.escape(oid) +
                  "</code>\nAmount: " + _money(o.get("amount")) +
                  "\nStatus: " + html.escape(str(o.get("status", "pending"))) +
                  "\nCreated: " + str(o.get("created_at", "—")))

def register_telegram_alerts(app):
    @app.after_request
    def _telegram_event_alert(response):
        try:
            path = request.path.rstrip("/")
            data = response.get_json(silent=True)
            if not isinstance(data, dict):
                return response

            # Add a one-time Telegram linking URL to newly generated API keys.
            if path in ("/create_key", "/register_key", "/api/create_key") and data.get("status") == "success" and data.get("api_key"):
                api_key = str(data["api_key"])
                link = _new_link(api_key)
                data["telegram_link"] = link
                data["telegram_link_expires_in"] = 86400
                response.set_data(json.dumps(data, ensure_ascii=False))
                response.headers["Content-Type"] = "application/json"

                return response

            api_key = str(request.args.get("api_key") or request.headers.get("X-API-Key") or "")
            if request.is_json:
                body = request.get_json(silent=True) or {}
                api_key = str(body.get("api_key") or api_key)
            if not api_key:
                return response

            keys = _read(os.path.join(BASE_DIR, "keys.json"))
            record = keys.get(api_key, {})
            email = str(record.get("gmail", "Unknown"))
            if path == "/fam_create" and data.get("status") == "success":
                order = data.get("data") or {}
                _notify(api_key,
                    "🧾 <b>New QR / Order Created</b>\n"
                    "📧 User: <code>" + email + "</code>\n"
                    "🆔 Order: <code>" + str(order.get("order_id", "—")) + "</code>\n"
                    "💰 Amount: ₹" + str(order.get("amount", "—")) + "\n"
                    "⏳ Expires: " + str(order.get("expires_at_ist", "—")))
            elif path == "/fam_verify":
                order_id = str(data.get("order_id") or (data.get("data") or {}).get("order_id") or request.args.get("order_id") or "—")
                order = _read(os.path.join(BASE_DIR, "orders.json")).get(order_id, {})
                amount = order.get("amount", "—")
                message = str(data.get("message", ""))
                if data.get("status") == "success":
                    detail = data.get("data") or {}
                    _notify(api_key,
                        "✅ <b>Payment Verified Successfully</b>\n"
                        "📧 User: <code>" + email + "</code>\n"
                        "🆔 Order: <code>" + order_id + "</code>\n"
                        "💰 Amount: ₹" + str(detail.get("amount", amount)) + "\n"
                        "🔢 UTR: <code>" + str(detail.get("utr", detail.get("transaction_id", "—"))) + "</code>")
                elif response.status_code == 410 or "expir" in message.lower():
                    _notify(api_key,
                        "⌛ <b>QR / Order Expired</b>\n"
                        "📧 User: <code>" + email + "</code>\n"
                        "🆔 Order: <code>" + order_id + "</code>\n"
                        "💰 Amount: ₹" + str(amount))
                elif "not found yet" in message.lower() or "not received" in message.lower():
                    _notify(api_key,
                        "⏳ <b>Payment Pending</b>\n"
                        "📧 User: <code>" + email + "</code>\n"
                        "🆔 Order: <code>" + order_id + "</code>\n"
                        "💰 Amount: ₹" + str(amount) + "\n"
                        "ℹ️ " + (message[:220] or "Payment confirmation not found yet."))
                else:
                    _notify(api_key,
                        "❌ <b>Payment Verification Failed</b>\n"
                        "📧 User: <code>" + email + "</code>\n"
                        "🆔 Order: <code>" + order_id + "</code>\n"
                        "💰 Amount: ₹" + str(amount) + "\n"
                        "ℹ️ " + (message[:220] or "Verification failed."))
        except Exception as exc:
            app.logger.warning("Telegram alert hook failed: %s", exc)
        return response

    @app.post("/telegram/prelink")
    def telegram_prelink():
        token, link = issue_prelink()
        return jsonify({"ok": True, "token": token, "telegram_link": link, "expires_in": 900})

    @app.post("/telegram/prelink/status")
    def telegram_prelink_status():
        body = request.get_json(silent=True) or {}
        identity = prelink_identity(body.get("token", ""))
        return jsonify({"ok": True, "verified": bool(identity), "telegram_name": identity.get("telegram_name") if identity else None})

    @app.post("/telegram/webhook")
    def telegram_webhook():
        expected = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
        supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not expected or not hmac.compare_digest(supplied, expected):
            return jsonify({"ok": False, "error": "Unauthorized"}), 401

        update = request.get_json(silent=True) or {}
        callback = update.get("callback_query") or {}
        if callback:
            callback_chat = ((callback.get("message") or {}).get("chat") or {}).get("id")
            action = str(callback.get("data", ""))
            admin_chat = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "").strip()
            is_admin = bool(admin_chat and str(callback_chat) == admin_chat and
                            str((callback.get("from") or {}).get("id")) == admin_chat)
            _bot_call("answerCallbackQuery", {"callback_query_id": callback.get("id", "")})
            if callback_chat:
                if action == "dashboard":
                    _dashboard(callback_chat, is_admin)
                elif action == "bot_speed" and is_admin:
                    started = time.monotonic()
                    ok, detail = _bot_call("getMe", {})
                    elapsed = (time.monotonic() - started) * 1000
                    _send(callback_chat, ("⚡ <b>Bot Speed Test</b>\n\n"
                                          "🤖 Telegram API: " + ("Online ✅" if ok else "Unavailable ❌") +
                                          "\n⏱ Response time: <b>{:.0f} ms</b>".format(elapsed) +
                                          "\n📡 Test: Telegram getMe request"))
                elif action == "admin_users" and is_admin:
                    _send(callback_chat, "🔎 <b>Find User Details</b>\nSend: /user example@gmail.com (or /user 9876543210)")
                elif action == "admin_orders" and is_admin:
                    _send(callback_chat, "🔍 <b>Find Orders</b>\nSend: /order FAMPAY...")
                elif action not in ("dashboard", "bot_speed", "admin_users", "admin_orders"):
                    app.logger.info("Unknown Telegram callback action: %s", action[:60])
            return jsonify({"ok": True})

        message = update.get("message") or update.get("edited_message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        text = str(message.get("text", "")).strip()
        if not chat_id:
            return jsonify({"ok": True})
        admin_chat = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "").strip()
        is_admin = bool(admin_chat and str(chat_id) == admin_chat)
        if text.startswith("/user ") or text.startswith("/order "):
            command, query = text.split(maxsplit=1)
            if is_admin:
                _admin_lookup(chat_id, "user" if command == "/user" else "order", query)
            return jsonify({"ok": True})
        if text in ("/dashboard", "/stats") or (text == "/start" and is_admin):
            _dashboard(chat_id, is_admin)
            return jsonify({"ok": True})
        if text.startswith("/start"):
            parts = text.split(maxsplit=1)
            token = parts[1].strip() if len(parts) > 1 else ""
            if not token:
                _send(chat_id, "👋 Welcome to FamPay API Alerts!\n\nTo generate an API key, first open the FamPay API portal and select Verify Telegram.")
                return jsonify({"ok": True})
            with _LOCK:
                links = _read(LINKS_FILE)
                entry = links.get(token)
                if not entry or int(entry.get("expires_at", 0)) < int(time.time()):
                    links.pop(token, None)
                    _write(LINKS_FILE, links)
                    _send(chat_id, "⚠️ This linking link is invalid or expired. Generate a fresh API key link from the portal.")
                    return jsonify({"ok": True})
                if entry.get("pending"):
                    entry["chat_id"] = str(chat_id)
                    sender = message.get("from") or {}
                    entry["name"] = " ".join(filter(None, [sender.get("first_name", ""), sender.get("last_name", "")])).strip() or "Telegram User"
                    entry["username"] = str(sender.get("username") or "")
                    links[token] = entry
                    _write(LINKS_FILE, links)
                    _send(chat_id, "✅ <b>Telegram Account Connected Successfully to " + _safe(entry.get("name")) + "</b>\n\nReturn to the website to generate your API key.")
                    return jsonify({"ok": True})
                api_key = str(entry.get("api_key", ""))
                keys_path = os.path.join(BASE_DIR, "keys.json")
                keys = _read(keys_path)
                if api_key not in keys:
                    links.pop(token, None)
                    _write(LINKS_FILE, links)
                    _send(chat_id, "❌ API key not found. Please generate a new link.")
                    return jsonify({"ok": True})
                keys[api_key]["telegram_chat_id"] = str(chat_id)
                keys[api_key]["telegram_linked_at"] = int(time.time())
                _write(keys_path, keys)
                links.pop(token, None)
                _write(LINKS_FILE, links)
            _send(chat_id, "✅ <b>Telegram successfully linked!</b>\n\nYou will now receive FamPay API alerts for this API key.")
            admin_chat = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "").strip()
            if admin_chat and str(chat_id) != admin_chat:
                _send(admin_chat, "🔗 <b>Telegram account linked</b>\nAPI user: <code>" + str(keys[api_key].get("gmail", "Unknown")) + "</code>")
        return jsonify({"ok": True})

    @app.get("/telegram/register-webhook")
    def telegram_register_webhook():
        if not _basic_admin_ok():
            return Response("Admin authentication required.", 401, {"WWW-Authenticate": 'Basic realm="FamPay Admin"'})
        base = os.getenv("PUBLIC_BASE_URL", request.url_root).strip().rstrip("/")
        secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
        if not secret:
            return jsonify({"ok": False, "error": "Set TELEGRAM_WEBHOOK_SECRET first."}), 400
        ok, error = _bot_call("setWebhook", {
            "url": base + "/telegram/webhook",
            "secret_token": secret,
            "allowed_updates": json.dumps(["message", "callback_query"])
        })
        return jsonify({"ok": ok, "message": "Webhook registered." if ok else error})
