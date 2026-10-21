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
<title>FamPay API - @ROXXOP</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:Inter,system-ui,sans-serif}
body{background:linear-gradient(180deg,#7b61ff 0%,#6a5cff 100%);min-height:100vh;padding:0;overflow-x:hidden}
.top{color:#fff;text-align:center;padding:14px;font-size:12px;letter-spacing:2px;animation:slideDown .8s ease}
.header{text-align:center;padding:10px}
@keyframes slideDown{from{transform:translateY(-20px);opacity:0}to{transform:translateY(0);opacity:1}}
@keyframes gradientMove{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
@keyframes typing{from{width:0}to{width:100%}}
@keyframes blink{50%{border-color:transparent}}
@keyframes fadeUp{from{transform:translateY(20px);opacity:0}to{transform:translateY(0);opacity:1}}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.05)}}
@keyframes marquee{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
.hero{max-width:900px;margin:0 auto;padding:10px 16px}
.card{background:#fff;border-radius:22px;padding:18px;box-shadow:0 10px 30px rgba(0,0,0,.18);margin:12px 0;animation:fadeUp .6s ease forwards;opacity:0}
.card:nth-child(1){animation-delay:.1s}.card:nth-child(2){animation-delay:.2s}.card:nth-child(3){animation-delay:.3s}.card:nth-child(4){animation-delay:.4s}
.h1{font-size:24px;font-weight:900;background:linear-gradient(90deg,#6a5cff,#00d9ff,#6a5cff);background-size:200% 200%;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:gradientMove 3s ease infinite, float 3s ease-in-out infinite}
.typewriter{overflow:hidden;white-space:nowrap;border-right:2px solid #6a5cff;width:0;animation:typing 2.5s steps(40,end) forwards, blink .7s infinite;animation-delay:1s,1s;margin:8px auto;max-width:100%;font-size:13px;color:#6b7280}
.badge{display:inline-block;background:#eef0ff;color:#6a5cff;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:700;animation:pulse 2s infinite}
.muted{color:#6b7280;font-size:13px;line-height:1.5}
.marquee{overflow:hidden;white-space:nowrap;background:#111;color:#fff;border-radius:10px;padding:8px 0;margin:10px 0}
.marquee span{display:inline-block;padding-right:40px;animation:marquee 12s linear infinite}
.code{background:#0f0f12;color:#00ff88;border-radius:12px;padding:12px;font-family:monospace;font-size:12px;overflow:auto;word-break:break-all;border:1px solid #222;margin-top:10px}
.btn{width:100%;background:#111;border-radius:12px;color:#fff;padding:12px;text-align:center;font-weight:700;margin-top:10px;display:block;text-decoration:none;transition:.3s}
.btn:hover{transform:scale(1.02);background:#222}
.why{background:#fff;border-radius:22px;padding:18px;margin:14px 0}
.footer{background:#fff;border-radius:22px;padding:18px;text-align:center;margin:14px 0;animation:fadeUp .8s ease}
</style>
</head>
<body>
<div class="top">✦ FamPay API | Payment Documentation — fampay-api-7msf.onrender.com</div>
<div class="hero">
<div class="card" style="text-align:center">
<span class="badge">✦ Official API Infrastructure</span>
<div class="h1">FamPay Payment API</div>
<div class="typewriter">Enterprise-grade UPI gateway for papai69@fam — Sub 200ms</div>
<p class="muted">API v2.0 • 24/7 Active • Dev: <b>@ROXXOP</b></p>
<div class="marquee"><span>⚡ Instant QR — 🛡️ Secure — 🚀 Lightning Fast — 🔒 Bank Grade — ⚡ Instant QR — 🛡️ Secure — 🚀 Lightning Fast — 🔒 Bank Grade —</span></div>
</div>
<div class="card">
<b>1️⃣ Generate QR — Create Order</b>
<p class="muted">Create QR, get order_id (expires 5 min)</p>
<div class="code">GET {{base}}/fam_create?amount=10&api_key=FAM_xxx</div>
<a class="btn" href="{{base}}/fam_create?amount=10&api_key=DEMO" target="_blank">Try Generate QR →</a>
</div>
<div class="card">
<b>2️⃣ Verify Payment</b>
<p class="muted">Verify after user pays</p>
<div class="code">GET {{base}}/fam_verify?order_id=FAMPAY...&api_key=FAM_xxx</div>
<a class="btn" style="background:#3b82ff" href="{{base}}/fam_verify?order_id=DEMO&api_key=DEMO" target="_blank">Try Verify →</a>
</div>
<div class="why">
<h2 style="text-align:center">⭐ Why Choose FamPay API?</h2>
<p class="muted" style="text-align:center;margin-bottom:12px">Trusted by developers — fast, secure, easy</p>
<div style="background:#f8f7ff;border-radius:16px;padding:16px;text-align:center;margin:8px 0">🚀<br><b>Lightning Fast</b><br><span class="muted">&lt;200ms response</span></div>
<div style="background:#f0fdf4;border-radius:16px;padding:16px;text-align:center;margin:8px 0">🛡️<br><b>Bank-Grade Security</b><br><span class="muted">SSL/TLS encryption</span></div>
<div style="background:#faf5ff;border-radius:16px;padding:16px;text-align:center;margin:8px 0">&lt;/&gt;<br><b>Developer Friendly</b><br><span class="muted">Simple REST API</span></div>
</div>
<div class="footer">
<b>OFFICIAL API INFRASTRUCTURE</b><br><br>
<a href="https://t.me/ROXXOP" target="_blank">✈️ Join Support Community</a><br>
<span class="muted" style="font-size:11px">JSON: <a href="{{base}}/?json=1">{{base}}/?json=1</a></span>
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
