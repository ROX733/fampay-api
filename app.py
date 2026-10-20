from flask import Flask, request, jsonify
import requests, os, json, urllib.parse
app = Flask(__name__)
FAMPAY_UPI=os.getenv("FAMPAY_UPI","papai69@fam")
GMAIL=os.getenv("GMAIL","")
GPASS=os.getenv("GPASS","")
API_KEY=os.getenv("API_KEY","papifam123")
PAID_FILE="paid.json"
def load_paid():
 try:
  if os.path.exists(PAID_FILE):
   with open(PAID_FILE,"r") as f: return set(json.load(f))
 except: pass
 return set()
def save_paid(utr):
 try:
  p=load_paid(); p.add(str(utr))
  with open(PAID_FILE,"w") as f: json.dump(list(p),f)
 except: pass
def is_paid(utr): return str(utr) in load_paid()
def enc(s): return urllib.parse.quote(str(s),safe='')
@app.route('/')
def home(): return jsonify({"ok":True,"upi":FAMPAY_UPI})
@app.route('/health')
def health(): return jsonify({"ok":True,"upi":FAMPAY_UPI,"gmail_set":bool(GMAIL and GPASS)})
@app.route('/pay')
def pay():
 amount=request.args.get("amount","100")
 amount_f=float(str(amount).replace("₹","").replace(",",""))
 upi_raw=f"upi://pay?pa={FAMPAY_UPI}&am={amount_f:.2f}&cu=INR"
 qr=f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={enc(upi_raw)}"
 return jsonify({"ok":True,"upi":FAMPAY_UPI,"amount":amount_f,"upi_link":upi_raw,"qr_url":qr})
@app.route('/verify',methods=['GET','POST'])
def verify():
 if request.method=='GET':
  utr=request.args.get("utr") or request.args.get("id")
  key=request.args.get("api_key") or request.headers.get("x-api-key")
  user_id=request.args.get("user_id"); credit=request.args.get("credit")
 else:
  data=request.get_json(silent=True) or request.form.to_dict() or {}
  utr=data.get("utr") or request.args.get("utr")
  key=data.get("api_key") or request.headers.get("x-api-key") or request.args.get("api_key")
  user_id=data.get("user_id"); credit=data.get("credit")
 if not utr or len(str(utr).strip())<6: return jsonify({"ok":False,"error":"utr required"}),400
 utr=str(utr).strip().replace(" ","").replace("-","")
 if API_KEY and str(key)!=str(API_KEY): return jsonify({"ok":False,"status":"unauthorized"}),401
 if is_paid(utr): return jsonify({"ok":False,"status":"already_used","utr":utr}),400
 if not GMAIL or not GPASS: return jsonify({"ok":False,"error":"GMAIL/GPASS not set"}),500
 url=f"https://txggateway.vercel.app/api?Gmail={enc(GMAIL)}&GPASS={enc(GPASS)}&ID={enc(utr)}"
 r=requests.get(url,timeout=45); j=r.json()
 sta=str(j.get("status","")).lower(); ft=j.get("first_time",False)
 amt_str=str(j.get("amount","0") or "0")
 tmp=""; dot=False
 for ch in amt_str:
  if ch.isdigit(): tmp+=ch
  elif ch=="." and not dot: tmp+=ch; dot=True
 try: paid_amt=float(tmp) if tmp else 0
 except: paid_amt=0
 if sta=="not_found": return jsonify({"ok":False,"status":"not_found","utr":utr})
 if sta=="already_used": save_paid(utr); return jsonify({"ok":False,"status":"already_used","utr":utr})
 if sta=="verified" and ft==True:
  if str(credit).lower() in ("1","true","yes") and user_id:
   save_paid(utr); return jsonify({"ok":True,"status":"verified","utr":utr,"amount":paid_amt,"credited_to":str(user_id)})
  return jsonify({"ok":True,"status":"verified","utr":utr,"amount":paid_amt})
 return jsonify({"ok":False,"status":sta,"raw":j})
@app.route('/webhook',methods=['POST','GET'])
def webhook():
 data=request.get_json(silent=True) or request.args.to_dict() or {}
 utr=data.get("utr") or data.get("txn_id")
 if not utr: return jsonify({"ok":False,"error":"utr required"}),400
 if is_paid(str(utr)): return jsonify({"ok":False,"status":"already_used"}),400
 save_paid(str(utr))
 return jsonify({"ok":True,"status":"credited","utr":str(utr)})
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get("PORT",5000)))
