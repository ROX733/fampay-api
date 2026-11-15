from mongo_storage import read_state, write_state
import os
import json
import time
import hmac
from collections import Counter
from datetime import datetime, timezone
from functools import wraps
from flask import request, Response, render_template_string, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_LOG_FILE = os.path.join(BASE_DIR, "admin_activity.json")

ADMIN_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FamPay API — Admin Panel</title>
<style>
:root{color-scheme:dark;--bg:#0b1020;--card:#151d33;--line:#283550;--muted:#9ba9c5;--text:#f4f6ff;--purple:#9277ff;--green:#38d99a;--red:#ff7188;--amber:#ffc56d}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 10% 0,#30245d 0,transparent 38%),var(--bg);color:var(--text);font:14px Inter,system-ui,sans-serif}
.wrap{max-width:1200px;margin:auto;padding:28px 18px 60px}.top{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:24px}
h1{font-size:26px;margin:0;letter-spacing:-.8px}.sub{color:var(--muted);font-size:12px;margin-top:7px}
a{color:#c8bdff;text-decoration:none}.pill{border:1px solid var(--line);padding:9px 12px;border-radius:11px;background:#151d33;font-size:12px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.card{background:linear-gradient(145deg,#18223b,#121a2d);border:1px solid var(--line);border-radius:16px;padding:17px;min-width:0}
.metric{font-size:27px;font-weight:800;margin-top:8px}.label{font-size:11px;color:var(--muted);font-weight:700;letter-spacing:.6px}.green{color:var(--green)}.red{color:var(--red)}.amber{color:var(--amber)}
.section{margin-top:24px}.section h2{font-size:16px;margin:0 0 12px}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:14px;background:#111a2d}
table{width:100%;border-collapse:collapse;min-width:760px}th,td{text-align:left;padding:12px 13px;border-bottom:1px solid #26334c;font-size:12px;vertical-align:top}th{color:#aab8d2;background:#18233b;font-size:10px;letter-spacing:.8px;text-transform:uppercase}td{color:#e6ebf7}tr:last-child td{border-bottom:0}.muted{color:var(--muted)}.tag{display:inline-block;padding:4px 8px;border-radius:99px;background:#26334c;font-size:10px;font-weight:800}.tag.success{color:var(--green);background:#123a34}.tag.failed{color:var(--red);background:#421f32}.tag.pending{color:var(--amber);background:#40331e}
.notice{margin:15px 0;padding:12px 14px;border:1px solid #5a4b2b;background:#2b261c;color:#f3d69c;border-radius:12px;font-size:11px;line-height:1.6}
@media(max-width:850px){.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:460px){.grid{grid-template-columns:1fr 1fr}.metric{font-size:22px}.wrap{padding:20px 12px}}
</style></head><body><main class="wrap">
<header class="top"><div><h1>🛡️ FamPay API Admin</h1><div class="sub">Private operations dashboard · refreshed {{ refreshed }}</div></div><a class="pill" href="/">← Developer Portal</a></header>
<div class="notice">Gmail App Passwords are intentionally masked. This dashboard never reveals or exports mailbox credentials. Protect this page with a strong admin password and HTTPS.</div>
<section class="grid">
<div class="card"><div class="label">TOTAL USERS / API KEYS</div><div class="metric">{{ users }}</div></div>
<div class="card"><div class="label">TOTAL QR GENERATED</div><div class="metric">{{ total_qr }}</div></div>
<div class="card"><div class="label">SUCCESSFUL ORDERS</div><div class="metric green">{{ successful }}</div></div>
<div class="card"><div class="label">FAILED VERIFICATIONS</div><div class="metric red">{{ failed }}</div></div>
<div class="card"><div class="label">PENDING ORDERS</div><div class="metric amber">{{ pending }}</div></div>
<div class="card"><div class="label">EXPIRED ORDERS</div><div class="metric">{{ expired }}</div></div>
<div class="card"><div class="label">TOTAL ACTIVITY EVENTS</div><div class="metric">{{ activity_count }}</div></div>
<div class="card"><div class="label">LINKED TELEGRAM USERS</div><div class="metric">{{ linked }}</div></div>
</section>
<section class="section"><h2>👤 Registered Users</h2><div class="table-wrap"><table><thead><tr><th>Gmail</th><th>UPI ID</th><th>Mobile</th><th>Gmail App Password</th><th>API Key</th><th>Created</th><th>Telegram</th></tr></thead><tbody>
{% for u in user_rows %}<tr><td>{{ u.gmail }}</td><td>{{ u.upi }}</td><td>{{ u.mobile }}</td><td><span class="tag">••••••••••••••••</span></td><td class="muted">{{ u.api_key }}</td><td>{{ u.created }}</td><td>{{ u.telegram }}</td></tr>{% else %}<tr><td colspan="7" class="muted">No API keys generated yet.</td></tr>{% endfor %}
</tbody></table></div></section>
<section class="section"><h2>📋 Individual Activity Logs</h2><div class="table-wrap"><table><thead><tr><th>Time (UTC)</th><th>Event</th><th>User</th><th>Order ID</th><th>Amount</th><th>Result</th><th>Details</th></tr></thead><tbody>
{% for e in logs %}<tr><td>{{ e.time }}</td><td>{{ e.event }}</td><td>{{ e.user }}</td><td>{{ e.order_id }}</td><td>{{ e.amount }}</td><td><span class="tag {{ e.result_class }}">{{ e.result }}</span></td><td>{{ e.details }}</td></tr>{% else %}<tr><td colspan="7" class="muted">No activity recorded yet.</td></tr>{% endfor %}
</tbody></table></div></section>
<div class="sub" style="margin-top:18px">Order counts are calculated from current order and payment records. Expired means a pending order whose expiry timestamp has passed.</div>
</main></body></html>"""

def _read_json(path):
    return read_state(path)

def _write_log(entry):
    rows = _read_json(ADMIN_LOG_FILE)
    key = str(time.time_ns())
    rows[key] = entry
    if len(rows) > 2000:
        rows = dict(sorted(rows.items(), key=lambda item: item[0])[-2000:])
    write_state(ADMIN_LOG_FILE, rows)

def _admin_required():
    username = os.getenv("ADMIN_USERNAME", "")
    password = os.getenv("ADMIN_PASSWORD", "")
    auth = request.authorization
    if not username or not password or not auth:
        return False
    return hmac.compare_digest(auth.username or "", username) and hmac.compare_digest(auth.password or "", password)

def register_admin_panel(app):
    @app.before_request
    def _capture_admin_event_context():
        request._admin_started_at = time.time()

    @app.after_request
    def _record_admin_activity(response):
        endpoint = request.endpoint or ""
        event_names = {
            "create_key": "API key generated",
            "fam_create": "QR / payment order created",
            "fam_verify": "Payment verification"
        }
        if endpoint not in event_names:
            return response
        try:
            body = request.get_json(silent=True) or {}
            api_key = str(body.get("api_key") or request.args.get("api_key") or request.headers.get("X-API-Key") or "")
            keys = _read_json(os.path.join(BASE_DIR, "keys.json"))
            orders = _read_json(os.path.join(BASE_DIR, "orders.json"))
            payload = response.get_json(silent=True) or {}
            status = str(payload.get("status", "")).lower()
            email = str(body.get("gmail") or (keys.get(api_key) or {}).get("gmail") or "Unknown")
            order_id = str(payload.get("data", {}).get("order_id") or payload.get("order_id") or body.get("order_id") or "")
            order = orders.get(order_id, {}) if order_id else {}
            result = "success" if status == "success" else "failed"
            details = str(payload.get("message") or "")
            if endpoint == "fam_verify" and ("expir" in details.lower() or response.status_code == 410):
                result = "expired"
            if endpoint == "fam_create":
                result = "success" if status == "success" else "failed"
            entry = {
                "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "event": event_names[endpoint],
                "user": email,
                "order_id": order_id or "—",
                "amount": str(order.get("amount", body.get("amount", "—"))),
                "result": result,
                "details": details[:180] or ("HTTP " + str(response.status_code))
            }
            _write_log(entry)
        except Exception as exc:
            app.logger.warning("Admin activity log write failed: %s", exc)
        return response

    @app.get("/admin")
    def admin_dashboard():
        if not _admin_required():
            return Response("Admin authentication required.", 401, {"WWW-Authenticate": 'Basic realm="FamPay Admin"'})
        keys = _read_json(os.path.join(BASE_DIR, "keys.json"))
        orders = _read_json(os.path.join(BASE_DIR, "orders.json"))
        paid = _read_json(os.path.join(BASE_DIR, "paid.json"))
        events = _read_json(ADMIN_LOG_FILE)
        now = int(time.time())
        expired_ids = {oid for oid, order in orders.items() if order.get("status") != "success" and int(order.get("expires_at", 0) or 0) <= now}
        successful = len(paid)
        expired = len(expired_ids)
        pending = sum(1 for oid, order in orders.items() if oid not in paid and oid not in expired_ids)
        failed = sum(1 for item in events.values() if item.get("event") == "Payment verification" and item.get("result") == "failed")
        user_rows = []
        for api_key, item in keys.items():
            user_rows.append({
                "gmail": item.get("gmail", "—"),
                "upi": item.get("upi", "—"),
                "mobile": item.get("mobile", "—"),
                "api_key": api_key[:9] + "••••••••",
                "created": str(item.get("created_at", "—"))[:19],
                "telegram": ("Linked · " + str(item.get("telegram_chat_id"))) if item.get("telegram_chat_id") else "Not linked"
            })
        linked_count = sum(1 for item in keys.values() if item.get("telegram_chat_id"))
        logs = sorted(events.values(), key=lambda item: item.get("time", ""), reverse=True)[:250]
        for item in logs:
            item["result_class"] = "success" if item.get("result") == "success" else ("pending" if item.get("result") in ("pending", "expired") else "failed")
        return render_template_string(
            ADMIN_HTML,
            users=len(keys), total_qr=len(orders), successful=successful,
            failed=failed, pending=pending, expired=expired,
            activity_count=len(events), linked=linked_count, user_rows=user_rows,
            logs=logs, refreshed=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        )
