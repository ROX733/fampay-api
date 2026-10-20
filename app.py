from flask import Flask, request, jsonify
import requests, os, json, urllib.parse, time, random, string
from datetime import datetime

app = Flask(__name__)

# CONFIG - Render ENV me set karo
FAMPAY_UPI = os.getenv("FAMPAY_UPI", "papai69@fam")
GMAIL = os.getenv("GMAIL", "") # fallback admin gmail
GPASS = os.getenv("GPASS", "")
ADMIN_KEY = os.getenv("API_KEY", "papifam123") # admin ke liye

KEYS_FILE = "keys.json"
ORDERS_FILE = "orders.json"
PAID_FILE = "paid.json"

def load_json(f):
    try:
        if os.path.exists(f):
            with open(f, "r") as fh: return json.load(fh)
    except: pass
    return {}

def save_json(f, data):
    try:
        with open(f, "w") as fh: json.dump(data, fh)
    except: pass

def enc(s): return urllib.parse.quote(str(s), safe='')

def gen_key():
    return "FAM_" + ''.join(random.choices(string.hexdigits, k=32)).lower()

def gen_order():
    return "FAM" + str(int(time.time())) + ''.join(random.choices(string.digits, k=4))

@app.route('/')
def home():
    base = request.host_url.rstrip('/')
    return jsonify({
        "ok": True,
        "service": "FamPay Public API [FREE] - papai69@fam",
        "base": base,
        "endpoints": {
            "create_key": f"POST {base}/create_key  {{gmail,gpass,mobile}}",
            "fam_create": f"GET {base}/fam_create?amount=10&api_key=FAM_xxx",
            "fam_verify": f"GET {base}/fam_verify?order_id=FAMxxx&api_key=FAM_xxx",
            "direct_verify": f"GET {base}/api?Gmail=email&GPASS=pass&ID=utr",
            "verify": f"GET {base}/verify?utr=UTR&api_key=FAM_xxx",
            "pay": f"GET {base}/pay?amount=100",
            "health": f"GET {base}/health"
        }
    })

@app.route('/health')
def health():
    keys = load_json(KEYS_FILE)
    return jsonify({"ok": True, "upi": FAMPAY_UPI, "total_keys": len(keys), "admin_gmail_set": bool(GMAIL and GPASS)})

# 1. CREATE API KEY - Public (sab log use kar sakte)
@app.route('/create_key', methods=['POST', 'GET'])
def create_key():
    if request.method == 'GET':
        gmail = request.args.get("gmail") or request.args.get("Gmail")
        gpass = request.args.get("gpass") or request.args.get("GPASS")
        mobile = request.args.get("mobile") or request.args.get("phone") or "0000000000"
    else:
        d = request.get_json(silent=True) or request.form.to_dict()
        gmail = d.get("gmail") or d.get("Gmail")
        gpass = d.get("gpass") or d.get("GPASS") or d.get("pass")
        mobile = d.get("mobile") or d.get("phone") or "0000000000"
    
    if not gmail or "@" not in str(gmail): return jsonify({"ok": False, "error": "gmail required"}), 400
    if not gpass or len(str(gpass).replace(" ","")) < 8: return jsonify({"ok": False, "error": "gpass (16 letter app password) required"}), 400
    gpass = str(gpass).replace(" ","")
    
    # verify gmail via txg
    test_id = "TESTVERIFY123"
    try:
        url = f"https://txggateway.vercel.app/api?Gmail={enc(gmail)}&GPASS={enc(gpass)}&ID={enc(test_id)}"
        r = requests.get(url, timeout=20)
        j = r.json()
        sta = str(j.get("status","")).lower()
        if sta not in ("not_found","verified","already_used") and r.status_code != 200:
            if "auth" in str(j).lower() or "invalid" in str(j).lower():
                return jsonify({"ok": False, "error": "Gmail/App Password invalid", "raw": j}), 401
    except Exception as e:
        return jsonify({"ok": False, "error": "Gmail verify failed", "details": str(e)[:200]}), 500

    keys = load_json(KEYS_FILE)
    # check already
    for k,v in keys.items():
        if v.get("gmail") == gmail:
            return jsonify({"ok": True, "api_key": k, "message": "Already exists for this Gmail", "gmail": gmail})

    api_key = gen_key()
    for _ in range(5):
        if api_key in keys: api_key = gen_key()
        else: break
    
    keys[api_key] = {"gmail": gmail, "gpass": gpass, "mobile": str(mobile), "created": str(datetime.now())}
    save_json(KEYS_FILE, keys)
    return jsonify({"ok": True, "api_key": api_key, "gmail": gmail, "mobile": str(mobile), "message": "API Key Generated - Keep safe!"})

# 2. CREATE QR - Anuj style
@app.route('/fam_create', methods=['GET','POST'])
def fam_create():
    d = request.args.to_dict()
    if request.method == 'POST':
        jd = request.get_json(silent=True) or {}
        d.update(jd)
    amount = d.get("amount") or d.get("amt")
    api_key = d.get("api_key") or d.get("key") or request.headers.get("x-api-key")
    
    if not amount: return jsonify({"ok": False, "error": "amount required, ex: /fam_create?amount=10&api_key=FAM_xxx"}), 400
    if not api_key: return jsonify({"ok": False, "error": "api_key required"}), 401
    
    keys = load_json(KEYS_FILE)
    # allow admin key also
    if api_key != ADMIN_KEY and api_key not in keys:
        return jsonify({"ok": False, "error": "Invalid api_key"}), 401
    
    try: amt = float(str(amount).replace("₹","").replace(",",""))
    except: return jsonify({"ok": False, "error": "invalid amount"}), 400
    if amt <= 0: return jsonify({"ok": False, "error": "amount > 0"}), 400
    
    order_id = gen_order()
    upi_raw = f"upi://pay?pa={FAMPAY_UPI}&am={amt:.2f}&cu=INR&tn={order_id}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={enc(upi_raw)}"
    
    orders = load_json(ORDERS_FILE)
    orders[order_id] = {"amount": amt, "api_key": api_key, "upi": FAMPAY_UPI, "created": time.time(), "status": "pending"}
    save_json(ORDERS_FILE, orders)
    
    return jsonify({
        "ok": True,
        "order_id": order_id,
        "amount": amt,
        "upi": FAMPAY_UPI,
        "upi_link": upi_raw,
        "qr_code": qr_url,
        "expires_in": "5 minutes",
        "verify_url": f"{request.host_url.rstrip('/')}/fam_verify?order_id={order_id}&api_key={api_key}"
    })

# 3. VERIFY - Anuj style
@app.route('/fam_verify', methods=['GET','POST'])
def fam_verify():
    d = request.args.to_dict()
    if request.method == 'POST':
        jd = request.get_json(silent=True) or {}
        d.update(jd)
    order_id = d.get("order_id") or d.get("orderId") or d.get("id")
    api_key = d.get("api_key") or request.headers.get("x-api-key")
    utr = d.get("utr") or d.get("txn_id") or d.get("ID")
    
    if not api_key: return jsonify({"ok": False, "error": "api_key required"}), 401
    keys = load_json(KEYS_FILE)
    if api_key != ADMIN_KEY and api_key not in keys:
        return jsonify({"ok": False, "error": "Invalid api_key"}), 401
    if not order_id and not utr: return jsonify({"ok": False, "error": "order_id or utr required"}), 400
    
    # if utr directly given, use it
    if utr and not order_id:
        order_id = str(utr)

    orders = load_json(ORDERS_FILE)
    paid = load_json(PAID_FILE)
    
    # find order
    order = orders.get(str(order_id))
    if not order:
        # try as UTR direct
        if len(str(order_id)) >= 6:
            # treat order_id as UTR
            utr_to_check = str(order_id)
            gmail = keys[api_key]["gmail"] if api_key in keys else GMAIL
            gpass = keys[api_key]["gpass"] if api_key in keys else GPASS
        else:
            return jsonify({"ok": False, "status": "not_found", "error": "order_id not found"}), 404
    else:
        if str(order["api_key"]) != str(api_key) and api_key != ADMIN_KEY:
            return jsonify({"ok": False, "error": "order_id not belong to this api_key"}), 403
        utr_to_check = str(order_id)
        # we need UTR from user? Actually Anuj flow: user pays then verify with order_id - gateway checks by order_id/utr
        # For this public version we check via UTR = order_id if user sends utr as order_id
        gmail = keys[api_key]["gmail"] if api_key in keys else GMAIL
        gpass = keys[api_key]["gpass"] if api_key in keys else GPASS
        amt_expected = order["amount"]
        # if utr provided separately, use that
        if utr and len(str(utr)) >= 6:
            utr_to_check = str(utr)

    if str(utr_to_check) in paid:
        return jsonify({"ok": False, "status": "already_used", "order_id": str(order_id), "utr": str(utr_to_check)})

    # call txg
    try:
        url = f"https://txggateway.vercel.app/api?Gmail={enc(gmail)}&GPASS={enc(gpass)}&ID={enc(utr_to_check)}"
        r = requests.get(url, timeout=45)
        j = r.json()
        sta = str(j.get("status","")).lower()
        ft = j.get("first_time", False)
        amt_str = str(j.get("amount","0") or "0")
        tmp=""; dot=False
        for ch in amt_str:
            if ch.isdigit(): tmp+=ch
            elif ch=="." and not dot: tmp+=ch; dot=True
        try: paid_amt = float(tmp) if tmp else 0
        except: paid_amt = 0

        if sta == "not_found":
            return jsonify({"ok": False, "status": "not_found", "order_id": str(order_id), "message": "Payment not found - check UTR or wait 30 sec"})
        if sta == "already_used":
            paid[str(utr_to_check)] = True
            save_json(PAID_FILE, paid)
            return jsonify({"ok": False, "status": "already_used", "order_id": str(order_id)})
        if sta == "verified" and ft == True:
            if order and paid_amt != float(order["amount"]):
                # amount mismatch still consider verified but warn
                pass
            paid[str(utr_to_check)] = True
            if order_id: paid[str(order_id)] = True
            save_json(PAID_FILE, paid)
            if order_id in orders:
                orders[order_id]["status"] = "verified"
                orders[order_id]["utr"] = str(utr_to_check)
                orders[order_id]["paid_amount"] = paid_amt
                save_json(ORDERS_FILE, orders)
            return jsonify({"ok": True, "status": "verified", "order_id": str(order_id), "utr": str(utr_to_check), "amount": paid_amt, "fampay_upi": FAMPAY_UPI})
        return jsonify({"ok": False, "status": sta, "raw": j})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:300]}), 500

# 4. DIRECT TXG style - https://your-api/api?Gmail=&GPASS=&ID=
@app.route('/api', methods=['GET','POST'])
def api_direct():
    gmail = request.args.get("Gmail") or request.args.get("gmail")
    gpass = request.args.get("GPASS") or request.args.get("gpass")
    tid = request.args.get("ID") or request.args.get("id") or request.args.get("utr")
    if request.method == 'POST':
        jd = request.get_json(silent=True) or {}
        gmail = gmail or jd.get("Gmail") or jd.get("gmail")
        gpass = gpass or jd.get("GPASS") or jd.get("gpass")
        tid = tid or jd.get("ID") or jd.get("id") or jd.get("utr")
    if not gmail or not gpass or not tid:
        return jsonify({"ok": False, "error": "Need Gmail, GPASS, ID"}), 400
    try:
        url = f"https://txggateway.vercel.app/api?Gmail={enc(gmail)}&GPASS={enc(gpass)}&ID={enc(tid)}"
        r = requests.get(url, timeout=45)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:300]}), 500

@app.route('/verify', methods=['GET','POST'])
def verify_alias():
    return fam_verify()

@app.route('/pay')
def pay():
    amt = request.args.get("amount","10")
    try: amt_f = float(str(amt).replace("₹","").replace(",",""))
    except: amt_f = 10
    upi_raw = f"upi://pay?pa={FAMPAY_UPI}&am={amt_f:.2f}&cu=INR"
    qr = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={enc(upi_raw)}"
    return jsonify({"ok": True, "upi": FAMPAY_UPI, "amount": amt_f, "upi_link": upi_raw, "qr_url": qr})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
