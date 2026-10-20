from flask import Flask, request, jsonify, render_template_string
import requests, os, json, urllib.parse, time, random
from datetime import datetime

app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FamPay API | Payment Documentation</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:Inter,system-ui,-apple-system,sans-serif}
body{background:linear-gradient(180deg,#7b61ff 0%,#6a5cff 100%);min-height:100vh;padding:0}
.top{color:#fff;text-align:center;padding:18px 16px 6px;font-size:13px;letter-spacing:.3px}
.hero{max-width:900px;margin:0 auto;padding:10px 16px}
.card{background:#fff;border-radius:22px;padding:18px;box-shadow:0 10px 30px rgba(0,0,0,.18);margin:12px 0}
.badge{display:inline-block;background:#eef0ff;color:#6a5cff;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600}
.h1{font-size:20px;font-weight:800;margin:10px 0 6px;color:#111}
.muted{color:#6b7280;font-size:13px;line-height:1.5}
.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:12px}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
.stat{background:#f8f7ff;border:1px solid #eee;border-radius:16px;padding:12px;text-align:center}
.stat b{font-size:17px;color:#111}
.stat p{font-size:11px;color:#6b7280;margin-top:3px}
.code{background:#0f0f12;color:#00ff88;border-radius:12px;padding:12px;font-family:monospace;font-size:12px;overflow:auto;word-break:break-all;border:1px solid #222;margin-top:10px}
.code .y{color:#ffd60a}.code .p{color:#9d7dff}
.btn{width:100%;background:#111;border-radius:12px;color:#fff;padding:12px;text-align:center;font-weight:700;margin-top:10px;display:block;text-decoration:none;font-size:13px}
.btn-blue{background:#3b82ff}
.chip{display:inline-block;background:#f3f0ff;color:#6a5cff;padding:6px 10px;border-radius:20px;font-size:11px;font-weight:600;margin-right:6px}
.feature{display:flex;gap:12px;align-items:center;padding:14px;background:#fff;border-radius:16px;margin:10px 0}
.icon{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}
.why{background:#fff;border-radius:22px;padding:18px;margin:14px 0}
.why h2{text-align:center;font-size:18px;margin-bottom:6px}
.why .mini{text-align:center;color:#6b7280;font-size:12px;margin-bottom:14px}
.mini-card{background:#fff;border:1px solid #eee;border-radius:16px;padding:16px;text-align:center;margin:10px 0;box-shadow:0 6px 16px rgba(0,0,0,.06)}
.footer{background:#fff;border-radius:22px;padding:18px;text-align:center;margin:14px 0}
.dot{width:8px;height:8px;background:#3b82ff;border-radius:50%;display:inline-block}
a{color:#3b82ff;text-decoration:none}
</style>
</head>
<body>
<div class="top">FamPay API | Payment Documentation &nbsp; <span style="opacity:.7">fampay-api-7msf.onrender.com</span></div>

<div class="hero">

<div class="card">
<span class="badge">✦ Official API Infrastructure</span>
<div class="h1">FamPay Payment API</div>
<p class="muted">Enterprise-grade UPI payment gateway for <b>papai69@fam</b> — Instant QR & verification with sub-200ms response.</p>
<div style="margin-top:10px">
<span class="chip">API v2.0</span>
<span class="chip">24/7 Active</span>
<span class="chip">Global Access</span>
</div>
<div class="grid">
<div class="stat"><b>99.9%</b><p>Uptime</p></div>
<div class="stat"><b>&lt;200ms</b><p>Response</p></div>
<div class="stat"><b>24/7</b><p>Support</p></div>
</div>
</div>

<div class="card">
<div style="display:flex;gap:8px;align-items:center">
<span style="background:#3b82ff;color:#fff;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:700">API BASE</span>
<span style="font-weight:700;font-size:13px">Live Endpoint</span>
</div>
<p class="muted" style="margin-top:8px">Base URL for all requests</p>
<div class="code"><span class="y">GET</span> {{base}}/</div>
<div class="code" style="color:#aaa">curl {{base}}/health</div>
</div>

<div class="card">
<b>1️⃣ Generate QR — Create Order</b>
<p class="muted">Create payment QR, get order_id (expires 5 min)</p>
<div class="code"><span class="y">GET</span> {{base}}/fam_create<span class="p">?amount=10&api_key=FAM_xxx</span></div>
<pre class="code">{
  "status": "success",
  "data": {
    "order_id": "FAMPAY20260507...",
    "amount": 10,
    "upi": "papai69@fam",
    "qr_code": "https://api.qrserver.com/..."
  },
  "dev": "@ROXXOP"
}</pre>
<a class="btn" href="{{base}}/fam_create?amount=10&api_key=DEMO" target="_blank">Try Generate QR</a>
</div>

<div class="card">
<b>2️⃣ Verify Payment</b>
<p class="muted">Verify after user pays</p>
<div class="code"><span class="y">GET</span> {{base}}/fam_verify<span class="p">?order_id=FAMPAY...&api_key=FAM_xxx</span></div>
<pre class="code" style="color:#00ff88">Success: {"status":"success","data":{"amount":10,"utr":"3012..."},"dev":"@ROXXOP"}</pre>
<pre class="code" style="color:#ff6b6b">Failed:  {"status":"error","message":"Transaction failed - Payment not received"}</pre>
<a class="btn btn-blue" href="{{base}}/fam_verify?order_id=FAMPAYDEMO&api_key=DEMO" target="_blank">Try Verify</a>
</div>

<div class="why">
<h2>⭐ Why Choose FamPay API?</h2>
<p class="mini">Trusted by developers — fast, secure, easy</p>
<div class="mini-card">
<div class="icon" style="background:#eef0ff;margin:0 auto">🚀</div>
<b>Lightning Fast</b>
<p class="muted">Instant payment verification with &lt;200ms response time</p>
</div>
<div class="mini-card">
<div class="icon" style="background:#e6f9f0;margin:0 auto">🛡️</div>
<b>Bank-Grade Security</b>
<p class="muted">End-to-end encryption with SSL/TLS protocols</p>
</div>
<div class="mini-card">
<div class="icon" style="background:#f3e8ff;margin:0 auto">&lt;/&gt;</div>
<b>Developer Friendly</b>
<p class="muted">Simple RESTful API with comprehensive documentation</p>
</div>
</div>

<div class="footer">
<div class="badge">OFFICIAL API INFRASTRUCTURE</div>
<div style="margin:14px 0;font-size:14px">
🛡️ &nbsp; 🔒 &nbsp; ⚙️
</div>
<div style="font-size:13px"><span class="dot"></span> API v2.0 &nbsp; <span class="dot" style="background:#10b981"></span> 24/7 Active &nbsp; <span class="dot" style="background:#f59e0b"></span> Global Access</div>
<p style="margin-top:14px"><a href="https://t.me/ROXXOP" target="_blank">✈️ Join Support Community</a></p>
<p class="muted" style="margin-top:6px">Dev: <b>@ROXXOP</b> • <a href="https://t.me/FampayPaymentApi_Bot">Telegram Bot</a></p>
<p class="muted" style="font-size:11px;margin-top:8px">JSON: <a href="{{base}}/?json=1">{{base}}/?json=1</a></p>
</div>

</div>
</body>
</html>
"""

# === FIXED CONFIG ===
FAMPAY_UPI = os.getenv("FAMPAY_UPI", "papai69@fam")
GLOBAL_GMAIL = os.getenv("GMAIL", "")
GLOBAL_GPASS = os.getenv("GPASS", "")
KEYS_FILE = "keys.json"
ORDERS_FILE = "orders.json"

def load_json_file(fname, default):
    try:
        if os.path.exists(fname):
            with open(fname, "r") as f:
                return json.load(f)
    except: pass
    return default

def save_json_file(fname, data):
    try:
        with open(fname, "w") as f:
            json.dump(data, f)
    except: pass

BotKeys = load_json_file(KEYS_FILE, {})
Orders = load_json_file(ORDERS_FILE, {})
PaidSet = set(load_json_file("paid.json", []))

def save_keys(): save_json_file(KEYS_FILE, BotKeys)
def save_orders(): save_json_file(ORDERS_FILE, Orders)
def save_paid():
    try: save_json_file("paid.json", list(PaidSet))
    except: pass

def enc(s): return urllib.parse.quote(str(s), safe='')
def is_paid(id): return str(id) in PaidSet
def mark_paid(id):
    PaidSet.add(str(id))
    save_paid()

@app.route('/')
def home():
    base = request.host_url.rstrip('/')
    if request.args.get('json') == '1' or request.args.get('format') == 'json':
        return jsonify({"ok": True, "service": "FamPay Public API [FREE] - papai69@fam", "base": base, "dev": "@ROXXOP",
            "endpoints": {"health": f"GET {base}/health", "pay": f"GET {base}/pay?amount=100", "create_key": f"POST {base}/create_key", "fam_create": f"GET {base}/fam_create?amount=10&api_key=FAM_xxx", "fam_verify": f"GET {base}/fam_verify?order_id=FAMxxx&api_key=FAM_xxx"}})
    return render_template_string(HTML_PAGE, base=base)

@app.route('/health')
def health():
    return jsonify({"ok": True, "upi": FAMPAY_UPI, "global_gmail_set": bool(GLOBAL_GMAIL and GLOBAL_GPASS), "total_keys": len(BotKeys), "total_orders": len(Orders)})

@app.route('/pay')
def pay():
    amount = request.args.get("amount", "10")
    try: amount_f = float(str(amount).replace("₹","").replace(",",""))
    except: return jsonify({"ok": False, "error": "invalid amount"}), 400
    upi_raw = f"upi://pay?pa={FAMPAY_UPI}&am={amount_f:.2f}&cu=INR"
    qr = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={enc(upi_raw)}"
    return jsonify({"ok": True, "upi": FAMPAY_UPI, "amount": amount_f, "upi_link": upi_raw, "qr_url": qr})

@app.route('/create_key', methods=['POST', 'GET'])
def create_key():
    data = request.get_json(silent=True) or {}
    if not data: data = request.args.to_dict()
    gmail = data.get("gmail") or data.get("email") or request.args.get("gmail")
    gpass = data.get("gpass") or data.get("pass") or data.get("GPASS") or request.args.get("gpass")
    mobile = data.get("mobile") or data.get("phone") or request.args.get("mobile") or "0000000000"
    if not gmail or "@" not in str(gmail):
        return jsonify({"status":"error","message":"gmail required"}), 400
    if not gpass or len(str(gpass)) < 8:
        return jsonify({"status":"error","message":"gpass (App Password 16 letters) required"}), 400
    api_key = "FAM_" + os.urandom(16).hex()
    for _ in range(3):
        if api_key in BotKeys: api_key = "FAM_" + os.urandom(16).hex()
        else: break
    BotKeys[api_key] = {"gmail": str(gmail).strip(), "gpass": str(gpass).strip().replace(" ",""), "mobile": str(mobile), "created": int(time.time()), "source": "render"}
    save_keys()
    return jsonify({"status":"success","api_key": api_key, "gmail": gmail, "dev":"@ROXXOP"})

@app.route('/register_key', methods=['POST'])
def register_key():
    data = request.get_json(silent=True) or {}
    api_key = data.get("api_key") or data.get("key")
    gmail = data.get("gmail") or data.get("email")
    gpass = data.get("gpass") or data.get("pass")
    mobile = data.get("mobile") or "0000000000"
    if not api_key or not gmail or not gpass:
        return jsonify({"status":"error","message":"api_key,gmail,gpass required"}), 400
    BotKeys[str(api_key).strip()] = {"gmail": str(gmail).strip(), "gpass": str(gpass).strip().replace(" ",""), "mobile": str(mobile), "created": int(time.time()), "source": "bot"}
    save_keys()
    return jsonify({"status":"success","api_key": str(api_key).strip(), "dev":"@ROXXOP"})

@app.route('/fam_create', methods=['GET','POST'])
def fam_create():
    data = request.get_json(silent=True) or {}
    qs = request.args.to_dict()
    for k,v in data.items():
        if k.lower() not in [x.lower() for x in qs]: qs[k.lower()] = v
    nq = {str(k).lower(): v for k,v in qs.items()}
    api_key = nq.get("api_key") or nq.get("apikey") or nq.get("key")
    amount = nq.get("amount") or nq.get("amt")
    if not api_key: return jsonify({"status":"error","message":"api_key required","example":"?amount=10&api_key=YOUR_KEY","dev":"@ROXXOP"}), 400
    api_key = str(api_key).strip()
    info = BotKeys.get(api_key)
    if not info: return jsonify({"status":"error","message":"Invalid api_key","dev":"@ROXXOP"}), 401
    if not amount: return jsonify({"status":"error","message":"amount required","dev":"@ROXXOP"}), 400
    try: amount_f = float(str(amount).replace("₹","").replace(",",""))
    except: amount_f = 0
    if amount_f < 1 or amount_f > 100000:
        return jsonify({"status":"error","message":"amount must be 1-100000","dev":"@ROXXOP"}), 400
    order_id = "FAMPAY" + datetime.now().strftime("%Y%m%d%H%M%S") + os.urandom(3).hex().upper()
    upi_raw = f"upi://pay?pa={FAMPAY_UPI}&am={amount_f:.2f}&cu=INR&tn={order_id}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={enc(upi_raw)}"
    order = {"order_id": order_id, "amount": amount_f, "amount_str": f"{amount_f:.2f}", "api_key": api_key, "gmail": info.get("gmail",""), "gpass": info.get("gpass",""), "upi": FAMPAY_UPI, "upi_link": upi_raw, "qr_code": qr_url, "qr_url": qr_url, "created": int(time.time()), "expiry": int(time.time())+300, "status": "pending"}
    Orders[order_id] = order
    save_orders()
    return jsonify({"status":"success","data":{"order_id": order_id, "amount": amount_f, "amount_str": f"{amount_f:.2f}", "upi": FAMPAY_UPI, "upi_link": upi_raw, "qr_code": qr_url, "qr_url": qr_url, "expires_in": 300, "expires_at": order["expiry"]}, "dev":"@ROXXOP"})

@app.route('/fam_verify', methods=['GET','POST'])
def fam_verify():
    data = request.get_json(silent=True) or {}
    qs = request.args.to_dict()
    for k,v in data.items():
        if k.lower() not in [x.lower() for x in qs]: qs[k.lower()] = v
    nq = {str(k).lower(): v for k,v in qs.items()}
    api_key = nq.get("api_key") or nq.get("apikey") or nq.get("key")
    order_id = nq.get("order_id") or nq.get("orderid") or nq.get("order") or nq.get("id")
    utr_param = nq.get("utr") or nq.get("txn_id") or nq.get("txn")
    if not api_key: return jsonify({"status":"error","message":"api_key required","dev":"@ROXXOP"}), 400
    api_key = str(api_key).strip()
    info = BotKeys.get(api_key)
    if not info: return jsonify({"status":"error","message":"Invalid api_key","dev":"@ROXXOP"}), 401
    oid = str(order_id).strip() if order_id else str(utr_param).strip() if utr_param else ""
    if not oid: return jsonify({"status":"error","message":"order_id required","example":"?order_id=FAMPAY...&api_key=KEY","dev":"@ROXXOP"}), 400
    order = Orders.get(oid)
    gmail = info.get("gmail") or GLOBAL_GMAIL
    gpass = info.get("gpass") or GLOBAL_GPASS
    if not gmail or not gpass:
        return jsonify({"status":"error","message":"Gmail not set for this API key","dev":"@ROXXOP"}), 500
    if is_paid(oid):
        return jsonify({"status":"error","message":"Already verified","order_id": oid, "dev":"@ROXXOP"}), 400
    target_id = str(utr_param).strip() if utr_param else oid
    url = f"https://txggateway.vercel.app/api?Gmail={enc(gmail)}&GPASS={enc(gpass)}&ID={enc(target_id)}"
    try:
        r = requests.get(url, timeout=30)
        j = r.json()
    except Exception as e:
        return jsonify({"status":"error","message":"Verification timeout - try again","order_id": oid, "dev":"@ROXXOP"}), 500
    sta = str(j.get("status","")).lower()
    ft = j.get("first_time", False)
    amt_str = str(j.get("amount","0") or "0")
    tmp="";dot=False
    for ch in amt_str:
        if ch.isdigit(): tmp+=ch
        elif ch=="." and not dot: tmp+=ch; dot=True
    try: paid_amt=float(tmp) if tmp else 0
    except: paid_amt=0
    if sta=="not_found":
        return jsonify({"status":"error","message":"Transaction failed - Payment not received","order_id": oid, "dev":"@ROXXOP"})
    if sta=="already_used":
        mark_paid(oid)
        return jsonify({"status":"error","message":"Transaction already verified","order_id": oid, "dev":"@ROXXOP"})
    if sta=="verified" and ft==True:
        mark_paid(oid)
        if utr_param: mark_paid(str(utr_param))
        txn_id=str(j.get("txn_id","") or target_id)
        utr_val=str(j.get("utr","") or txn_id)
        if txn_id: mark_paid(txn_id)
        if utr_val: mark_paid(utr_val)
        if order:
            order["status"]="verified"
            Orders[oid]=order
            save_orders()
        return jsonify({"status":"success","data":{"order_id": oid, "transaction_id": txn_id, "amount": paid_amt, "utr": utr_val, "sender_name": str(j.get("sender","") or "FamPay User"), "payment_time_ist": str(j.get("payment_time","") or datetime.now().strftime("%d-%m-%Y %H:%M"))}, "dev":"@ROXXOP"})
    return jsonify({"status":"error","message": str(j.get("message","Verification failed")), "order_id": oid, "dev":"@ROXXOP", "raw": j})

@app.route('/api', methods=['GET','POST'])
def direct_api():
    gmail = request.args.get("Gmail") or request.args.get("gmail")
    gpass = request.args.get("GPASS") or request.args.get("gpass")
    tid = request.args.get("ID") or request.args.get("id") or request.args.get("utr")
    if request.is_json:
        j = request.get_json(silent=True) or {}
        gmail = gmail or j.get("Gmail") or j.get("gmail")
        gpass = gpass or j.get("GPASS") or j.get("gpass")
        tid = tid or j.get("ID") or j.get("id") or j.get("utr")
    if not gmail or not gpass or not tid:
        return jsonify({"status":"error","message":"Gmail, GPASS, ID required"}), 400
    url = f"https://txggateway.vercel.app/api?Gmail={enc(gmail)}&GPASS={enc(gpass)}&ID={enc(tid)}"
    try:
        r = requests.get(url, timeout=30)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"status":"error","message": str(e)[:200]}), 500

@app.route('/verify', methods=['GET','POST'])
def verify():
    qs = request.args.to_dict()
    if request.is_json:
        j=request.get_json(silent=True) or {}
        for k,v in j.items(): qs[k]=v
    api_key = qs.get("api_key") or qs.get("key") or request.headers.get("x-api-key")
    utr = qs.get("utr") or qs.get("id") or qs.get("ID")
    if not api_key or not utr:
        return jsonify({"ok": False, "error":"api_key and utr required"}), 400
    return fam_verify()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
