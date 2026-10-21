import os, json, time, secrets, re, math, ssl, imaplib, email
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

def load_json(p):
    try:
        with open(p,"r",encoding="utf-8") as f:
            v=json.load(f)
        return v if isinstance(v,dict) else {}
    except:
        return {}

def save_json(p,v):
    t=p+".tmp"
    with open(t,"w",encoding="utf-8") as f:
        json.dump(v,f,indent=2,ensure_ascii=False)
    os.replace(t,p)

BotKeys=load_json(KEYS_FILE)
Orders=load_json(ORDERS_FILE)
PaidRecords=load_json(PAID_FILE)

HTML = '''<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>FamPay API</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,sans-serif;background:linear-gradient(180deg,#7C6CF6,#A78BFA);min-height:100vh;padding:16px;color:#111827}
.container{max-width:680px;margin:0 auto}
.card{background:#fff;border-radius:20px;padding:22px;margin-bottom:16px;box-shadow:0 12px 32px rgba(0,0,0,.14)}
.center{text-align:center}
.logo{width:58px;height:58px;background:#7C6CF6;border-radius:16px;display:flex;align-items:center;justify-content:center;margin:0 auto 12px}
.btn{display:inline-flex;background:#111827;color:#fff;padding:12px 24px;border-radius:999px;text-decoration:none;font-weight:700;margin-top:12px}
.endpoint{background:#F5F7FF;border:1px solid #DDE3FF;border-radius:12px;padding:10px;overflow:auto;margin:12px 0;font-family:monospace;font-size:11px;color:#4338CA}
.code{background:#0F172A;color:#E2E8F0;padding:14px;border-radius:12px;margin-top:10px;font-family:monospace;font-size:11px;white-space:pre-wrap}
</style></head><body><div class="container">
<div class="card center">
<div class="logo">⚡</div>
<div style="font-size:10px;font-weight:800;color:#6D5DF6">FamPay DevPortal - AUTOMATED UPI SOLUTIONS</div>
<h1>FamPay <span style="color:#7C6CF6">DevPortal</span></h1>
<a href="https://t.me/FampayPaymentApi_Bot" target="_blank" class="btn">● GET API KEY</a>
<p style="color:#6B7280;font-size:13px;margin-top:12px">Get your API key from Telegram Bot</p>
</div>
<div class="card center">
<h2>API <span style="color:#7C6CF6">Documentation</span></h2>
<p style="color:#6B7280;font-size:13px">Lightning-fast payment verification</p>
<div style="display:flex;justify-content:space-around;margin-top:16px;border-top:1px solid #eee;padding-top:12px;font-size:12px">
<div>✅ 99.9% Uptime</div><div>⚡ &lt;200ms Response</div><div>🔒 SSL Encrypted</div>
</div></div>
<div class="card">
<h3>1. Generate QR Code</h3>
<p style="color:#6B7280;font-size:13px;margin:8px 0">Generate dynamic UPI QR code</p>
<div class="endpoint">GET https://fampay-api-7msf.onrender.com/fam_create?amount=AMOUNT&api_key=YOUR_API_KEY</div>
<div class="code">{
  "status": "success",
  "data": {
    "order_id": "FAMPAY_A1B2C3D4E5F6",
    "amount": 100,
    "upi_link": "upi://pay?pa=...",
    "qr_code": "https://api.qrserver.com/...",
    "expires_in": 300
  }
}</div>
</div>
<div class="card">
<h3>2. Verify Payment Status</h3>
<p style="color:#6B7280;font-size:13px;margin:8px 0">Verify payment using Order ID</p>
<div class="endpoint">GET https://fampay-api-7msf.onrender.com/fam_verify?order_id=ORDER_ID&api_key=YOUR_API_KEY</div>
<div class="code">{
  "status": "success",
  "data": {
    "order_id": "FAMPAY2028...",
    "transaction_id": "UTR12345678",
    "amount": 100
  }
}</div>
</div>
<div class="card center">
<h3>⭐ Why Choose FamPay API?</h3>
<p>🚀 Lightning Fast - &lt;200ms response</p>
<p>🛡️ Bank-Grade Security - SSL/TLS</p>
<p>💻 Developer Friendly - Simple REST API</p>
<div style="margin-top:12px"><a href="https://t.me/FampayPaymentApi_Bot" style="background:#229ED9;color:#fff;padding:8px 16px;border-radius:20px;text-decoration:none;font-size:12px">💬 Join Support Community</a></div>
</div>
</div></body></html>'''

def error(m,s=400):
    return jsonify({"status":"error","message":m}),s

def amount_value(v):
    try:
        a=float(str(v).replace("₹","").replace(",","").strip())
        if not math.isfinite(a) or a<=0 or a>100000:
            return None
        return round(a,2)
    except:
        return None

def get_api_key():
    k=request.args.get("api_key") or request.headers.get("X-API-Key")
    if not k and request.is_json:
        b=request.get_json(silent=True) or {}
        k=b.get("api_key")
    return k

def decode_mime(v):
    try:
        return str(make_header(decode_header(v or "")))
    except:
        return str(v or "")

def extract_text(msg):
    parts=[]
    mparts=msg.walk() if msg.is_multipart() else [msg]
    for part in mparts:
        if part.get_content_maintype()=="multipart":
            continue
        if part.get_content_type() not in ("text/plain","text/html"):
            continue
        if part.get("Content-Disposition","").lower().startswith("attachment"):
            continue
        try:
            p=part.get_payload(decode=True)
            if p:
                parts.append(p.decode(part.get_content_charset() or "utf-8",errors="replace"))
            elif isinstance(part.get_payload(),str):
                parts.append(part.get_payload())
        except:
            pass
    t=" ".join(parts)
    t=re.sub(r"<[^>]+>"," ",t)
    return re.sub(r"\s+"," ",t).strip()

def find_transaction_id(text):
    pats=[r"\bUTR(?:\s*(?:No|Number|ID|Ref(?:erence)?))?\s*[:#\-]?\s*([A-Z0-9]{8,30})\b"]
    for pat in pats:
        m=re.search(pat,text,re.I)
        if m:
            return m.group(1)
    return None

def find_amount(text):
    pats=[r"(?:amount|received|credited|paid|payment of|INR|Rs\.?|₹)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)"]
    for pat in pats:
        m=re.search(pat,text,re.I)
        if m:
            v=amount_value(m.group(1))
            if v is not None:
                return v
    return None

def check_gmail_payment(record,order):
    gmail=str(record.get("gmail","")).strip()
    gpass=str(record.get("gpass","")).replace(" ","").strip()
    try:
        ctx=ssl.create_default_context()
        with imaplib.IMAP4_SSL(IMAP_HOST,993,ssl_context=ctx) as mail:
            mail.login(gmail,gpass)
            st,_=mail.select("INBOX",readonly=True)
            if st!="OK":
                return None,"Could not open Gmail inbox."
            st,data=mail.search(None,"ALL")
            if st!="OK" or not data or not data[0]:
                return None,"No inbox messages found."
            for mid in reversed(data[0].split()[-100:]):
                st,fetched=mail.fetch(mid,"(RFC822)")
                if st!="OK":
                    continue
                raw=next((i[1] for i in fetched if isinstance(i,tuple) and len(i)>1),None)
                if not raw:
                    continue
                msg=email.message_from_bytes(raw)
                subj=decode_mime(msg.get("Subject",""))
                body=subj+" "+extract_text(msg)
                if order["order_id"].lower() not in body.lower():
                    continue
                det=find_amount(body)
                exp=amount_value(order.get("amount"))
                if det is not None and exp is not None and abs(det-exp)>0.009:
                    continue
                tid=find_transaction_id(body)
                if not tid:
                    continue
                return {"order_id":order["order_id"],"transaction_id":tid,"utr":tid,"amount":det if det is not None else exp,"payment_time":msg.get("Date",""),"email_subject":subj,"verified_at":datetime.now(timezone.utc).isoformat()},None
        return None,"No matching payment email found yet."
    except imaplib.IMAP4.error:
        return None,"Gmail login failed."
    except Exception:
        return None,"Email verification failed."

@app.get("/")
def index():
    return render_template_string(HTML)

@app.get("/health")
def health():
    return jsonify({"ok":True,"total_keys":len(BotKeys),"total_orders":len(Orders)})

@app.route("/create_key",methods=["POST"])
def create_key():
    body=request.get_json(silent=True)
    if not isinstance(body,dict):
        return error("Send JSON body")
    gmail=str(body.get("gmail","")).strip().lower()
    gpass=str(body.get("gpass","")).replace(" ","").strip()
    upi=str(body.get("upi","")).strip()
    api_key="FAM_"+secrets.token_urlsafe(32)
    with LOCK:
        BotKeys[api_key]={"gmail":gmail,"gpass":gpass,"upi":upi,"created_at":datetime.now(timezone.utc).isoformat()}
        save_json(KEYS_FILE,BotKeys)
    return jsonify({"status":"success","api_key":api_key,"upi":upi}),201

@app.route("/fam_create",methods=["GET","POST"])
def fam_create():
    api_key=get_api_key()
    if not api_key or api_key not in BotKeys:
        return error("Invalid API key",401)
    raw=request.args.get("amount") if request.method=="GET" else (request.get_json(silent=True) or {}).get("amount")
    amount=amount_value(raw)
    if amount is None:
        return error("Invalid amount")
    merchant_upi=str(BotKeys[api_key].get("upi","")).strip()
    order_id="FAMPAY_"+secrets.token_hex(12).upper()
    exp=int(time.time())+ORDER_EXPIRY
    upi_link="upi://pay?pa="+quote(merchant_upi,safe="")+"&pn=Merchant&am="+format(amount,".2f")+"&cu=INR&tn="+quote(order_id,safe="")
    qr="https://api.qrserver.com/v1/create-qr-code/?size=250x250&data="+quote(upi_link,safe="")
    order={"order_id":order_id,"api_key":api_key,"amount":amount,"upi":merchant_upi,"upi_link":upi_link,"qr_code":qr,"expires_at":exp,"status":"pending"}
    with LOCK:
        Orders[order_id]=order
        save_json(ORDERS_FILE,Orders)
    return jsonify({"status":"success","data":{"order_id":order_id,"amount":amount,"upi":merchant_upi,"upi_link":upi_link,"qr_code":qr,"expires_in":ORDER_EXPIRY,"expires_at":exp}}),201

@app.route("/fam_verify",methods=["GET","POST"])
def fam_verify():
    api_key=get_api_key()
    if not api_key or api_key not in BotKeys:
        return error("Invalid API key",401)
    oid=str((request.args.get("order_id") if request.method=="GET" else (request.get_json(silent=True) or {}).get("order_id",""))).strip()
    if not oid:
        return error("order_id required")
    with LOCK:
        order=Orders.get(oid)
        paid=PaidRecords.get(oid)
    if paid:
        return jsonify({"status":"success","data":paid})
    if int(time.time())>int(order.get("expires_at",0)):
        return jsonify({"status":"pending","message":"Order expired"})
    res,msg=check_gmail_payment(BotKeys[api_key],order)
    if not res:
        return jsonify({"status":"pending","message":msg,"data":{"order_id":oid}})
    with LOCK:
        PaidRecords[oid]=res
        save_json(PAID_FILE,PaidRecords)
    return jsonify({"status":"success","data":res})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
