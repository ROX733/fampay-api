from flask import Flask, request, jsonify
import requests, os, json, urllib.parse, time, random
from datetime import datetime

app = Flask(__name__)

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
    return jsonify({
        "ok": True,
        "service": "FamPay Public API [FREE] - papai69@fam",
        "base": base,
        "endpoints": {
            "health": f"GET {base}/health",
            "pay": f"GET {base}/pay?amount=100",
            "create_key": f"POST {base}/create_key  {{\"gmail\",\"gpass\",\"mobile\"}}",
            "register_key": f"POST {base}/register_key  {{\"api_key\",\"gmail\",\"gpass\"}}  (Bot sync)",
            "fam_create": f"GET {base}/fam_create?amount=10&api_key=FAM_xxx",
            "fam_verify": f"GET {base}/fam_verify?order_id=FAMxxx&api_key=FAM_xxx",
            "verify": f"GET {base}/verify?utr=UTR&api_key=FAM_xxx",
            "direct_verify": f"GET {base}/api?Gmail=email&GPASS=pass&ID=utr"
        }
    })

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
