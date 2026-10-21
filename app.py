import os, json, time, secrets, re, math, ssl, imaplib, email
from datetime import datetime, timezone
from email.header import decode_header, make_header
from threading import RLock
from urllib.parse import quote
from flask import Flask, request, jsonify, render_template_string
app=Flask(__name__)
BASE_DIR=os.path.dirname(os.path.abspath(__file__))
KEYS_FILE=os.path.join(BASE_DIR,"keys.json")
ORDERS_FILE=os.path.join(BASE_DIR,"orders.json")
PAID_FILE=os.path.join(BASE_DIR,"paid.json")
ORDER_EXPIRY=300
IMAP_HOST="imap.gmail.com"
LOCK=RLock()
def load_json(path):
    try:
        with open(path,"r",encoding="utf-8") as f:
            v=json.load(f)
        return v if isinstance(v,dict) else {}
    except: return {}
def save_json(path,value):
    t=path+".tmp"
    open(t,"w",encoding="utf-8").write(json.dumps(value,indent=2,ensure_ascii=False))
    os.replace(t,path)
BotKeys=load_json(KEYS_FILE)
Orders=load_json(ORDERS_FILE)
PaidRecords=load_json(PAID_FILE)
HTML="""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FamPay API</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:linear-gradient(180deg,#7C6CF6 0%,#8B7CF8 35%,#A78BFA 100%);min-height:100vh;padding:16px 14px 90px;color:#111827}
.container{max-width:680px;margin:0 auto}
.card{background:#fff;border-radius:20px;padding:22px 18px;margin-bottom:16px;box-shadow:0 12px 32px rgba(37,20,97,0.14);animation:slideUp .6s ease forwards;opacity:0}
.card:nth-child(1){animation-delay:.1s}.card:nth-child(2){animation-delay:.2s}.card:nth-child(3){animation-delay:.3s}.card:nth-child(4){animation-delay:.4s}.card:nth-child(5){animation-delay:.5s}
.center{text-align:center}
@keyframes slideUp{from{transform:translateY(20px);opacity:0}to{transform:translateY(0);opacity:1}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.08)}}
@keyframes bounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
@keyframes glow{0%,100%{box-shadow:0 8px 18px rgba(124,108,246,.35)}50%{box-shadow:0 12px 28px rgba(124,108,246,.55)}}
.logo-wrap{width:58px;height:58px;background:linear-gradient(135deg,#7C6CF6,#5B4FE8);border-radius:16px;display:flex;align-items:center;justify-content:center;margin:0 auto 12px;animation:float 3s ease-in-out infinite,glow 2s ease-in-out infinite}
.badge-top{display:inline-block;background:#EDE9FF;color:#6D5DF6;font-size:10px;font-weight:800;letter-spacing:1.2px;padding:5px 12px;border-radius:20px;margin-bottom:10px;animation:pulse 2s infinite}
.h1{font-size:26px;font-weight:800;line-height:1.1}.h1 span{color:#7C6CF6}
.btn-dark{display:inline-flex;background:#111827;color:#fff;border:none;padding:12px 24px;border-radius:999px;font-weight:700;font-size:13px;margin-top:16px;cursor:pointer;align-items:center;gap:8px;text-decoration:none;transition:all .3s;animation:pulse 2.5s infinite}
.btn-dark:hover{transform:scale(1.05);background:#000}
.sub{color:#6B7280;font-size:13px;line-height:1.6;margin-top:12px}
.stats{display:flex;justify-content:space-between;margin-top:20px;border-top:1px solid #F3F4F6;padding-top:16px}
.stat{flex:1;text-align:center}.stat-icon{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 6px;font-size:16px;animation:bounce 2s infinite}
.stat:nth-child(2) .stat-icon{animation-delay:.2s}.stat:nth-child(3) .stat-icon{animation-delay:.4s}
.stat b{display:block;font-size:12px;color:#111827}
.sec-head{display:flex;align-items:center;gap:12px;margin-bottom:8px}
.sec-num{width:36px;height:36px;background:#EDE9FF;color:#7C6CF6;border-radius:10px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px;animation:pulse 2s infinite}
.sec-title{font-size:16px;font-weight:800}.sec-type{font-size:10px;font-weight:700;letter-spacing:.6px;color:#6B7280;margin-top:2px}
.sec-desc{font-size:13px;color:#4B5563;line-height:1.6;margin:8px 0 14px}
.endpoint{background:#F5F7FF;border:1px solid #DDE3FF;border-radius:12px;padding:10px 12px;display:flex;gap:10px;align-items:flex-start;overflow:auto;margin:12px 0}
.method{background:#7C6CF6;color:#fff;font-size:11px;font-weight:800;padding:4px 8px;border-radius:6px;flex-shrink:0}
.endpoint code{font-family:'JetBrains Mono',monospace;font-size:11px;color:#4338CA;word-break:break-all;line-height:1.5}
.req-title{font-size:11px;font-weight:800;letter-spacing:.8px;color:#111827;margin:18px 0 10px;display:flex;align-items:center;gap:6px}
.table{border:1px solid #F3F4F6;border-radius:12px;overflow:hidden}
.t-head{display:grid;grid-template-columns:90px 90px 1fr;background:#F9FAFB;padding:9px 12px;font-size:10px;font-weight:800;color:#6B7280;letter-spacing:.6px}
.t-row{display:grid;grid-template-columns:90px 90px 1fr;padding:12px 12px;font-size:12px;border-top:1px solid #F3F4F6;align-items:center;gap:8px}
.t-row b{font-family:'JetBrains Mono',monospace;font-size:12px}
.tag-req{background:#FEE2E2;color:#DC2626;font-size:10px;font-weight:700;padding:3px 8px;border-radius:20px;display:inline-block}
.code-wrap{position:relative;background:#0F172A;border-radius:14px;margin-top:12px;overflow:hidden;border:1px solid #1E293B}
.code-head{display:flex;justify-content:space-between;align-items:center;padding:10px 12px;background:#111C34;border-bottom:1px solid #1E293B}
.code-label{font-size:11px;font-weight:700;color:#94A3B8}
.copy{background:#7C6CF6;color:#fff;border:none;padding:6px 12px;border-radius:8px;font-size:11px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:4px;transition:.2s}
.code-wrap pre{margin:0;padding:14px;color:#E2E8F0;font-family:'JetBrains Mono',monospace;font-size:11px;line-height:1.7;overflow:auto;white-space:pre-wrap;word-break:break-word}
.pro-tip{background:#FFFBEB;border:1px solid #FDE68A;border-radius:12px;padding:11px 12px;font-size:11.5px;color:#92400E;line-height:1.5;margin-top:14px;display:flex;gap:8px;animation:bounce 3s infinite}
.features{display:grid;gap:12px;margin-top:14px}
.feat{background:#fff;border:1px solid #F3F4F6;border-radius:16px;padding:18px;text-align:center;transition:transform .3s}
.feat:hover{transform:translateY(-3px)}
.feat-icon{width:46px;height:46px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 8px;font-size:22px;animation:float 3s ease-in-out infinite}
.feat:nth-child(2) .feat-icon{animation-delay:.5s}.feat:nth-child(3) .feat-icon{animation-delay:1s}
.feat h4{font-size:13px;font-weight:800}.feat p{font-size:11px;color:#6B7280;margin-top:4px;line-height:1.5}
.footer{margin-top:20px;text-align:center}.dot{display:inline-block;width:6px;height:6px;background:#7C6CF6;border-radius:50%;margin-right:6px;animation:pulse 1.5s infinite}
.footer-links{display:flex;justify-content:center;gap:14px;margin-top:10px;font-size:11px;color:#111827;font-weight:600}
</style></head><body><div class="container">
<div class="card center" style="padding:30px 18px">
<div class="logo-wrap">⚡</div>
<div class="badge-top">FamPay DevPortal</div>
<div style="font-size:10px;font-weight:800;letter-spacing:1.2px;color:#6B7280;margin-top:-6px;margin-bottom:6px">AUTOMATED UPI SOLUTIONS</div>
<h1 class="h1">FamPay <span>DevPortal</span></h1>
<a href="https://t.me/FampayPaymentApi_Bot" target="_blank" class="btn-dark">● GET API KEY</a>
<p class="sub">Integrate FamPay automatic payment verification into your applications with lightning-fast speed.</p>
</div>
<div class="card center">
<div style="width:54px;height:54px;background:#EEF2FF;border-radius:14px;display:flex;align-items:center;justify-content:center;margin:0 auto 12px;font-size:26px;animation:float 2.5s infinite">📄</div>
<h2 style="font-size:20px;font-weight:800">API <span style="color:#7C6CF6">Documentation</span></h2>
<p class="sub">Integrate FamPay automatic payment verification into your applications with lightning-fast speed and military-grade security.</p>
<div class="stats">
<div class="stat"><div class="stat-icon" style="background:#ECFDF5">✅</div><b>99.9% Uptime</b></div>
<div class="stat"><div class="stat-icon" style="background:#FEF3C7">⚡</div><b>&lt;200ms Response</b></div>
<div class="stat"><div class="stat-icon" style="background:#DBEAFE">🔒</div><b>SSL Encrypted</b></div>
</div></div>
<div class="card">
<div class="sec-head"><div class="sec-num">1</div><div><div class="sec-title">Generate QR Code</div><div class="sec-type">POST Payment Request</div></div></div>
<div class="sec-desc">Generate a dynamic UPI QR code for receiving instant payments with automatic verification.</div>
<div class="endpoint"><span class="method">GET</span><code>/fam_create?amount=AMOUNT&api_key=YOUR_API_KEY</code></div>
<div class="req-title">📋 REQUEST PARAMETERS</div>
<div class="table"><div class="t-head"><span>PARAMETER</span><span>TYPE</span><span>DESCRIPTION</span></div>
<div class="t-row"><b>amount</b><span class="tag-req">Required</span><span>Payment Amount (1 - 100000)</span></div>
<div class="t-row"><b>api_key</b><span class="tag-req">Required</span><span>Your API key from Telegram Bot</span></div></div>
<div class="req-title" style="margin-top:16px">💻 RESPONSE FORMAT</div>
<div class="code-wrap"><div class="code-head"><span class="code-label">JSON</span><button class="copy" onclick="copyCode(this)">📋 COPY</button></div>
<pre>{
  "status": "success",
  "data": {
    "order_id": "FAMPAY_A1B2C3D4E5F6",
    "amount": 100,
    "upi": "merchant@upi",
    "upi_link": "upi://pay?pa=...",
    "qr_code": "https://api.qrserver.com/...",
    "expires_in": 300
  }
}</pre></div>
<div class="pro-tip">💡 <span><b>Pro Tip:</b> QR codes expire after 5 minutes. Save order_id for verification.</span></div>
</div>
<div class="card">
<div class="sec-head"><div class="sec-num">2</div><div><div class="sec-title">Verify Payment Status</div><div class="sec-type">Check Transaction Completion</div></div></div>
<div class="sec-desc">Verify if payment has been successfully received using the unique Order ID.</div>
<div class="endpoint"><span class="method">GET</span><code>/fam_verify?order_id=ORDER_ID&api_key=YOUR_API_KEY</code></div>
<div class="req-title">📋 REQUEST PARAMETERS</div>
<div class="table"><div class="t-head"><span>PARAMETER</span><span>TYPE</span><span>DESCRIPTION</span></div>
<div class="t-row"><b>order_id</b><span class="tag-req">Required</span><span>The unique order ID from QR generation</span></div>
<div class="t-row"><b>api_key</b><span class="tag-req">Required</span><span>Your authentication key</span></div></div>
<div class="req-title" style="margin-top:16px">💻 RESPONSE EXAMPLES</div>
<div class="code-wrap" style="border:1px solid #A7F3D0"><div class="code-head" style="background:#ECFDF5"><span class="code-label" style="color:#065F46">✅ PAYMENT SUCCESS</span><button class="copy" onclick="copyCode(this)">📋 COPY</button></div>
<pre>{
  "status": "success",
  "data": {
    "order_id": "FAMPAY2028...",
    "transaction_id": "UTR12345678",
    "amount": 100
  }
}</pre></div>
<div class="code-wrap" style="border:1px solid #FECACA;margin-top:10px"><div class="code-head" style="background:#FEF2F2"><span class="code-label" style="color:#991B1B">❌ PAYMENT FAILED / PENDING</span><button class="copy" onclick="copyCode(this)">📋 COPY</button></div>
<pre>{
  "status": "pending",
  "message": "No matching payment email found yet.",
  "data": { "order_id": "FAMPAY2028...", "amount": 100 }
}</pre></div>
<div class="pro-tip" style="background:#EFF6FF;border-color:#BFDBFE;color:#1E40AF">🔔 <span><b>Important:</b> Keep your api_key confidential. Never expose it in client-side code.</span></div>
</div>
<div class="card">
<h3 style="font-size:16px;font-weight:800;text-align:center;margin-bottom:14px">⭐ Why Choose FamPay API?</h3>
<div class="features">
<div class="feat"><div class="feat-icon" style="background:#EDE9FF">🚀</div><h4>Lightning Fast</h4><p>Instant verification with &lt;200ms response time</p></div>
<div class="feat"><div class="feat-icon" style="background:#D1FAE5">🛡️</div><h4>Bank-Grade Security</h4><p>End-to-end encryption with SSL/TLS protocols</p></div>
<div class="feat"><div class="feat-icon" style="background:#EDE9FF">💻</div><h4>Developer Friendly</h4><p>Simple REST API with comprehensive docs</p></div>
</div></div>
<div class="footer"><div style="background:#fff;border-radius:20px;padding:16px">
<div style="font-size:10px;font-weight:800;letter-spacing:1.2px;color:#6B7280"><span class="dot"></span>OFFICIAL API INFRASTRUCTURE</div>
<div class="footer-links"><span>🔷 API v2.0</span><span>● 24/7 Active</span><span>🌐 Global Access</span></div>
<div style="margin-top:12px"><a href="https://t.me/FamPayVerifyBot" style="background:#229ED9;color:#fff;padding:8px 16px;border-radius:20px;text-decoration:none;font-size:12px;font-weight:700">💬 Join Support Community</a></div>
</div></div></div>
<script>function copyCode(btn){const pre=btn.closest('.code-wrap').querySelector('pre');navigator.clipboard.writeText(pre.innerText);const old=btn.innerHTML;btn.innerHTML='✅ COPIED';btn.style.background='#10B981';setTimeout(()=>{btn.innerHTML=old;btn.style.background='#7C6CF6'},1500);}</script>
</body></html>
"""
def error(m,s=400): return jsonify({"status":"error","message":m}),s
def amount_value(v):
    try:
        a=float(str(v).replace("₹","").replace(",","").strip())
        if not math.isfinite(a) or a<=0 or a>100000: return None
        return round(a,2)
    except: return None
def get_api_key():
    k=request.args.get("api_key") or request.headers.get("X-API-Key")
    if not k and request.is_json:
        b=request.get_json(silent=True) or {}
        k=b.get("api_key")
    return k
def decode_mime(v):
    try: return str(make_header(decode_header(v or "")))
    except: return str(v or "")
def extract_text(msg):
    parts=[]
    mparts=msg.walk() if msg.is_multipart() else [msg]
    for part in mparts:
        if part.get_content_maintype()=="multipart": continue
        if part.get_content_type() not in ("text/plain","text/html"): continue
        if part.get("Content-Disposition","").lower().startswith("attachment"): continue
        try:
            p=part.get_payload(decode=True)
            if p: parts.append(p.decode(part.get_content_charset() or "utf-8",errors="replace"))
            elif isinstance(part.get_payload(),str): parts.append(part.get_payload())
        except: pass
    t=" ".join(parts)
    t=re.sub(r"<[^>]+>"," ",t)
    return re.sub(r"\s+"," ",t).strip()
def find_transaction_id(text):
    pats=[r"\bUTR(?:\s*(?:No|Number|ID|Ref(?:erence)?))?\s*[:#\-]?\s*([A-Z0-9]{8,30})\b",r"\btransaction(?:\s*(?:ID|Reference|Ref|No|Number))?\s*[:#\-]?\s*([A-Z0-9]{8,30})\b",r"\bUPI\s*(?:Ref(?:erence)?|Txn(?:\s*ID)?)\s*[:#\-]?\s*([A-Z0-9]{8,30})\b"]
    for pat in pats:
        m=re.search(pat,text,re.I)
        if m: return m.group(1)
    return None
def find_amount(text):
    pats=[r"(?:amount|received|credited|paid|payment of|INR|Rs\.?|₹)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",r"₹\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)"]
    for pat in pats:
        m=re.search(pat,text,re.I)
        if m:
            v=amount_value(m.group(1))
            if v is not None: return v
    return None
def check_gmail_payment(record,order):
    gmail=str(record.get("gmail","")).strip()
    gpass=str(record.get("gpass","")).replace(" ","").strip()
    try:
        ctx=ssl.create_default_context()
        with imaplib.IMAP4_SSL(IMAP_HOST,993,ssl_context=ctx) as mail:
            mail.login(gmail,gpass)
            st,_=mail.select("INBOX",readonly=True)
            if st!="OK": return None,"Could not open Gmail inbox."
            st,data=mail.search(None,"ALL")
            if st!="OK" or not data or not data[0]: return None,"No inbox messages found."
            for mid in reversed(data[0].split()[-100:]):
                st,fetched=mail.fetch(mid,"(RFC822)")
                if st!="OK": continue
                raw=next((i[1] for i in fetched if isinstance(i,tuple) and len(i)>1),None)
                if not raw: continue
                msg=email.message_from_bytes(raw)
                subj=decode_mime(msg.get("Subject",""))
                body=subj+" "+extract_text(msg)
                if order["order_id"].lower() not in body.lower(): continue
                det=find_amount(body)
                exp=amount_value(order.get("amount"))
                if det is not None and exp is not None and abs(det-exp)>0.009: continue
                tid=find_transaction_id(body)
                if not tid: continue
                return {"order_id":order["order_id"],"transaction_id":tid,"utr":tid,"amount":det if det is not None else exp,"payment_time":msg.get("Date",""),"email_subject":subj,"verified_at":datetime.now(timezone.utc).isoformat()},None
        return None,"No matching payment email found yet."
    except imaplib.IMAP4.error:
        return None,"Gmail login failed. Check Gmail address, Google App Password and IMAP access."
    except (OSError,TimeoutError):
        app.logger.exception("Gmail connection failed")
        return None,"Could not connect to Gmail. Try again later."
    except Exception:
        app.logger.exception("Email verification failed")
        return None,"Email verification failed unexpectedly."
@app.get("/")
def index(): return render_template_string(HTML)
@app.get("/health")
def health(): return jsonify({"ok":True,"imap_host":IMAP_HOST,"total_keys":len(BotKeys),"total_orders":len(Orders)})
@app.route("/create_key",methods=["POST"])
def create_key():
    body=request.get_json(silent=True)
    if not isinstance(body,dict): return error("Send a JSON request body.")
    gmail=str(body.get("gmail","")).strip().lower()
    gpass=str(body.get("gpass","")).replace(" ","").strip()
    mobile=str(body.get("mobile","")).strip()
    upi=str(body.get("upi","")).strip()
    if not re.fullmatch(r"[^@\s]+@gmail\.com",gmail,re.I): return error("A valid Gmail address is required.")
    if len(gpass)!=16 or not gpass.isalnum(): return error("Use the 16-character Google App Password, without spaces.")
    if mobile and not re.fullmatch(r"[0-9+\-\s]{7,20}",mobile): return error("Invalid mobile number.")
    if not re.fullmatch(r"[A-Za-z0-9.\-_]{2,256}@[A-Za-z0-9]{2,64}",upi): return error("Enter a valid UPI ID, for example name@upi.")
    api_key="FAM_"+secrets.token_urlsafe(32)
    with LOCK:
        BotKeys[api_key]={"gmail":gmail,"gpass":gpass,"mobile":mobile,"upi":upi,"created_at":datetime.now(timezone.utc).isoformat()}
        save_json(KEYS_FILE,BotKeys)
    return jsonify({"status":"success","api_key":api_key,"gmail":gmail,"upi":upi}),201
@app.route("/register_key",methods=["POST"])
def register_key(): return create_key()
@app.route("/fam_create",methods=["GET","POST"])
def fam_create():
    api_key=get_api_key()
    if not api_key or api_key not in BotKeys: return error("Invalid or missing API key.",401)
    raw=request.args.get("amount") if request.method=="GET" else (request.get_json(silent=True) or {}).get("amount")
    amount=amount_value(raw)
    if amount is None: return error("Amount must be greater than 0 and no more than 100000.")
    merchant_upi=str(BotKeys[api_key].get("upi","")).strip()
    if not merchant_upi: return error("No UPI ID registered for this API key.")
    order_id="FAMPAY_"+secrets.token_hex(12).upper()
    exp=int(time.time())+ORDER_EXPIRY
    upi_link="upi://pay?pa="+quote(merchant_upi,safe="")+"&pn=Merchant&am="+format(amount,".2f")+"&cu=INR&tn="+quote(order_id,safe="")
    qr="https://api.qrserver.com/v1/create-qr-code/?size=250x250&data="+quote(upi_link,safe="")
    order={"order_id":order_id,"api_key":api_key,"amount":amount,"upi":merchant_upi,"upi_link":upi_link,"qr_code":qr,"created_at":int(time.time()),"expires_at":exp,"status":"pending"}
    with LOCK:
        Orders[order_id]=order
        save_json(ORDERS_FILE,Orders)
    return jsonify({"status":"success","data":{"order_id":order_id,"amount":amount,"upi":merchant_upi,"upi_link":upi_link,"qr_code":qr,"expires_in":ORDER_EXPIRY,"expires_at":exp}}),201
@app.route("/fam_verify",methods=["GET","POST"])
def fam_verify():
    api_key=get_api_key()
    if not api_key or api_key not in BotKeys: return error("Invalid or missing API key.",401)
    oid=str((request.args.get("order_id") if request.method=="GET" else (request.get_json(silent=True) or {}).get("order_id",""))).strip()
    if not oid: return error("order_id is required.")
    with LOCK:
        order=Orders.get(oid)
        if not isinstance(order,dict): return error("Order not found.",404)
        if order.get("api_key")!=api_key: return error("This order does not belong to this API key.",403)
        paid=PaidRecords.get(oid)
    if paid: return jsonify({"status":"success","data":paid})
    if int(time.time())>int(order.get("expires_at",0)): return jsonify({"status":"pending","message":"Order has expired.","data":{"order_id":oid,"amount":order.get("amount")}})
    res,msg=check_gmail_payment(BotKeys[api_key],order)
    if not res: return jsonify({"status":"pending","message":msg,"data":{"order_id":oid,"amount":order.get("amount")}})
    with LOCK:
        PaidRecords[oid]=res
        order["status"]="email_match"
        Orders[oid]=order
        save_json(PAID_FILE,PaidRecords)
        save_json(ORDERS_FILE,Orders)
    return jsonify({"status":"success","data":res})
@app.errorhandler(404)
def not_found(_): return jsonify({"status":"error","message":"Endpoint not found."}),404
@app.errorhandler(405)
def method_not_allowed(_): return jsonify({"status":"error","message":"Method not allowed."}),405
@app.errorhandler(500)
def internal_error(_): return jsonify({"status":"error","message":"Internal server error."}),500
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
