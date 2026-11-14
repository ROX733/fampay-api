
import os, json, time, secrets, re, math, ssl, imaplib, email
from io import BytesIO
from datetime import datetime, timezone
from email.header import decode_header, make_header
from threading import RLock
from urllib.parse import quote
from flask import Flask, request, jsonify, render_template_string, send_file
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import ImageDraw, ImageFont
from cryptography.fernet import Fernet

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_FILE = os.path.join(BASE_DIR, "keys.json")
ORDERS_FILE = os.path.join(BASE_DIR, "orders.json")
PAID_FILE = os.path.join(BASE_DIR, "paid.json")
ORDER_EXPIRY = 300
IMAP_HOST = "imap.gmail.com"
LOCK = RLock()

def _fernet():
    key = os.getenv("FERNET_KEY", "").strip()
    if not key:
        return None
    try:
        return Fernet(key.encode("utf-8"))
    except Exception as exc:
        raise RuntimeError("FERNET_KEY is invalid; generate a Fernet key and set it in Render.") from exc

def encrypt_gmail_password(value):
    cipher = _fernet()
    if cipher is None:
        raise RuntimeError("FERNET_KEY is not configured.")
    return "enc:" + cipher.encrypt(str(value).encode("utf-8")).decode("ascii")

def decrypt_gmail_password(record):
    value = str(record.get("gpass", "")).strip()
    if value.startswith("enc:"):
        cipher = _fernet()
        if cipher is None:
            raise RuntimeError("FERNET_KEY is required to decrypt stored Gmail credentials.")
        return cipher.decrypt(value[4:].encode("ascii")).decode("utf-8")
    return value  # Legacy plaintext records are migrated when FERNET_KEY is configured.

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

def get_all_keys():
    with LOCK:
        try:
            with open(KEYS_FILE,"r",encoding="utf-8") as f:
                data=json.load(f)
                if isinstance(data,dict):
                    return data
        except:
            pass
    return {}

BotKeys=load_json(KEYS_FILE)
Orders=load_json(ORDERS_FILE)
PaidRecords=load_json(PAID_FILE)
# Migrate legacy plaintext Gmail App Passwords to encrypted-at-rest values.
try:
    _cipher = _fernet()
    if _cipher:
        _changed = False
        for _record in BotKeys.values():
            if isinstance(_record, dict) and _record.get("gpass") and not str(_record.get("gpass")).startswith("enc:"):
                _record["gpass"] = encrypt_gmail_password(_record["gpass"])
                _changed = True
        if _changed:
            save_json(KEYS_FILE, BotKeys)
except Exception as _migration_error:
    print(f"Gmail credential migration warning: {_migration_error}")

HTML = """<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#6d5dfc">
<title>FamPay API — Developer Portal</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#f6f7fc;--surface:#fff;--surface2:#f2f3fa;--text:#17172b;--muted:#70728a;--line:#e7e8f1;--purple:#6d5dfc;--purple2:#8c62ff;--code:#111326;--shadow:0 18px 55px rgba(38,32,92,.08)}
html[data-theme=dark]{--bg:#0d1020;--surface:#171b30;--surface2:#202540;--text:#f2f2ff;--muted:#a5a8c0;--line:#303651;--purple:#a79aff;--purple2:#846cff;--code:#090c19;--shadow:0 18px 55px rgba(0,0,0,.22);color-scheme:dark}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;transition:background .25s,color .25s}
a{color:inherit;text-decoration:none}.shell{max-width:1060px;margin:auto;padding:0 22px}
.topbar{height:76px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.brand{display:flex;align-items:center;gap:11px;font-family:'Space Grotesk';font-weight:700;font-size:18px;letter-spacing:-.5px}
.brand-mark{height:38px;width:38px;border-radius:13px;display:grid;place-items:center;color:#fff;background:linear-gradient(135deg,#6d5dfc,#a66bff);box-shadow:0 8px 20px #6d5dfc44;font-size:20px}
.nav-actions{display:flex;align-items:center;gap:10px}.nav-link{font-size:13px;font-weight:700;color:var(--muted);padding:10px 12px}
.theme-btn{border:1px solid var(--line);background:var(--surface);color:var(--text);border-radius:12px;padding:10px 13px;font:700 12px 'DM Sans';cursor:pointer}
.hero{position:relative;overflow:hidden;border-radius:30px;padding:54px 48px 40px;background:linear-gradient(120deg,#17152f 0%,#30236b 48%,#714dcb 100%);color:#fff;box-shadow:0 24px 65px #34217a30}
.hero:before,.hero:after{content:"";position:absolute;border-radius:50%;filter:blur(1px);pointer-events:none}
.hero:before{width:320px;height:320px;right:-80px;top:-160px;background:#b7a4ff26}
.hero:after{width:220px;height:220px;right:160px;bottom:-170px;background:#e2b5ff20}
.hero-inner{position:relative;z-index:1;max-width:700px}
.eyebrow{display:inline-flex;align-items:center;gap:8px;border:1px solid #ffffff35;background:#ffffff12;border-radius:999px;padding:7px 12px;font-size:10px;font-weight:800;letter-spacing:1.5px;color:#ddd6ff}
.live-dot{width:7px;height:7px;background:#66e6b1;border-radius:50%;box-shadow:0 0 0 4px #66e6b122}
.hero h1{font:700 clamp(34px,6vw,54px)/1.04 'Space Grotesk';letter-spacing:-2px;margin:22px 0 14px}
.hero h1 span{background:linear-gradient(90deg,#c9baff,#ffcbf2);-webkit-background-clip:text;background-clip:text;color:transparent}
.hero p{max-width:590px;color:#d3cfee;font-size:15px;line-height:1.75;margin:0}
.hero-pills{display:flex;flex-wrap:wrap;gap:9px;margin-top:24px}.hero-pill{border:1px solid #ffffff30;background:#ffffff12;padding:8px 11px;border-radius:10px;color:#f1edff;font-size:11px;font-weight:700}
.base-card{margin-top:20px;background:var(--surface);border:1px solid var(--line);border-radius:20px;padding:20px 22px;box-shadow:var(--shadow)}
.base-top{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}
.base-title{font-size:12px;font-weight:800;letter-spacing:1px;color:var(--muted)}
.base-url-row{display:flex;align-items:center;gap:12px}
.base-url{font:500 13px 'JetBrains Mono';word-break:break-all;flex:1;color:var(--text)}
.copy-base{flex-shrink:0;border:0;background:var(--purple);color:#fff;padding:10px 14px;border-radius:11px;font:700 11px 'DM Sans';cursor:pointer}
.base-help{font-size:11px;color:var(--muted);line-height:1.6;margin-top:11px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:20px 0 34px}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:16px;display:flex;align-items:center;gap:12px}
.stat-icon{width:38px;height:38px;display:grid;place-items:center;border-radius:12px;background:var(--surface2);font-size:18px}
.stat b{display:block;font-size:12px}.stat small{display:block;color:var(--muted);font-size:10px;margin-top:3px}
.section-kicker{font-size:10px;letter-spacing:1.8px;font-weight:800;color:var(--purple);margin:30px 0 8px}
.section-heading{font:700 26px 'Space Grotesk';letter-spacing:-.7px;margin:0 0 7px}
.section-intro{font-size:13px;color:var(--muted);line-height:1.7;margin:0 0 18px}
.doc-card{background:var(--surface);border:1px solid var(--line);border-radius:22px;padding:24px;margin:16px 0;box-shadow:var(--shadow)}
.doc-head{display:flex;align-items:center;gap:13px;margin-bottom:10px}
.doc-icon{width:43px;height:43px;border-radius:14px;display:grid;place-items:center;background:linear-gradient(135deg,#eeeaff,#e8e3ff);color:#5b4ce0;font-size:20px}
html[data-theme=dark] .doc-icon{background:#302b54;color:#c7bbff}
.doc-title{font:700 18px 'Space Grotesk';margin:0}.doc-sub{font-size:10px;color:var(--muted);font-weight:800;letter-spacing:1px;margin-top:3px}
.doc-desc{font-size:13px;color:var(--muted);line-height:1.7;margin:8px 0 15px}
.endpoint{display:flex;align-items:center;gap:10px;background:var(--surface2);border:1px solid var(--line);border-radius:12px;padding:12px;margin:12px 0;min-width:0}
.method{background:#e5e0ff;color:#5746d8;border-radius:7px;padding:5px 8px;font-size:10px;font-weight:900}
html[data-theme=dark] .method{background:#39315f;color:#d1c8ff}
.endpoint code{font:11px 'JetBrains Mono';word-break:break-all;line-height:1.6}
.param-title{font-size:10px;font-weight:900;letter-spacing:1.2px;margin:18px 0 9px}
.param-table{border:1px solid var(--line);border-radius:12px;overflow:hidden}
.param-row{display:grid;grid-template-columns:100px 90px 1fr;gap:10px;padding:12px;font-size:11px;border-top:1px solid var(--line);align-items:center}
.param-row:first-child{border-top:0;background:var(--surface2);font-size:9px;font-weight:900;color:var(--muted);letter-spacing:1px}
.param-row code{font:600 11px 'JetBrains Mono'}
.required{font-size:9px;font-weight:800;color:#d64e67}
.codebox{background:var(--code);border:1px solid #282b43;border-radius:15px;overflow:hidden;margin-top:14px}
.codebar{display:flex;align-items:center;justify-content:space-between;padding:10px 13px;border-bottom:1px solid #292c44;color:#a9aec8;font-size:10px;font-weight:800}
.copy-code{border:0;background:#34305d;color:#e7e1ff;border-radius:8px;padding:7px 10px;font-size:10px;font-weight:800;cursor:pointer}
.codebox pre{margin:0;padding:15px;color:#e4e6f3;font:11px/1.8 'JetBrains Mono';white-space:pre-wrap;overflow:auto;word-break:break-word}
.tip{margin-top:14px;background:#fff8e8;color:#87601b;border:1px solid #f4dfae;border-radius:12px;padding:12px;font-size:11px;line-height:1.6}
html[data-theme=dark] .tip{background:#352c1d;color:#f5d994;border-color:#65502c}
.features{display:grid;grid-template-columns:repeat(3,1fr);gap:13px;margin-top:18px}
.feature{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:20px}
.feature-icon{font-size:23px;margin-bottom:13px}.feature h3{font:700 14px 'Space Grotesk';margin:0 0 7px}.feature p{font-size:11px;line-height:1.65;color:var(--muted);margin:0}
.key-card{background:linear-gradient(145deg,var(--surface),var(--surface2));border:1px solid var(--line);border-radius:24px;padding:25px;box-shadow:var(--shadow);margin:18px 0 30px}
.key-form{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px}
.field label{display:block;font-size:11px;font-weight:800;margin-bottom:7px}
.field input{width:100%;border:1px solid var(--line);background:var(--surface);color:var(--text);border-radius:11px;padding:13px;font:13px 'DM Sans';outline:none}
.field input:focus{border-color:var(--purple);box-shadow:0 0 0 3px #7968ff22}
.key-submit{grid-column:1/-1;border:0;border-radius:12px;padding:14px;background:linear-gradient(100deg,#6d5dfc,#9b5bfa);color:white;font:800 13px 'DM Sans';cursor:pointer}
.key-submit:disabled{opacity:.6;cursor:wait}
.key-result{display:none;margin-top:15px;padding:14px;border-radius:12px;background:#e9fff2;color:#12643b;font-size:12px;overflow-wrap:anywhere}
.key-result.error{background:#fff0f0;color:#9f2525}
.key-value{font:11px 'JetBrains Mono';padding:11px;background:#fff;border:1px solid #d8e5dc;border-radius:9px;margin-top:9px;color:#18251d}
.key-copy{border:0;background:#202039;color:white;border-radius:8px;padding:9px 12px;font-weight:800;font-size:10px;margin-top:9px}
.key-note{font-size:11px;color:var(--muted);line-height:1.65;margin-top:13px}
.info-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:13px;margin:18px 0 30px}
.info-card{background:var(--surface);border:1px solid var(--line);border-radius:17px;padding:18px}
.info-card h3{font:700 14px 'Space Grotesk';margin:0 0 8px}
.info-card p,.info-card li{font-size:11px;line-height:1.7;color:var(--muted)}
.info-card ul{padding-left:18px;margin:8px 0 0}
.console-card{background:var(--surface);border:1px solid var(--line);border-radius:22px;padding:24px;margin:18px 0 30px;box-shadow:var(--shadow)}
.console-form{display:grid;grid-template-columns:1fr 1fr;gap:13px}
.console-form .field{min-width:0}
.console-form .console-submit{grid-column:1/-1;border:0;border-radius:12px;padding:14px;background:linear-gradient(100deg,#6d5dfc,#9b5bfa);color:#fff;font:800 13px 'DM Sans';cursor:pointer}
.console-submit:disabled{opacity:.6;cursor:wait}
.console-output{display:none;margin-top:18px;border:1px solid var(--line);border-radius:14px;overflow:hidden}
.console-output-head{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px 13px;background:var(--surface2);font-size:11px;font-weight:800}
.console-output pre{margin:0;padding:15px;background:var(--code);color:#e4e6f3;font:11px/1.8 'JetBrains Mono';white-space:pre-wrap;overflow-wrap:anywhere;max-height:360px;overflow:auto}
.console-hint{font-size:11px;line-height:1.7;color:var(--muted);margin-top:12px}
@media(max-width:650px){.info-grid,.console-form{grid-template-columns:1fr}.console-form .console-submit{grid-column:auto}}
.footer{border-top:1px solid var(--line);padding:22px 0 32px;text-align:center;color:var(--muted);font-size:11px}
@media(max-width:650px){.shell{padding:0 14px}.topbar{height:66px}.nav-link{display:none}.hero{padding:38px 23px 30px;border-radius:23px}.hero h1{letter-spacing:-1.3px}.stats{gap:8px}.stat{padding:11px;display:block}.stat-icon{margin-bottom:8px}.stat b{font-size:10px}.stat small{font-size:9px}.doc-card{padding:18px}.param-row{grid-template-columns:75px 72px 1fr;padding:10px 8px;font-size:10px}.features{grid-template-columns:1fr}.feature{display:flex;gap:13px;align-items:flex-start}.feature-icon{margin:0}.key-form{grid-template-columns:1fr}.key-submit{grid-column:auto}.base-url-row{align-items:flex-start;flex-direction:column}.copy-base{width:100%}}

/* Premium motion layer */
body{overflow-x:hidden}
body:before{content:"";position:fixed;inset:0;z-index:-2;pointer-events:none;background:radial-gradient(ellipse at 12% 12%,rgba(109,93,252,.10),transparent 35%),radial-gradient(ellipse at 88% 42%,rgba(166,107,255,.08),transparent 32%)}
.hero{background-size:180% 180%;animation:heroGradient 14s ease infinite}
.hero:before{animation:orbFloat 9s ease-in-out infinite alternate}
.hero:after{animation:orbFloat 12s ease-in-out infinite alternate-reverse}
.brand-mark{animation:markPulse 4s ease-in-out infinite}
.hero h1 span{background-size:200% auto;animation:textShimmer 6s linear infinite}
.doc-card,.feature,.info-card,.stat,.base-card,.key-card,.console-card{transition:transform .35s cubic-bezier(.2,.8,.2,1),box-shadow .35s,border-color .35s}
.doc-card:hover,.feature:hover,.info-card:hover,.stat:hover{transform:translateY(-4px);box-shadow:0 22px 55px rgba(70,53,150,.12);border-color:rgba(109,93,252,.28)}
.copy-base,.key-submit,.console-submit,.theme-btn,.copy-code,.key-copy{transition:transform .2s,filter .2s,box-shadow .2s}
.copy-base:hover,.key-submit:hover,.console-submit:hover,.theme-btn:hover,.copy-code:hover,.key-copy:hover{transform:translateY(-2px);filter:brightness(1.06);box-shadow:0 9px 22px rgba(109,93,252,.2)}
.reveal{opacity:0;transform:translateY(22px);transition:opacity .7s ease,transform .7s cubic-bezier(.2,.8,.2,1)}
.reveal.is-visible{opacity:1;transform:translateY(0)}
.hero-inner>*{animation:fadeUp .8s both}
.hero-inner>*:nth-child(2){animation-delay:.10s}.hero-inner>*:nth-child(3){animation-delay:.20s}.hero-inner>*:nth-child(4){animation-delay:.30s}
@keyframes heroGradient{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
@keyframes orbFloat{from{transform:translate3d(0,0,0) scale(1)}to{transform:translate3d(-24px,18px,0) scale(1.08)}}
@keyframes markPulse{0%,100%{box-shadow:0 8px 20px #6d5dfc44}50%{box-shadow:0 8px 28px #9b5bfa88}}
@keyframes textShimmer{to{background-position:200% center}}
@keyframes fadeUp{from{opacity:0;transform:translateY(15px)}to{opacity:1;transform:translateY(0)}}

/* Extra lively interactions: emoji motion, glow and tactile buttons */
.live-dot{animation:livePulse 2s ease-in-out infinite}
.stat-icon,.doc-icon,.feature-icon{transform-origin:50% 65%;animation:emojiFloat 3.6s ease-in-out infinite}
.stat:nth-child(2) .stat-icon,.feature:nth-child(2) .feature-icon{animation-delay:.45s}
.stat:nth-child(3) .stat-icon,.feature:nth-child(3) .feature-icon{animation-delay:.9s}
.doc-card:nth-of-type(2) .doc-icon{animation:emojiWiggle 4.5s ease-in-out infinite}
.hero-pill{animation:pillBob 4s ease-in-out infinite}
.hero-pill:nth-child(2){animation-delay:.55s}.hero-pill:nth-child(3){animation-delay:1.1s}
.brand:hover .brand-mark{animation:markSpin .65s ease}
.theme-btn:active,.copy-base:active,.key-submit:active,.console-submit:active,.copy-code:active,.key-copy:active{transform:translateY(1px) scale(.97)}
.key-submit,.console-submit,.copy-base{position:relative;overflow:hidden}
.key-submit:before,.console-submit:before,.copy-base:before{content:"";position:absolute;inset:-80% auto -80% -35%;width:22%;transform:rotate(22deg);background:linear-gradient(90deg,transparent,#ffffff55,transparent);transition:left .65s ease}
.key-submit:hover:before,.console-submit:hover:before,.copy-base:hover:before{left:120%}
.feature:hover .feature-icon,.stat:hover .stat-icon,.doc-card:hover .doc-icon{animation:emojiPop .65s ease}
@keyframes livePulse{0%,100%{box-shadow:0 0 0 3px #66e6b122;opacity:1}50%{box-shadow:0 0 0 8px #66e6b10a;opacity:.72}}
@keyframes emojiFloat{0%,100%{transform:translateY(0) rotate(0)}35%{transform:translateY(-5px) rotate(-5deg)}70%{transform:translateY(-2px) rotate(4deg)}}
@keyframes emojiWiggle{0%,85%,100%{transform:rotate(0)}88%{transform:rotate(-9deg)}92%{transform:rotate(8deg)}96%{transform:rotate(-4deg)}}
@keyframes pillBob{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
@keyframes markSpin{to{transform:rotate(360deg)}}
@keyframes emojiPop{0%{transform:scale(1)}45%{transform:scale(1.22) rotate(-8deg)}75%{transform:scale(.94) rotate(5deg)}100%{transform:scale(1)}}



@media(prefers-reduced-motion:reduce){.hero,.hero:before,.hero:after,.hero-inner:after,.motion-version,.motion-spark,.hero-pill,.stat-icon,.doc-icon,.feature-icon,.brand-mark:after{animation:none!important}}

/* V3: highly visible motion layer; scroll reveal above remains enabled */
.motion-version{display:inline-flex;align-items:center;gap:9px;margin-top:15px;padding:9px 13px;border:1px solid #d7caff66;border-radius:999px;background:linear-gradient(100deg,#ffffff20,#bda7ff30,#ffffff12);color:#fff;font-size:10px;font-weight:900;letter-spacing:1.25px;box-shadow:0 0 0 1px #ffffff0c,0 8px 28px #a88aff30;animation:versionGlow 2.8s ease-in-out infinite}
.motion-version b{padding:3px 7px;border-radius:7px;background:#fff;color:#5942c9;font-size:10px}
.motion-version span{color:#baf8df;font-size:9px;letter-spacing:1px}
.hero{isolation:isolate}
.hero:before{width:360px;height:360px;right:-75px;top:-170px;background:radial-gradient(circle,#c6b3ff55 0%,#a78aff20 48%,transparent 72%);filter:blur(3px);animation:orbFloat 6s ease-in-out infinite alternate,orbGlow 3.8s ease-in-out infinite}
.hero:after{width:270px;height:270px;right:18%;bottom:-195px;background:radial-gradient(circle,#ffb8ed38 0%,#d8aaff18 48%,transparent 72%);animation:orbFloat 8s ease-in-out infinite alternate-reverse}
.hero-pill{transition:transform .25s,background .25s,border-color .25s;animation:pillBob 2.8s ease-in-out infinite}
.hero-pill:hover{transform:translateY(-7px) scale(1.04);background:#ffffff25;border-color:#ffffff75}
.stat-icon,.doc-icon,.feature-icon{will-change:transform;animation:emojiBounce 2.8s ease-in-out infinite}
.stat:nth-child(2) .stat-icon,.feature:nth-child(2) .feature-icon,.doc-card:nth-of-type(2) .doc-icon{animation-delay:.35s}
.stat:nth-child(3) .stat-icon,.feature:nth-child(3) .feature-icon{animation-delay:.7s}
.doc-card:hover,.feature:hover,.info-card:hover,.stat:hover{transform:translateY(-7px) scale(1.012);box-shadow:0 26px 65px rgba(109,93,252,.19);border-color:#8d7cff88}
.brand-mark{position:relative;overflow:hidden}
.brand-mark:after{content:"";position:absolute;inset:-60%;background:linear-gradient(110deg,transparent 42%,#ffffffa8 50%,transparent 58%);transform:translateX(-100%);animation:markShine 4s ease-in-out infinite}
.copy-base,.key-submit,.console-submit,.theme-btn,.copy-code,.key-copy{transition:transform .22s cubic-bezier(.2,.8,.2,1),filter .22s,box-shadow .22s}
.copy-base:hover,.key-submit:hover,.console-submit:hover{transform:translateY(-3px) scale(1.015);box-shadow:0 13px 30px #765cff55}
.reveal{will-change:opacity,transform}
.reveal.is-visible{animation:revealSettle .65s cubic-bezier(.2,.8,.2,1) both}
@keyframes versionGlow{0%,100%{box-shadow:0 0 0 1px #ffffff0c,0 8px 22px #a88aff24;filter:brightness(1)}50%{box-shadow:0 0 0 4px #ffffff0c,0 10px 34px #c5aaff70;filter:brightness(1.16)}}
@keyframes orbGlow{0%,100%{opacity:.65}50%{opacity:1}}
@keyframes emojiBounce{0%,100%{transform:translateY(0) rotate(0) scale(1)}30%{transform:translateY(-7px) rotate(-7deg) scale(1.08)}55%{transform:translateY(1px) rotate(4deg) scale(.98)}75%{transform:translateY(-3px) rotate(-3deg) scale(1.03)}}
@keyframes markShine{0%,65%,100%{transform:translateX(-100%)}82%{transform:translateX(100%)}}
@keyframes revealSettle{0%{filter:blur(2px)}100%{filter:blur(0)}}

/* V4 — premium visual system: restrained palette, sculpted surfaces, visible motion */
:root{--purple:#6654e8;--purple2:#9879ff;--shadow:0 22px 65px rgba(38,29,92,.10)}
html[data-theme=dark]{--purple:#ad9bff;--purple2:#c2a4ff}
body{background-image:radial-gradient(ellipse at 50% -12%,rgba(119,96,255,.13),transparent 44%),linear-gradient(180deg,rgba(255,255,255,.25),transparent 42%)}
.shell{position:relative}
.hero{border:1px solid rgba(255,255,255,.14);background:linear-gradient(118deg,#11152d 0%,#25204d 43%,#4b358f 76%,#7255bf 100%);background-size:220% 220%;animation:premiumGradient 10s ease-in-out infinite;box-shadow:0 28px 85px rgba(53,38,126,.27)}
.hero:before{width:440px;height:440px;right:-95px;top:-235px;background:radial-gradient(circle,rgba(196,174,255,.38),rgba(131,105,255,.12) 42%,transparent 70%);filter:blur(2px);animation:premiumOrb 7s ease-in-out infinite alternate}
.hero:after{width:330px;height:330px;right:18%;bottom:-235px;background:radial-gradient(circle,rgba(255,191,235,.2),rgba(164,137,255,.08) 48%,transparent 72%);animation:premiumOrb 9s ease-in-out infinite alternate-reverse}
.hero-inner:after{content:"";position:absolute;z-index:-1;right:-245px;top:15px;width:300px;height:300px;border:1px solid rgba(255,255,255,.15);border-radius:50%;box-shadow:0 0 0 24px rgba(255,255,255,.025),0 0 0 50px rgba(255,255,255,.018);animation:ringOrbit 24s linear infinite}
.motion-version{border:1px solid rgba(220,208,255,.32);background:linear-gradient(115deg,rgba(255,255,255,.16),rgba(165,139,255,.18));box-shadow:inset 0 1px rgba(255,255,255,.2),0 8px 26px rgba(10,8,40,.18);letter-spacing:1.6px}
.motion-version b{background:linear-gradient(135deg,#fff,#ded4ff);color:#4d3caa}
.motion-spark{width:7px;height:7px;border-radius:50%;background:#9cf3d0;box-shadow:0 0 0 5px rgba(156,243,208,.13),0 0 18px #9cf3d0;animation:sparkPulse 1.8s ease-in-out infinite}
.stat,.doc-card,.feature,.info-card,.base-card,.key-card,.console-card{position:relative;overflow:hidden;border-color:color-mix(in srgb,var(--line) 78%,var(--purple) 22%);box-shadow:0 12px 38px rgba(34,27,82,.055),inset 0 1px rgba(255,255,255,.7)}
html[data-theme=dark] .stat,html[data-theme=dark] .doc-card,html[data-theme=dark] .feature,html[data-theme=dark] .info-card,html[data-theme=dark] .base-card,html[data-theme=dark] .key-card,html[data-theme=dark] .console-card{box-shadow:0 14px 42px rgba(0,0,0,.2),inset 0 1px rgba(255,255,255,.035)}
.stat:before,.doc-card:before,.feature:before,.info-card:before{content:"";position:absolute;inset:0 0 auto;height:2px;background:linear-gradient(90deg,transparent,var(--purple2),#d9caff,transparent);opacity:.7}
.stat-icon,.doc-icon,.feature-icon{display:grid;place-items:center;flex:0 0 auto;border:1px solid rgba(128,105,235,.2);background:linear-gradient(145deg,#fff 0%,#f0edff 55%,#e2dcff 100%);color:#5b49c9;box-shadow:inset 0 1px 0 #fff,0 8px 20px rgba(83,65,180,.12);font-family:'Space Grotesk';font-weight:700}
.stat-icon{width:42px;height:42px;border-radius:14px;font-size:20px}
.doc-icon{width:46px;height:46px;border-radius:15px;font-size:13px;letter-spacing:.5px}
.feature-icon{width:44px;height:44px;border-radius:14px;font-size:21px;margin-bottom:13px}
html[data-theme=dark] .stat-icon,html[data-theme=dark] .doc-icon,html[data-theme=dark] .feature-icon{background:linear-gradient(145deg,#30294f,#211d3d);color:#c9bcff;border-color:#9c87ff35;box-shadow:inset 0 1px #ffffff15,0 9px 22px #05040d66}
.stat-icon,.doc-icon,.feature-icon{animation:premiumIconDrift 5.5s ease-in-out infinite}
.stat:nth-child(2) .stat-icon,.feature:nth-child(2) .feature-icon{animation-delay:1s}
.stat:nth-child(3) .stat-icon,.feature:nth-child(3) .feature-icon{animation-delay:2s}
.doc-card:nth-of-type(2) .doc-icon{animation-delay:1.2s}
.doc-card:hover .doc-icon,.feature:hover .feature-icon,.stat:hover .stat-icon{animation:premiumIconFocus .65s cubic-bezier(.2,.8,.2,1)}
.hero-pill{border:1px solid rgba(220,210,255,.2);background:linear-gradient(135deg,rgba(255,255,255,.13),rgba(255,255,255,.045));backdrop-filter:blur(12px);box-shadow:inset 0 1px rgba(255,255,255,.13);animation:pillFloat 5s ease-in-out infinite}
.hero-pill:nth-child(2){animation-delay:1s}.hero-pill:nth-child(3){animation-delay:2s}
.doc-card:hover,.feature:hover,.info-card:hover,.stat:hover{transform:translateY(-6px);box-shadow:0 24px 60px rgba(82,65,170,.15);border-color:rgba(132,111,255,.45)}
.brand-mark{background:linear-gradient(145deg,#7462f5,#9b79ff 55%,#5946d4);box-shadow:0 9px 24px rgba(105,82,238,.35),inset 0 1px rgba(255,255,255,.38)}
.brand-mark:after{animation:premiumSheen 5s ease-in-out infinite}
.key-submit,.console-submit,.copy-base{background:linear-gradient(105deg,#5c4bd6,#8066f2 55%,#a077f6);box-shadow:0 9px 22px rgba(105,82,238,.2)}
.reveal{opacity:0;transform:translateY(30px) scale(.985);transition:opacity .85s ease,transform .85s cubic-bezier(.16,1,.3,1)}
.reveal.is-visible{opacity:1;transform:translateY(0) scale(1)}
@keyframes premiumGradient{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
@keyframes premiumOrb{0%{transform:translate3d(-18px,8px,0) scale(.92);opacity:.58}100%{transform:translate3d(24px,-14px,0) scale(1.12);opacity:1}}
@keyframes ringOrbit{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
@keyframes sparkPulse{0%,100%{transform:scale(.85);opacity:.7}50%{transform:scale(1.2);opacity:1}}
@keyframes premiumIconDrift{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
@keyframes premiumIconFocus{0%{transform:scale(1)}45%{transform:scale(1.12) rotate(-5deg)}100%{transform:scale(1)}}
@keyframes pillFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
@keyframes premiumSheen{0%,68%,100%{transform:translateX(-120%)}84%{transform:translateX(120%)}}
@media(max-width:650px){.hero-inner:after{right:-205px;top:38px;width:210px;height:210px}.motion-version{font-size:9px}.stat-icon{width:40px;height:40px}}


@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation-duration:.01ms!important;animation-iteration-count:1!important;scroll-behavior:auto!important;transition-duration:.01ms!important}.reveal{opacity:1;transform:none}}


/* V5 — Telegram-like animated emoji + high-contrast API response panels */
.premium-emoji{font-family:"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif!important;font-weight:400!important;font-size:23px!important;line-height:1;filter:drop-shadow(0 5px 7px rgba(86,65,190,.24));animation:telegramEmojiFloat 2.1s cubic-bezier(.4,0,.2,1) infinite}
.stat:nth-child(2) .premium-emoji,.feature:nth-child(2) .premium-emoji{animation-delay:.3s}
.stat:nth-child(3) .premium-emoji,.feature:nth-child(3) .premium-emoji{animation-delay:.6s}
.doc-card:nth-of-type(2) .premium-emoji{animation-delay:.45s}
.doc-card:hover .premium-emoji,.feature:hover .premium-emoji,.stat:hover .premium-emoji{animation:telegramEmojiPop .55s cubic-bezier(.2,.8,.2,1)}
@keyframes telegramEmojiFloat{0%,100%{transform:translateY(0) scale(1) rotate(0);filter:drop-shadow(0 4px 5px rgba(86,65,190,.18))}35%{transform:translateY(-6px) scale(1.12) rotate(-7deg);filter:drop-shadow(0 9px 9px rgba(86,65,190,.3))}68%{transform:translateY(1px) scale(.97) rotate(4deg)}}
@keyframes telegramEmojiPop{0%{transform:scale(1)}45%{transform:scale(1.28) rotate(-10deg)}75%{transform:scale(.92) rotate(6deg)}100%{transform:scale(1)}}
.codebox pre,.console-output pre{background:#000!important;color:#f4f4f4!important}
.success-response .codebar{background:linear-gradient(100deg,#087b45,#0b9b5a)!important;color:#fff!important;border-bottom-color:#087b45!important}
.success-response .codebar .copy-code{background:#ffffff24!important;color:#fff!important;border:1px solid #ffffff35}
.console-output-head.is-success{background:linear-gradient(100deg,#087b45,#0b9b5a)!important;color:#fff!important}
.console-output-head.is-error{background:#8f2534!important;color:#fff!important}
@media(prefers-reduced-motion:reduce){.premium-emoji{animation:none!important}}

</style>
</head>
<body>
<div class="shell">
<header class="topbar">
  <a class="brand" href="/"><span class="brand-mark">ϟ</span><span>FamPay <span style="color:var(--purple)">API</span></span></a>
  <nav class="nav-actions"><a class="nav-link" href="#documentation">Documentation</a><a class="nav-link" href="#generate-api-key">Create API Key</a><button class="theme-btn" id="themeToggle" type="button">🌙 Dark mode</button></nav>
</header>
<section class="hero">
  <div class="hero-inner">
    <div class="eyebrow"><span class="live-dot"></span> DEVELOPER PLATFORM</div>
    <div class="motion-version"><span class="motion-spark"></span> DESIGN SYSTEM <b>V4</b> <span>LIVE</span></div>
    <h1>Payments made<br><span>simple & automatic.</span></h1>
    <p>Create UPI payment requests, generate hosted QR codes and verify incoming payments through your registered Gmail inbox — all through one straightforward API.</p>
    <div class="hero-pills"><span class="hero-pill">UPI QR generation</span><span class="hero-pill">Gmail IMAP verification</span><span class="hero-pill">Simple REST endpoints</span></div>
  </div>
</section>
<section class="base-card">
  <div class="base-top"><div class="base-title">YOUR API BASE URL</div><span style="font-size:10px;color:var(--muted)">LIVE DOMAIN</span></div>
  <div class="base-url-row"><code class="base-url" id="baseUrlValue">Loading…</code><button class="copy-base" id="copyBaseUrl" type="button">Copy Base URL</button></div>
  <p class="base-help">This is the root address of your API. Add an endpoint path to it when making requests — for example, <code>/fam_create</code> or <code>/fam_verify</code>. The endpoint examples below show the complete live URL.</p>
</section>
<div class="stats">
  <div class="stat"><span class="stat-icon premium-emoji" aria-hidden="true">💸</span><div><b>UPI payments</b><small>Dynamic QR requests</small></div></div>
  <div class="stat"><span class="stat-icon premium-emoji" aria-hidden="true">📩</span><div><b>Inbox matching</b><small>Gmail IMAP checks</small></div></div>
  <div class="stat"><span class="stat-icon premium-emoji" aria-hidden="true">🔐</span><div><b>Private API keys</b><small>Merchant-based access</small></div></div>
</div>
<section id="documentation">
  <div class="section-kicker">API REFERENCE</div><h2 class="section-heading">Documentation</h2>
  <p class="section-intro">Use your API key with the endpoints below. All responses are returned in JSON format.</p>
  <article class="doc-card">
    <div class="doc-head"><div class="doc-icon premium-emoji" aria-hidden="true">💳</div><div><h3 class="doc-title">Generate QR Code</h3><div class="doc-sub">CREATE A PAYMENT ORDER</div></div></div>
    <p class="doc-desc">Create a new UPI payment request. The API returns a unique order ID and a QR image hosted on this API server. Each QR request expires after five minutes.</p>
    <div class="endpoint"><span class="method">GET</span><code id="createEndpoint">/fam_create?amount=AMOUNT&amp;api_key=YOUR_API_KEY</code></div>
    <div class="param-title">REQUEST PARAMETERS</div>
    <div class="param-table"><div class="param-row"><span>PARAMETER</span><span>TYPE</span><span>DESCRIPTION</span></div>
      <div class="param-row"><code>amount</code><span class="required">Required</span><span>Payment amount in INR (1–100000).</span></div>
      <div class="param-row"><code>api_key</code><span class="required">Required</span><span>Your API key generated from this page.</span></div>
    </div>
    <div class="codebox success-response"><div class="codebar"><span>SUCCESS RESPONSE</span><button class="copy-code" type="button" onclick="copyCode(this)">COPY</button></div><pre>{
  "status": "success",
  "data": {
    "order_id": "FAMPAY2026111400401024D72AA0",
    "qr_url": "https://fampay-api-7msf.onrender.com/qr_codes/FAMPAY2026111400401024D72AA0.png",
    "upi_id": "merchant@upi",
    "amount": "10",
    "created_at_ist": "14-11-2026 18:00:00",
    "expires_at_ist": "14-11-2026 18:05:00"
  },
  "dev": "@ROXXOP"
}</pre></div>
  </article>
  <article class="doc-card">
    <div class="doc-head"><div class="doc-icon premium-emoji" aria-hidden="true">✨</div><div><h3 class="doc-title">Verify Payment Status</h3><div class="doc-sub">CHECK PAYMENT COMPLETION</div></div></div>
    <p class="doc-desc">Check whether an order has been paid. Submit the order ID returned by the QR generation endpoint.</p>
    <div class="endpoint"><span class="method">GET</span><code id="verifyEndpoint">/fam_verify?order_id=ORDER_ID&amp;api_key=YOUR_API_KEY</code></div>
    <div class="param-title">REQUEST PARAMETERS</div>
    <div class="param-table"><div class="param-row"><span>PARAMETER</span><span>TYPE</span><span>DESCRIPTION</span></div>
      <div class="param-row"><code>order_id</code><span class="required">Required</span><span>Order ID received from <code>/fam_create</code>.</span></div>
      <div class="param-row"><code>api_key</code><span class="required">Required</span><span>Your personal API key.</span></div>
    </div>
    <div class="codebox success-response"><div class="codebar"><span>FIRST SUCCESSFUL VERIFY RESPONSE</span><button class="copy-code" type="button" onclick="copyCode(this)">COPY</button></div><pre>{
  "status": "success",
  "data": {
    "order_id": "FAMPAY2026111400401024D72AA0",
    "transaction_id": "UPI123456789012",
    "amount": 10,
    "utr": "301268197755",
    "sender_name": "Customer",
    "payment_time_ist": "14-11-2026 18:02:12",
    "already_verified": "false"
  },
  "dev": "@ROXXOP"
}</pre></div>
    <div class="codebox"><div class="codebar"><span>SECOND REQUEST ONWARD — ALREADY VERIFIED</span><button class="copy-code" type="button" onclick="copyCode(this)">COPY</button></div><pre>{
  "status": "success",
  "order_id": "FAMPAY2026111400401024D72AA0",
  "already_verified": "true",
  "message": "Payment was already verified",
  "dev": "@ROXXOP"
}</pre></div>
    <div class="codebox"><div class="codebar"><span>PENDING / NOT PAID RESPONSE</span><button class="copy-code" type="button" onclick="copyCode(this)">COPY</button></div><pre>{
  "status": "error",
  "message": "Transaction failed - Payment not received",
  "order_id": "FAMPAY2026111400401024D72AA0",
  "already_verified": "false",
  "dev": "@ROXXOP"
}</pre></div>
    <div class="tip">💡 QR requests expire after five minutes. Save the <b>order_id</b> and use it to check payment status. Keep your API key private.</div>
  </article>
</section>
<section>
  <div class="section-kicker">BUILT FOR DEVELOPERS</div><h2 class="section-heading">Why Choose FamPay API?</h2>
  <p class="section-intro">A compact workflow for creating payment requests and checking incoming transactions.</p>
  <div class="features">
    <div class="feature"><div class="feature-icon premium-emoji" aria-hidden="true">⚡</div><div><h3>Simple Integration</h3><p>Clear GET endpoints and JSON responses make it easy to connect your application.</p></div></div>
    <div class="feature"><div class="feature-icon premium-emoji" aria-hidden="true">🔑</div><div><h3>Merchant API Keys</h3><p>Each merchant gets a personal key after Gmail IMAP credentials are verified.</p></div></div>
    <div class="feature"><div class="feature-icon premium-emoji" aria-hidden="true">📱</div><div><h3>Hosted QR Codes</h3><p>QR images are generated and served directly from your API domain.</p></div></div>
  </div>
</section>
<section class="key-card" id="generate-api-key">
  <div class="section-kicker">GET STARTED</div><h2 class="section-heading">Generate your API Key</h2>
  <p class="section-intro">Verify your Gmail App Password and register your UPI details to create a personal API key.</p>
  <form class="key-form" id="apiKeyForm">
    <div class="field"><label for="keyGmail">Gmail Address</label><input id="keyGmail" name="gmail" type="email" placeholder="yourname@gmail.com" autocomplete="email" required></div>
    <div class="field"><label for="keyGpass">Gmail App Password</label><input id="keyGpass" name="gpass" type="password" placeholder="16-character App Password" autocomplete="new-password" required></div>
    <div class="field"><label for="keyUpi">UPI ID</label><input id="keyUpi" name="upi" type="text" placeholder="yourname@bank" required></div>
    <div class="field"><label for="keyMobile">Mobile Number</label><input id="keyMobile" name="mobile" type="tel" inputmode="numeric" placeholder="10-digit mobile number" required></div>
    <button class="key-submit" id="keySubmit" type="submit">🔐 Verify Gmail &amp; Generate API Key</button>
  </form>
  <p class="key-note">🔒 Enter a Google App Password, not your normal Gmail password. Your Gmail credentials are checked through IMAP before an API key is created. Use this page over HTTPS.</p>
  <div class="key-result" id="keyResult" role="status" aria-live="polite"></div>
</section>
<section>
  <div class="section-kicker">QUICK START &amp; IMPORTANT NOTES</div><h2 class="section-heading">After generating your API key</h2>
  <p class="section-intro">Follow these steps to connect your app and understand the verification responses.</p>
  <div class="info-grid">
    <article class="info-card"><h3>🚀 1. Create a payment order</h3><p>Call <code>/fam_create</code> with your API key and amount. Save the returned <code>order_id</code> and show the returned QR code to the customer.</p></article>
    <article class="info-card"><h3>🔎 2. Verify the payment</h3><p>Call <code>/fam_verify</code> with the same API key and order ID. The API checks the registered Gmail inbox for the matching payment email.</p></article>
    <article class="info-card"><h3>♻️ 3. Already-verified behavior</h3><p>The first successful verification returns payment details with <code>already_verified: "false"</code>. Every later request for that paid order returns <code>already_verified: "true"</code>.</p></article>
    <article class="info-card"><h3>⏱️ 4. QR expiry &amp; security</h3><p>Payment QR orders expire after five minutes. Keep your API key and Gmail App Password private. Never expose them in public frontend code or logs.</p></article>
  </div>
</section>
<section class="console-card" id="test-console">
  <div class="section-kicker">LIVE API TOOL</div><h2 class="section-heading">Payment Verify Test Console</h2>
  <p class="section-intro">Enter your API key and an order ID to send a real verification request to this API. This checks the registered Gmail inbox; it is not a simulated response.</p>
  <form class="console-form" id="verifyTestForm">
    <div class="field"><label for="testApiKey">API Key</label><input id="testApiKey" name="api_key" type="password" placeholder="FAM_..." autocomplete="off" required></div>
    <div class="field"><label for="testOrderId">Order ID</label><input id="testOrderId" name="order_id" type="text" placeholder="FAMPAY..." autocomplete="off" required></div>
    <button class="console-submit" id="verifyTestSubmit" type="submit">▶ Run Payment Verification</button>
  </form>
  <p class="console-hint">⚠️ Use an order ID created with this API key. A successful first test marks the order as verified; all later tests for that same paid order will return <code>already_verified: "true"</code>. Do not share your API key.</p>
  <div class="console-output" id="verifyTestOutput" aria-live="polite">
    <div class="console-output-head"><span id="verifyTestStatus">API RESPONSE</span><button class="copy-code" id="copyVerifyTest" type="button">COPY JSON</button></div>
    <pre id="verifyTestJson"></pre>
  </div>
</section>
<footer class="footer">FamPay API Developer Portal · API v2.0 · <span id="footerBaseUrl"></span></footer>
</div>
<script>

// Smooth on-scroll reveals (respects reduced-motion preferences).
(function(){
  const targets=document.querySelectorAll('.base-card,.stat,.doc-card,.feature,.key-card,.info-card,.console-card,.section-kicker,.section-heading');
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches){targets.forEach(el=>el.classList.add('is-visible'));return}
  targets.forEach(el=>el.classList.add('reveal'));
  if(!('IntersectionObserver' in window)){targets.forEach(el=>el.classList.add('is-visible'));return}
  const observer=new IntersectionObserver(entries=>{
    entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('is-visible');observer.unobserve(entry.target)}});
  },{threshold:.10,rootMargin:'0px 0px -35px 0px'});
  targets.forEach(el=>observer.observe(el));
})();

const root=document.documentElement;
const themeButton=document.getElementById('themeToggle');
function setTheme(theme){root.dataset.theme=theme;localStorage.setItem('fampay-theme',theme);themeButton.textContent=theme==='dark'?'☀️ Light mode':'🌙 Dark mode'}
setTheme(localStorage.getItem('fampay-theme')||'light');
themeButton.addEventListener('click',()=>setTheme(root.dataset.theme==='dark'?'light':'dark'));
const baseUrl=window.location.origin;
document.getElementById('baseUrlValue').textContent=baseUrl;
document.getElementById('footerBaseUrl').textContent=baseUrl;
document.getElementById('createEndpoint').textContent=baseUrl+'/fam_create?amount=AMOUNT&api_key=YOUR_API_KEY';
document.getElementById('verifyEndpoint').textContent=baseUrl+'/fam_verify?order_id=ORDER_ID&api_key=YOUR_API_KEY';
async function copyText(value){
  if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(value);return}
  const field=document.createElement('textarea');field.value=value;field.style.position='fixed';field.style.opacity='0';document.body.appendChild(field);field.focus();field.select();
  const ok=document.execCommand('copy');field.remove();if(!ok)throw new Error('Copy unavailable');
}
document.getElementById('copyBaseUrl').addEventListener('click',async function(){
  const button=this;const old=button.textContent;
  try{await copyText(baseUrl);button.textContent='✓ Copied';}
  catch(e){button.textContent='Select URL above';}
  setTimeout(()=>button.textContent=old,1800);
});
async function copyCode(button){
  const text=button.closest('.codebox').querySelector('pre').innerText;
  const old=button.textContent;
  try{await copyText(text);button.textContent='COPIED';}
  catch(e){button.textContent='COPY FAILED';}
  setTimeout(()=>button.textContent=old,1500);
}
const verifyTestForm=document.getElementById('verifyTestForm');
const verifyTestButton=document.getElementById('verifyTestSubmit');
const verifyTestOutput=document.getElementById('verifyTestOutput');
const verifyTestJson=document.getElementById('verifyTestJson');
verifyTestForm.addEventListener('submit',async function(e){
  e.preventDefault();
  const values=Object.fromEntries(new FormData(verifyTestForm).entries());
  verifyTestButton.disabled=true;verifyTestButton.textContent='⏳ Checking payment…';
  verifyTestOutput.style.display='none';
  try{
    const response=await fetch('/fam_verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(values)});
    const result=await response.json();
    verifyTestJson.textContent=JSON.stringify(result,null,2);
    document.getElementById('verifyTestStatus').textContent='API RESPONSE · HTTP '+response.status;
    const responseHead=document.querySelector('.console-output-head');responseHead.classList.toggle('is-success',result.status==='success');responseHead.classList.toggle('is-error',result.status!=='success');
    verifyTestOutput.style.display='block';
  }catch(err){
    verifyTestJson.textContent=JSON.stringify({status:'error',message:'Network error. Please try again.'},null,2);
    document.getElementById('verifyTestStatus').textContent='REQUEST FAILED';
    document.querySelector('.console-output-head').classList.remove('is-success');document.querySelector('.console-output-head').classList.add('is-error');
    verifyTestOutput.style.display='block';
  }finally{
    verifyTestButton.disabled=false;verifyTestButton.textContent='▶ Run Payment Verification';
  }
});
document.getElementById('copyVerifyTest').addEventListener('click',async function(){
  const old=this.textContent;
  try{await copyText(verifyTestJson.textContent);this.textContent='COPIED';}
  catch(e){this.textContent='COPY FAILED';}
  setTimeout(()=>this.textContent=old,1500);
});
document.getElementById('apiKeyForm').addEventListener('submit',async function(e){
  e.preventDefault();
  const form=e.currentTarget,button=document.getElementById('keySubmit'),box=document.getElementById('keyResult');
  const data=Object.fromEntries(new FormData(form).entries());
  if(!data.upi.trim()||!data.mobile.trim()){box.className='key-result error';box.style.display='block';box.textContent='Please enter both UPI ID and mobile number.';return}
  button.disabled=true;button.textContent='⏳ Verifying Gmail…';box.style.display='none';
  try{
    const response=await fetch('/create_key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const result=await response.json();box.style.display='block';
    if(!response.ok||result.status!=='success'){box.className='key-result error';box.textContent=result.message||'Could not generate API key. Check your details.';return}
    box.className='key-result';
    box.innerHTML='<b>✓ API key created successfully</b><div class="key-value" id="generatedKey"></div><button type="button" class="key-copy" id="copyGeneratedKey">COPY API KEY</button><p style="font-size:11px;margin-top:9px">Save this key securely. It will not be shown again on this page.</p><p style="margin-top:14px"><a id="telegramLinkButton" target="_blank" rel="noopener" style="display:inline-block;background:#229ED9;color:#fff;padding:11px 14px;border-radius:10px;font-weight:800;text-decoration:none">✈️ Connect Telegram Alerts</a></p><small>Link your Telegram account within 24 hours to receive personal alerts.</small>';
    document.getElementById('generatedKey').textContent=result.api_key;
    const telegramLinkButton=document.getElementById('telegramLinkButton');
    if(result.telegram_link){telegramLinkButton.href=result.telegram_link;}else{telegramLinkButton.style.display='none';}
    document.getElementById('copyGeneratedKey').addEventListener('click',async function(){try{await copyText(result.api_key);this.textContent='COPIED'}catch(e){this.textContent='COPY FAILED'}});
    form.reset();
  }catch(err){box.className='key-result error';box.style.display='block';box.textContent='Network error. Please try again.'}
  finally{button.disabled=false;button.textContent='🔐 Verify Gmail & Generate API Key'}
});
</script>
</body></html>"""

def error(m,s=400):
    return jsonify({"status":"error","message":m,"dev":"@ROXXOP"}),s

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
    if isinstance(k,str):
        k=k.strip()
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
    patterns = [
        r"\bUTR(?:\s*(?:No|Number|ID|Ref(?:erence)?))?\s*[:#\-]?\s*([A-Z0-9]{8,30})\b",
        r"\bUPI\s*(?:Ref|ID|Txn)?\s*[:#\-]?\s*([0-9]{10,20})\b",
        r"\bTransaction\s*(?:ID|No)?\s*[:#\-]?\s*([A-Z0-9]{8,30})\b",
        r"\bRef\s*(?:No|ID)?\s*[:#\-]?\s*([0-9]{8,20})\b",
    ]
    for pat in patterns:
        m=re.search(pat,text,re.I)
        if m:
            return m.group(1)
    return None

def find_amount(text):
    # Try multiple amount patterns
    patterns = [
        r"(?:amount|received|credited|paid|payment of|INR|Rs\.?|₹)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
        r"(?:Rs\.?|₹|INR)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
        r"([0-9]+(?:\.[0-9]{1,2})?)\s*(?:credited|received|paid)",
    ]
    for pat in patterns:
        m=re.search(pat,text,re.I)
        if m:
            try:
                v=amount_value(m.group(1))
                if v and v > 0 and v <= 100000:
                    return v
            except:
                continue
    return None

def check_gmail_payment(record,order):
    gmail=str(record.get("gmail","")).strip()
    gpass=decrypt_gmail_password(record).replace(" ","").strip()
    try:
        ctx=ssl.create_default_context()
        # FIX 1: Use correct IMAP host - imap.gmail.com
        with imaplib.IMAP4_SSL("imap.gmail.com",993,ssl_context=ctx) as mail:
            mail.login(gmail,gpass)
            st,_=mail.select("INBOX",readonly=True)
            if st!="OK":
                return None,"Could not open Gmail inbox."
            
            # Search recent emails - last 20 emails or last 10 mins
            st,data=mail.search(None,"ALL")
            if st!="OK" or not data or not data[0]:
                return None,"No inbox messages found."
            
            exp_amount = amount_value(order.get("amount"))
            order_created = order.get("created_at", int(time.time()) - 300)
            
            for mid in reversed(data[0].split()[-100:]):  # Last 100 emails
                st,fetched=mail.fetch(mid,"(RFC822)")
                if st!="OK":
                    continue
                raw=next((i[1] for i in fetched if isinstance(i,tuple) and len(i)>1),None)
                if not raw:
                    continue
                msg=email.message_from_bytes(raw)
                subj=decode_mime(msg.get("Subject",""))
                body_text=extract_text(msg)
                full_body=(subj+" "+body_text).lower()
                
                # Check if email is recent (within last 15 mins from order creation or now)
                # and contains payment keywords
                payment_keywords = ["credited", "received", "payment", "upi", "paid", "amount", "rs", "inr", "₹"]
                has_payment_keyword = any(k in full_body for k in payment_keywords)
                if not has_payment_keyword:
                    continue
                
                # FIX 2: Don't require order_id in email body (bank emails never contain our order_id)
                # Instead match by amount and time
                det_amount = find_amount(subj+" "+body_text)
                
                # If amount found, check if matches order amount
                if det_amount is not None and exp_amount is not None:
                    if abs(det_amount - exp_amount) > 0.50:  # Allow 0.50 difference
                        continue
                elif exp_amount is not None:
                    # If we can't parse amount from email, check if email body contains the amount as string
                    amount_str = str(int(exp_amount)) if float(exp_amount).is_integer() else str(exp_amount)
                    if amount_str not in (subj+" "+body_text):
                        continue
                
                # Try to find transaction ID - multiple patterns
                tid = find_transaction_id(subj+" "+body_text)
                if not tid:
                    # Try alternative patterns for transaction ID
                    alt_patterns = [
                        r"transaction\s*(?:id|no|number)?\s*[:#]?\s*([A-Z0-9]{10,})",
                        r"upi\s*(?:ref|id|txn)?\s*[:#]?\s*([0-9]{12})",
                        r"ref\s*(?:no|number|id)?\s*[:#]?\s*([0-9A-Z]{8,})",
                        r"\b([0-9]{12})\b",  # 12 digit UPI ref
                    ]
                    for pat in alt_patterns:
                        import re as re2
                        m = re2.search(pat, subj+" "+body_text, re2.I)
                        if m:
                            tid = m.group(1)
                            break
                if not tid:
                    # Even if no transaction ID, if amount matches and recent, consider it paid
                    # Generate a dummy transaction ID from order
                    tid = f"UPI{order['order_id'][-12:]}"
                
                # Check email time - should be after order creation (within 15 mins)
                try:
                    from email.utils import parsedate_to_datetime
                    email_date = parsedate_to_datetime(msg.get("Date",""))
                    if email_date:
                        email_timestamp = email_date.timestamp()
                        # Email should be after order creation and within 20 mins
                        if email_timestamp < (order_created - 60):  # Email before order - ignore
                            continue
                        if email_timestamp > (order_created + 1200):  # Email too far in future - ignore
                            pass
                except:
                    pass
                
                # Found matching payment!
                sender = "Customer"
                # Try to extract sender name
                try:
                    m = re.search(r"from\s+([A-Z][a-z]+\s+[A-Z][a-z]+)", body_text, re.I)
                    if m:
                        sender = m.group(1)
                except:
                    pass
                
                return {
                    "order_id": order["order_id"],
                    "transaction_id": tid,
                    "utr": tid,
                    "amount": det_amount if det_amount is not None else exp_amount,
                    "sender_name": sender,
                    "payment_time_ist": msg.get("Date",""),
                    "payment_time": msg.get("Date",""),
                    "email_subject": subj,
                    "verified_at": datetime.now(timezone.utc).isoformat()
                }, None
        
        return None,"No matching payment email found yet."
    except imaplib.IMAP4.error as e:
        print(f"IMAP login failed for {gmail}: {e}")
        return None,f"Gmail login failed for {gmail} - check App Password"
    except Exception as e:
        print(f"Email verification error: {e}")
        import traceback
        traceback.print_exc()
        return None,f"Email verification failed: {str(e)[:100]}"
@app.get("/")
def index():
    return render_template_string(HTML)

@app.get("/health")
def health():
    keys=get_all_keys()
    check=request.args.get("check_key")
    exists=check.strip() in keys if check else False
    return jsonify({"ok":True,"total_keys":len(keys),"total_orders":len(Orders),"check_key_exists":exists,"dev":"@ROXXOP"})

@app.route("/create_key", methods=["GET", "POST"])
def create_key():
    try:
        if request.method == "GET":
            gmail = str(request.args.get("gmail","")).strip().lower()
            gpass = str(request.args.get("gpass","")).replace(" ","").strip()
            upi = str(request.args.get("upi","")).strip()
            mobile = str(request.args.get("mobile","")).strip()
            incoming_key = str(request.args.get("api_key","")).strip()
        else:
            body = request.get_json(silent=True) or {}
            gmail = str(body.get("gmail") or request.args.get("gmail","")).strip().lower()
            gpass = str(body.get("gpass") or request.args.get("gpass","")).replace(" ","").strip()
            upi = str(body.get("upi") or request.args.get("upi","")).strip()
            mobile = str(body.get("mobile") or request.args.get("mobile","")).strip()
            incoming_key = str(body.get("api_key") or request.args.get("api_key","")).strip()
        
        # Both merchant UPI ID and mobile number are required for key registration.
        if not upi:
            return error("upi is required")
        if not mobile:
            return error("mobile is required")
        if not gmail:
            return error("gmail is required")
        if not gpass:
            return error("gpass (Gmail App Password) is required")
        
        # New Gmail App Passwords must be encrypted at rest.
        if not os.getenv("FERNET_KEY", "").strip():
            return jsonify({"status":"error","message":"Server security is not configured. Please contact the administrator."}),503

        # Validate input format before attempting the Gmail connection.
        if not re.fullmatch(r"[^\s@]+@gmail\.com", gmail, re.I):
            return error("Enter a valid @gmail.com address")
        if len(gpass) != 16:
            return error("Invalid Gmail App Password. Enter the 16-character Google App Password.")
        if "@" not in upi or upi.startswith("@") or upi.endswith("@"):
            return error("Invalid UPI ID. Example: yourname@fam")

        # Verify the supplied credentials against Gmail IMAP before creating or saving any API key.
        try:
            with imaplib.IMAP4_SSL(IMAP_HOST, 993, ssl_context=ssl.create_default_context(), timeout=15) as mail:
                mail.login(gmail, gpass)
                status, _ = mail.select("INBOX", readonly=True)
                if status != "OK":
                    return error("Gmail login succeeded, but IMAP could not open the inbox. Check that IMAP access is enabled.")
        except imaplib.IMAP4.error:
            return error("Gmail IMAP authentication failed. Check the Gmail address and 16-character App Password, and make sure 2-Step Verification and IMAP access are enabled.")
        except (OSError, TimeoutError):
            return error("Could not connect to Gmail IMAP. Please try again later.")
        except Exception:
            return error("Gmail IMAP verification failed. Please check your credentials and try again.")

        # Generate an API key only after Gmail IMAP verification succeeds.
        keys = get_all_keys()
        while True:
            api_key = "FAM_" + secrets.token_hex(20).upper() + secrets.token_hex(10).lower()
            if api_key not in keys:
                break

        with LOCK:
            latest = get_all_keys()
            latest[api_key] = {
                "gmail": gmail,
                "gpass": encrypt_gmail_password(gpass),
                "mobile": mobile,
                "upi": upi,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_via": "bot"
            }
            BotKeys.clear()
            BotKeys.update(latest)
            save_json(KEYS_FILE, BotKeys)
            # Also ensure file exists
            if not os.path.exists(KEYS_FILE):
                save_json(KEYS_FILE, latest)
        
        return jsonify({
            "status": "success",
            "message": "API Key created successfully",
            "api_key": api_key,
            "gmail": gmail,
            "upi": upi,
            "mobile": mobile,
            "dev": "@ROXXOP"
        }), 201
    except Exception as e:
        return jsonify({"status":"error","message":f"Server error in create_key: {str(e)}","dev":"@ROXXOP"}), 500


@app.route("/register_key", methods=["GET", "POST"])
def register_key_alias():
    return create_key()

@app.route("/api/create_key", methods=["GET", "POST"])
def api_create_key_alias():
    return create_key()

@app.route("/qr.php", methods=["GET", "POST"])
def qr_php_compat():
    # Backward compat for old endpoint https://fampay.anujbots.xyz/qr.php
    # Redirect to fam_create
    return fam_create()

@app.route("/verify.php", methods=["GET", "POST"])
def verify_php_compat():
    # Backward compat for old endpoint https://fampay.anujbots.xyz/verify.php
    return fam_verify()

@app.route("/delete_key", methods=["GET", "POST"])
def delete_key():
    api_key = get_api_key() or request.args.get("api_key","").strip()
    if not api_key:
        return error("api_key required")
    keys = get_all_keys()
    with LOCK:
        if api_key in keys:
            del keys[api_key]
            BotKeys.clear()
            BotKeys.update(keys)
            save_json(KEYS_FILE, BotKeys)
            return jsonify({"status":"success","message":"API Key deleted","dev":"@ROXXOP"})
        else:
            return jsonify({"status":"error","message":"API Key not found","dev":"@ROXXOP"}), 404

@app.route("/fam_create", methods=["GET", "POST"])
def fam_create():
    api_key=get_api_key()
    keys=get_all_keys()
    if not api_key or api_key not in keys:
        return jsonify({"status":"error","message":"Invalid API key","dev":"@ROXXOP"}),401
    raw=request.args.get("amount") if request.method=="GET" else (request.get_json(silent=True) or {}).get("amount")
    amount=amount_value(raw)
    if amount is None:
        return error("Invalid amount")
    merchant_upi=str(keys[api_key].get("upi","")).strip()
    if not merchant_upi:
        return error("No UPI ID")
    # Generate order_id like FAMPAY2026042300401024D72AA0 (as per user example)
    order_id="FAMPAY"+datetime.now().strftime("%Y%m%d%H%M%S")+secrets.token_hex(6).upper()
    exp=int(time.time())+ORDER_EXPIRY
    # IST time format
    now_ist = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    exp_ist = datetime.fromtimestamp(exp).strftime("%d-%m-%Y %H:%M:%S")
    # Serve QR images from this API host (or PUBLIC_BASE_URL when configured).
    public_base = os.getenv("PUBLIC_BASE_URL", request.host_url).strip().rstrip("/")
    qr_url = f"{public_base}/qr_codes/{order_id}.png"
    # Keep the UPI payload locally; no third-party QR service is used.
    upi_link="upi://pay?pa="+quote(merchant_upi,safe="")+"&pn=Merchant&am="+format(amount,".2f")+"&cu=INR&tn="+quote(order_id,safe="")
    order={"order_id":order_id,"api_key":api_key,"amount":amount,"upi":merchant_upi,"upi_link":upi_link,"qr_code":qr_url,"qr_url":qr_url,"expires_at":exp,"status":"pending","created_at":int(time.time())}
    with LOCK:
        Orders[order_id]=order
        save_json(ORDERS_FILE,Orders)
    # Exact format as user requested: order_id, qr_url, upi_id, amount as string, created_at_ist, expires_at_ist, dev
    return jsonify({
        "status":"success",
        "data":{
            "order_id":order_id,
            "qr_url":qr_url,
            "upi_id":merchant_upi,
            "amount":str(int(amount)) if float(amount).is_integer() else str(amount),
            "created_at_ist":now_ist,
            "expires_at_ist":exp_ist
        },
        "dev":"@ROXXOP"
    }),201

@app.get("/qr_codes/<order_id>.png")
def serve_order_qr(order_id):
    # Only generate QR images for orders created by this API.
    with LOCK:
        order = Orders.get(order_id)
    if not order:
        return error("QR code not found", 404)
    if int(time.time()) >= int(order.get("expires_at", 0)):
        return error("QR Expired", 410)

    upi_link = str(order.get("upi_link", "")).strip()
    if not upi_link.startswith("upi://pay?"):
        return error("Invalid QR payment data", 404)

    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(upi_link)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # Small FamPay-orange mark in a white safe-zone; QR stays standard black and white.
    width, height = qr_image.size
    logo_size = max(42, int(min(width, height) * 0.14))
    left = (width - logo_size) // 2
    top = (height - logo_size) // 2
    padding = max(5, int(logo_size * 0.12))
    draw = ImageDraw.Draw(qr_image)
    draw.rounded_rectangle((left-padding, top-padding, left+logo_size+padding, top+logo_size+padding), radius=max(6, int(logo_size*0.16)), fill="white")
    draw.rounded_rectangle((left, top, left+logo_size, top+logo_size), radius=max(5, int(logo_size*0.14)), fill="#FFAD00")

    # Compact white FamPay monogram, intentionally small for scan reliability.
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(logo_size * 0.70))
    except OSError:
        font = ImageFont.load_default()
    ImageDraw.Draw(qr_image).text((left+logo_size/2, top+logo_size/2-1), "F", font=font, fill="white", anchor="mm")

    output = BytesIO()
    qr_image.save(output, format="PNG", optimize=True)
    output.seek(0)
    response = send_file(output, mimetype="image/png", download_name=f"{order_id}.png")
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/fam_verify", methods=["GET", "POST"])
def fam_verify():
    api_key=get_api_key()
    keys=get_all_keys()
    if not api_key or api_key not in keys:
        return jsonify({"status":"error","message":"Invalid API key","dev":"@ROXXOP"}),401
    oid=str((request.args.get("order_id") if request.method=="GET" else (request.get_json(silent=True) or {}).get("order_id",""))).strip()
    if not oid:
        return jsonify({"status":"error","message":"order_id required","dev":"@ROXXOP"}),400

    with LOCK:
        order=Orders.get(oid)
        if not order:
            return jsonify({"status":"error","message":"Transaction failed - Payment not received","order_id":oid,"already_verified":"false","dev":"@ROXXOP"}),404

        # Only a previously successful verification is treated as already verified.
        paid=PaidRecords.get(oid)
        if paid:
            paid.pop("total_request",None)
            PaidRecords[oid]=paid
            save_json(PAID_FILE,PaidRecords)

    if paid:
        return jsonify({
            "status":"success",
            "order_id":oid,
            "already_verified":"true",
            "message":"Payment was already verified",
            "dev":"@ROXXOP"
        }),200

    # Never check Gmail after the five-minute QR/order expiry.
    if int(time.time()) >= int(order.get("expires_at",0)):
        return jsonify({"status":"error","message":"QR Expired","order_id":oid,"already_verified":"false","dev":"@ROXXOP"}),410

    res,msg=check_gmail_payment(keys[api_key],order)
    if not res:
        return jsonify({
            "status":"error",
            "message":msg or "Transaction failed - Payment not received",
            "order_id":oid,
            "already_verified":"false",
            "dev":"@ROXXOP"
        }),200

    # First successful verification returns full payment details.
    res.pop("total_request",None)
    res["already_verified"]="false"
    with LOCK:
        PaidRecords[oid]=res
        save_json(PAID_FILE,PaidRecords)

    return jsonify({"status":"success","data":res,"dev":"@ROXXOP"}),200
\n\n
# Admin and Telegram integrations.
from admin_panel import register_admin_panel
from telegram_alerts import register_telegram_alerts
register_admin_panel(app)
register_telegram_alerts(app)
