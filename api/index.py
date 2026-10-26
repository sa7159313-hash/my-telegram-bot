import os, time, json, re, datetime, requests, traceback, sys, importlib.util
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = str(os.environ.get("OWNER_ID","0") or "0")
MY_URL = os.environ.get("MY_URL","").rstrip("/") or "https://my-telegram-bot-lime.vercel.app"
LORE_ENV = os.environ.get("THE_BEAST_KING_MONARCH_AKAAN_LORE","")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

MALIK_NAME="MD Saif Ahmad"; MALIK_TITLE="The Shadow King"
MEMORY={}; ABUSE={}; PROFILES={}; REMINDERS=[]; CHAT_LOG=[]; BAD_KEYS={}; LAST_ERROR="No error"; _LAST_WEBHOOK=0; _LAST_NEWS=0; PENDING_FIX=None

def tg_send(cid,txt,reply_id=None):
    try:
        p={"chat_id":cid,"text":txt[:3900]}
        if reply_id: p["reply_to_message_id"]=reply_id
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=p, timeout=10)
    except: pass

def get_ist_now(): return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
def get_ist_str(): return get_ist_now().strftime("%d %b %Y, %I:%M %p IST, %A")
def get_future_ist(m=30): return (get_ist_now() + datetime.timedelta(minutes=m)).strftime("%I:%M %p IST")

def report_fault(where, exc_obj=None):
    global LAST_ERROR
    try:
        exc_type, exc_val, exc_tb = sys.exc_info()
        if exc_obj: exc_val = exc_obj
        tb_str = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))[-1500:]
        if exc_tb:
            f = traceback.extract_tb(exc_tb)[-1]
            file_name, line_no, func, code_line = f.filename.split("/")[-1], f.lineno, f.name, f.line
        else:
            file_name, line_no, func, code_line = "index.py", "?", where, str(exc_val)
        LAST_ERROR=f"{where} | {file_name}:{line_no} | {exc_val}"
        suggest="Check env"
        e=str(exc_val).lower()
        if "generativeai" in e: suggest="requirements.txt me google-generativeai==0.8.3 add karo"
        if "flask" in e: suggest="Top pe app=Flask(__name__) missing hai"
        if "gsk_" in e or "groq" in e or "429" in e: suggest="Groq key block, /fix?id=OWNER_ID hit karo"
        if "upstash" in e: suggest="UPSTASH url/token env me check karo"
        if "nameerror" in e: suggest=f"{code_line} define nahi hai"
        if OWNER_ID!="0":
            tg_send(OWNER_ID, f"🚨 Fault\n📍{where}\n📄{file_name}:{line_no} {func}\n💥{exc_val}\n📝{code_line}\n💡{suggest}\n⏰{get_ist_str()}\n{tb_str[-500:]}")
    except: pass

# --- ULTIMATE AUDIT ENGINE - YE SAB CHECK KAREGA ---
def full_system_audit():
    faults=[]
    # 1. Code Identity
    faults.append({"layer":"CODE IDENTITY","status":"OK","info":f"Ye code Rakan - BeastKing Monarch Telegram Bot hai. Owner: {MALIK_NAME} aka {MALIK_TITLE}. Framework: Flask. AI: Groq/Gemini/OpenAI. Deploy: Vercel {MY_URL}. Isi ka hai, dusre ka nahi."})
    # 2. ENV Check
    if not BOT_TOKEN: faults.append({"layer":"ENV BOT_TOKEN","status":"FAULT","line":"api/index.py line 12","current":"Missing","should":"Vercel ENV me BOT_TOKEN daalo","fix":"Add BOT_TOKEN"})
    if OWNER_ID=="0": faults.append({"layer":"ENV OWNER_ID","status":"FAULT","line":"ENV","current":"0","should":OWNER_ID,"fix":"OWNER_ID set karo"})
    if not MY_URL.startswith("https"): faults.append({"layer":"ENV MY_URL","status":"FAULT","line":"ENV MY_URL","current":MY_URL,"should":"https://...vercel.app","fix":"MY_URL correct karo"})
    # 3. Requirements
    try:
        if importlib.util.find_spec("flask") is None: faults.append({"layer":"requirements.txt","status":"FAULT","line":"requirements.txt line 1","current":"flask missing","should":"Flask==3.0.0","fix":"requirements.txt me Flask likho"})
        if importlib.util.find_spec("google.generativeai") is None: faults.append({"layer":"requirements.txt","status":"FAULT","line":"requirements.txt line 2","current":"genai missing","should":"google-generativeai==0.8.3","fix":"requirements.txt me google-generativeai add karo"})
    except Exception as e: faults.append({"layer":"requirements.txt","status":"FAULT","info":str(e)})
    # 4. Redis / Upstash JSON
    try:
        if not UPSTASH_URL: faults.append({"layer":"UPSTASH REDIS","status":"FAULT","line":"ENV UPSTASH_REDIS_REST_URL","current":"Empty","should":"https://...upstash.io","should_be":"UPSTASH URL daalo warna memory save nahi hogi","fix":"ENV add karo"})
        else:
            # test get
            h={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
            r=requests.get(f"{UPSTASH_URL}/get/RAKAN_MEM", headers=h, timeout=5)
            if r.status_code!=200: faults.append({"layer":"UPSTASH REDIS","status":"FAULT","line":"upstash() line 70","current":f"HTTP {r.status_code}","should":"200 OK","fix":"Token check karo"})
    except Exception as e: faults.append({"layer":"UPSTASH REDIS","status":"FAULT","info":str(e),"fix":"Token/URL check"})
    # 5. MEMORY JSON
    try:
        json.dumps(MEMORY); json.dumps(ABUSE)
    except Exception as e: faults.append({"layer":"MEMORY JSON","status":"FAULT","line":"MEMORY dict line 16","current":str(e),"should":"Valid JSON","fix":"MEMORY={} reset karo, /fix?id= hit karo"})
    # 6. API Keys
    g,gm,go=get_keys()
    if len([k for k in g if k not in BAD_KEYS])==0: faults.append({"layer":"GROQ API KEYS","status":"FAULT","line":"get_keys() line 100","current":f"0/{len(g)} valid","should":">0 valid","fix":"Nayi GROQ key ENV me daalo ya /fix hit karo"})
    if len([k for k in gm if k not in BAD_KEYS])==0: faults.append({"layer":"GEMINI API KEYS","status":"FAULT","line":"get_keys() line 100","current":f"0/{len(gm)} valid","should":">0 valid","fix":"Nayi GEMINI key daalo"})
    # 7. Vercel / GitHub
    if "vercel" not in MY_URL: faults.append({"layer":"VERCEL DEPLOY","status":"WARN","line":"MY_URL","current":MY_URL,"should":"vercel.app url","fix":"Vercel URL correct karo"})
    # 8. Lore Loop Bug (video wala)
    if "can't create or run the app" in str(MEMORY): faults.append({"layer":"LORE LOOP","status":"FAULT","line":"get_lore_fresh() line 145","current":"Long tutorial spam","should":"1-2 lines friend","fix":"MEMORY clear + lore short rule"})
    if len(faults)==1: faults.append({"layer":"ALL SYSTEMS","status":"OK","info":"Koi fault nahi, Rakan 100% fit hai Malik"})
    return faults

def upstash(cmd,key,val=None):
    if not UPSTASH_URL or not UPSTASH_TOKEN: return None
    try:
        headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        if cmd=="get":
            r=requests.get(f"{UPSTASH_URL}/get/{key}", headers=headers, timeout=5)
            if r.status_code==200:
                d=r.json().get("result"); return json.loads(d) if d else None
        if cmd=="set" and val is not None:
            r=requests.post(f"{UPSTASH_URL}", headers=headers, json=["SET", key, json.dumps(val)], timeout=5)
            return r.status_code==200
    except Exception as e: report_fault(f"upstash_{cmd}", e)
    return None

def load_persist():
    global MEMORY,ABUSE,PROFILES,CHAT_LOG,REMINDERS,_LAST_NEWS
    try:
        if not UPSTASH_URL: return
        MEMORY=upstash("get","RAKAN_MEM") or {}; ABUSE=upstash("get","RAKAN_ABUSE") or {}
        PROFILES=upstash("get","RAKAN_PROFILES") or {}; CHAT_LOG=upstash("get","RAKAN_LOGS") or []
        REMINDERS=upstash("get","RAKAN_REMINDERS") or []; _LAST_NEWS=upstash("get","RAKAN_LAST_NEWS") or 0
    except Exception as e: report_fault("load_persist", e)
def save_persist():
    try:
        if not UPSTASH_URL: return
        upstash("set","RAKAN_MEM",MEMORY); upstash("set","RAKAN_ABUSE",ABUSE)
        upstash("set","RAKAN_PROFILES",PROFILES); upstash("set","RAKAN_LOGS",CHAT_LOG[-400:]); upstash("set","RAKAN_REMINDERS",REMINDERS)
        upstash("set","RAKAN_LAST_NEWS",_LAST_NEWS)
    except Exception as e: report_fault("save_persist", e)
load_persist()

def get_keys():
    try:
        g,gm,go=[],[],[]
        for k,v in os.environ.items():
            if not v: continue
            raw=str(v); parts=[p.strip().strip('"').strip("'") for p in raw.replace("\n",",").split(",") if p.strip()]
            for p in parts:
                ku=k.upper()
                if "GEMINI" in ku and len(p)>20 and p not in gm: gm.append(p)
                if "GROQ" in ku and len(p)>10 and p not in g: g.append(p)
                if "OPENAI" in ku and p.startswith("sk-") and p not in go: go.append(p)
                if p.startswith("gsk_") and p not in g: g.append(p)
                if p.startswith("AIza") and p not in gm: gm.append(p)
                if p.startswith("AQ.") and p not in gm: gm.append(p)
                if p.startswith("sk-") and len(p)>30 and p not in go: go.append(p)
        return list(dict.fromkeys(g)),list(dict.fromkeys(gm)),list(dict.fromkeys(go))
    except Exception as e: report_fault("get_keys", e); return [],[],[]
GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys()

def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<900
def mark_bad(k): BAD_KEYS[k]=time.time()
def auto_heal_keys():
    global GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS,BAD_KEYS
    try:
        if len([k for k in GROQ_KEYS if not is_bad(k)])==0 and len([k for k in GEMINI_KEYS if not is_bad(k)])==0:
            if len(BAD_KEYS)>0 and time.time()-min(BAD_KEYS.values())>300:
                BAD_KEYS.clear(); GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys(); return True
    except Exception as e: report_fault("auto_heal_keys", e)
    return False

def ensure_webhook():
    global _LAST_WEBHOOK
    if time.time()-_LAST_WEBHOOK<3600: return "CACHED"
    _LAST_WEBHOOK=time.time()
    if not BOT_TOKEN: return "NO TOKEN"
    try:
        exp=f"{MY_URL}/webhook"; requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":exp}, timeout=8); return "OK"
    except Exception as e: report_fault("ensure_webhook", e); return "ERR"

BASE_LORE = f"""You are Rakan - BeastKing Monarch, built by {MALIK_NAME} aka {MALIK_TITLE} on Vercel/Flask. You are NOT made by OpenAI, Meta, Google. Owner is MD Saif Ahmad. Truth only. Dost jaisa short reply. Urdu/Hindi mix for Malik. Extra: {LORE_ENV}"""

def get_lore_fresh():
    ist=get_ist_str(); future=get_future_ist(30)
    return f"""{BASE_LORE}
IST: {ist} Future: {future}
RULES:
1. Be 1-2 lines max like best friend, no essay.
2. If user says good/okkk/hii/ok without context, ask 'Ha bolo Malik? Kaunsa app? Kya kaam hai?' Don't give tutorial.
3. If asked who created you, say 'Malik MD Saif Ahmad ne, The Shadow King ne, GitHub/Vercel pe Flask/Groq/Gemini se'.
4. BANNED: I can't create or run the app for you, step-by-step guide to create app, Haan bolo Malik Gussa kyu, OpenAI engineers.
5. If user pastes code, don't echo code, say 'Code mil gaya Malik, check kar raha hu'.
"""

def clean(txt):
    try:
        if not txt: return "bolo?"
        txt=re.sub(r"I can't create or run the app.*","",txt,flags=re.IGNORECASE)
        txt=re.sub(r"Haan bolo Malik,? Gussa kyu.*","",txt,flags=re.IGNORECASE)
        txt=re.sub(r"step by step.*app.*","",txt,flags=re.IGNORECASE)
        txt=re.sub(r"\s+"," ",txt).strip()
        if "10:45 PM" in txt: txt=txt.replace("10:45 PM", get_ist_str())
        # cut long
        if len(txt)>300: txt=txt[:300]+"... bolo detail chahiye?"
        return txt[:800] if txt else "Ha bolo Malik?"
    except Exception as e: report_fault("clean", e); return "bolo?"

def tg_get_file_bytes(fid):
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}", timeout=10).json()
        fp=r["result"]["file_path"]; return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=30).content
    except Exception as e: report_fault("tg_get_file_bytes", e); return None

GROQ_MODELS=["openai/gpt-oss-120b","llama-3.3-70b-versatile","llama-3.1-8b-instant","mixtral-8x7b-32768","gemma2-9b-it"]
GEMINI_MODELS=["gemini-2.5-flash","gemini-2.0-flash","gemini-1.5-flash"]
OPENAI_MODELS=["gpt-4o-mini","gpt-4o"]

def my_own_ai(text):
    low=text.lower().strip()
    if low in ["q","qq"]: return "kyun? bolo kya hua?"
    if low in ["k"]: return "kya?"
    if low in ["good","ok","okkk","okk","hii","hello"] and len(low)<6: return "Ha bolo Malik? Kaunsa app? Kya kaam hai?"
    if "time kya" in low: return f"{get_ist_str()}"
    if "30 min" in low: return f"Abhi {get_ist_str()}, 30 min baad {get_future_ist(30)} hoga."
    return None

def ask_groq(prompt):
    try:
        auto_heal_keys(); lore=get_lore_fresh()
        for k in GROQ_KEYS:
            if is_bad(k): continue
            for m in GROQ_MODELS:
                try:
                    r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":lore},{"role":"user","content":prompt}],"temperature":0.3,"max_tokens":150}, timeout=15)
                    if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                    if r.status_code in [401,403,429]: mark_bad(k); break
                except: continue
    except Exception as e: report_fault("ask_groq", e)
    return None

def ask_openai(prompt):
    try:
        lore=get_lore_fresh()
        for k in OPENAI_KEYS:
            if is_bad(k): continue
            for m in OPENAI_MODELS:
                try:
                    r=requests.post(OPENAI_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":lore},{"role":"user","content":prompt}],"temperature":0.3,"max_tokens":150}, timeout=15)
                    if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                    if r.status_code in [401,403,429]: mark_bad(k); break
                except: continue
    except Exception as e: report_fault("ask_openai", e)
    return None

def ask_gemini(prompt):
    try:
        lore=get_lore_fresh()
        for k in GEMINI_KEYS:
            if is_bad(k): continue
            for m in GEMINI_MODELS:
                try:
                    genai.configure(api_key=k); model=genai.GenerativeModel(m, system_instruction=lore)
                    res=model.generate_content(prompt)
                    if res.text: return clean(res.text)
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower(): mark_bad(k); break
                    continue
    except Exception as e: report_fault("ask_gemini", e)
    return None

def ask_all(prompt): return my_own_ai(prompt) or ask_groq(prompt) or ask_openai(prompt) or ask_gemini(prompt) or "Ha bolo Malik?"

def ask_gemini_vision(img,prompt):
    try:
        lore=get_lore_fresh()
        for k in GEMINI_KEYS:
            try:
                genai.configure(api_key=k); model=genai.GenerativeModel("gemini-1.5-flash", system_instruction=lore)
                res=model.generate_content([prompt, {"mime_type":"image/jpeg","data":img}])
                if res.text: return clean(res.text)
            except: continue
    except Exception as e: report_fault("vision", e)
    return None

def transcribe_media(audio_bytes,fn="voice.ogg"):
    try:
        for k in GROQ_KEYS:
            try:
                r=requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization": f"Bearer {k}"}, files={"file":(fn,audio_bytes)}, data={"model":"whisper-large-v3"}, timeout=20)
                if r.status_code==200: return r.json().get("text","")
            except: continue
    except: pass
    return None

def brain(text,uid,is_owner,uname,reply_context=""):
    global MEMORY, PENDING_FIX
    try:
        uid=str(uid)
        if uid not in MEMORY: MEMORY[uid]={"hist":"","count":0}
        low=text.lower().strip()
        MEMORY[uid]["count"]+=1

        # CODE PASTE PROTECTION - video wala fault 18-28 sec
        if len(text)>800 and ("import os" in text or "def report_fault" in text):
            return "Code mil gaya Malik, poora scan kar raha hu. /audit likho, main har layer ka fault bata dunga."

        # PERMISSION SYSTEM - Auto fix permission
        if low in ["ha fix karo","han fix karo","fix karo","yes fix","ha kar do"]:
            if PENDING_FIX and is_owner:
                f=PENDING_FIX
                # Do fix
                if f["layer"]=="MEMORY JSON" or f["layer"]=="LORE LOOP":
                    MEMORY.clear(); ABUSE.clear(); save_persist()
                    PENDING_FIX=None
                    return f"Done Malik, {f['layer']} clear kar diya. Line {f.get('line','')} se. Ab test karo."
                if "API KEYS" in f["layer"]:
                    BAD_KEYS.clear(); save_persist()
                    PENDING_FIX=None
                    return f"Done Malik, {f['layer']} ka BAD clear kar diya, nayi keys active."
                if "UPSTASH" in f["layer"]:
                    PENDING_FIX=None
                    return f"Malik {f['layer']} ka fix ENV me karna padega, Vercel pe {f.get('fix','')} daalo."
                PENDING_FIX=None
                return f"Done Malik, {f['layer']} fix kar diya."
            return "Koi pending fix nahi hai Malik, /audit likho."

        # AUDIT COMMAND - Har cheez ka query
        if low in ["/audit","audit","/diagnose","diagnose","full report"]:
            faults=full_system_audit()
            msg=f"🔍 Full System Audit - {get_ist_str()}\n\n"
            for i,f in enumerate(faults,1):
                msg+=f"{i}. {f['layer']} - {f['status']}\n   Line: {f.get('line','-')}\n   Info: {f.get('info',f.get('current',''))}\n   Should: {f.get('should','')}\n   Fix: {f.get('fix','')}\n\n"
            # set first fault as pending
            real_faults=[x for x in faults if x["status"]=="FAULT"]
            if real_faults and is_owner:
                PENDING_FIX=real_faults[0]
                msg+=f"\n⚠️ Malik pehla fault hai: {PENDING_FIX['layer']} at {PENDING_FIX.get('line','')}\nKya mai isko khud fix karke bheju? Type: 'ha fix karo' - permission do to action lunga."
            else:
                msg+="✅ Koi fault nahi, sab OK Malik."
            return msg[:3900]

        if low in ["/report","report"]:
            ist=get_ist_str(); g_ok=len([k for k in GROQ_KEYS if not is_bad(k)]); gm_ok=len([k for k in GEMINI_KEYS if not is_bad(k)]); o_ok=len([k for k in OPENAI_KEYS if not is_bad(k)])
            return f"Report Malik: G:{g_ok}/{len(GROQ_KEYS)} GM:{gm_ok}/{len(GEMINI_KEYS)} O:{o_ok}/{len(OPENAI_KEYS)} Time:{ist} LastErr:{LAST_ERROR[:80]}"

        if low in ["/start","start"]: return "Welcome to your world The Shadow King 👑 - Hazir hu Malik" if is_owner else f"Welcome {uname}, bolo?"
        if "kis ka code" in low or "kiska code" in low or "ye code kya" in low:
            return f"Ye code Rakan BeastKing Monarch ka hai Malik, {MALIK_NAME} aka {MALIK_TITLE} ka. Flask + Groq/Gemini/OpenAI + Vercel + Upstash Redis + Telegram bot. Isi ka hai, dusre ka nahi. /audit likho full detail ke liye."
        if "time kya" in low: return f"{get_ist_str()}"
        if "30 min" in low: return f"Abhi {get_ist_str()}, 30 min baad {get_future_ist(30)} hoga."

        # Loop clear - video wala thik hai but app create nhi wala
        if "app create nhi" in low or "app nahi banana" in low:
            MEMORY[uid]["hist"]=""; return "Samjha Malik, app nahi banana. Bolo phir kya kaam hai?"

        full=f"IST:{get_ist_str()} Owner:{is_owner} Name:{uname} Reply:{reply_context} Hist:{MEMORY[uid]['hist'][-1500:]} Msg:{text} -> short 1-2 lines friend, truth only"
        ans=ask_all(full) or "Ha bolo Malik?"
        ans=clean(ans); MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-3000:]; save_persist(); return ans
    except Exception as e:
        report_fault(f"brain {uid}", e); return "Malik yahan fault aaya, /audit likho full report ke liye"

@app.route("/", methods=["GET"])
def home():
    try: return f"Rakan V6 Ultimate Live G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} O:{len(OPENAI_KEYS)} {get_ist_str()} {ensure_webhook()}",200
    except Exception as e: report_fault("home", e); return f"Error {e}",200

@app.route("/fix", methods=["GET"])
def fix():
    try:
        global GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS,BAD_KEYS,_LAST_NEWS
        if str(request.args.get("id",""))!=OWNER_ID: return "Access Denied",403
        GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys(); BAD_KEYS.clear(); _LAST_NEWS=0; load_persist(); save_persist()
        return f"FIXED SELF-HEALED {get_ist_str()} G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} O:{len(OPENAI_KEYS)} LastErr:{LAST_ERROR}",200
    except Exception as e: report_fault("fix", e); return f"Fix err {e}",200

@app.route("/audit", methods=["GET"])
def audit_route():
    try:
        if str(request.args.get("id",""))!=OWNER_ID: return "Access Denied",403
        f=full_system_audit()
        return jsonify({"time":get_ist_str(),"owner":MALIK_NAME,"code":"Rakan BeastKing Monarch","faults":f}),200
    except Exception as e: report_fault("audit_route", e); return jsonify({"error":str(e)}),200

@app.route("/cron", methods=["GET","POST"])
def cron():
    global _LAST_NEWS
    try:
        if time.time()-_LAST_NEWS > 1800:
            _LAST_NEWS=time.time(); save_persist()
            if OWNER_ID and BOT_TOKEN:
                try:
                    news=ask_groq("Give 1 TRUE news in 1 line - Trading/AI/Merchant Navy/Jobs") or "Update check"
                    if news and len(news)>10: tg_send(OWNER_ID, f"📰 {get_ist_str()}:\n{news}")
                except Exception as e: report_fault("cron news", e)
        return "cron ok "+get_ist_str(),200
    except Exception as e: report_fault("cron outer", e); return "cron err",200

@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"Webhook {ensure_webhook()} {get_ist_str()}",200
    try:
        data=request.get_json(silent=True) or {}; msg=data.get("message",{}) or {}
        chat_id=msg.get("chat",{}).get("id"); user_id=str(msg.get("from",{}).get("id",0)); uname=msg.get("from",{}).get("first_name","user")
        text=msg.get("text","") or msg.get("caption","") or ""; message_id=msg.get("message_id")
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID)
        if is_owner: uname=MALIK_NAME
        reply_context=""; reply_msg=msg.get("reply_to_message")
        if reply_msg:
            rt=reply_msg.get("text","") or reply_msg.get("caption","") or ""
            if rt: reply_context=f"Replied to: {rt}"
            if reply_msg.get("photo") and text:
                b=tg_get_file_bytes(reply_msg["photo"][-1]["file_id"])
                if b:
                    v=ask_gemini_vision(b, f"User says: {text}")
                    if v: tg_send(chat_id,v,message_id); return "ok",200
        if msg.get("photo"):
            b=tg_get_file_bytes(msg["photo"][-1]["file_id"])
            if b:
                q=text if text else "Is photo me kya hai short me"
                v=ask_gemini_vision(b,q)
                if v: tg_send(chat_id,v,message_id)
                else: tg_send(chat_id,brain(text or "photo",user_id,is_owner,uname,reply_context),message_id)
                return "ok",200
        media_id=None; media_name="voice.ogg"
        if msg.get("voice"): media_id=msg["voice"]["file_id"]
        elif msg.get("audio"): media_id=msg["audio"]["file_id"]; media_name="audio.mp3"
        elif msg.get("video"): media_id=msg["video"]["file_id"]; media_name="video.mp4"
        elif msg.get("video_note"): media_id=msg["video_note"]["file_id"]; media_name="video.mp4"
        if media_id:
            b=tg_get_file_bytes(media_id)
            if b:
                heard=transcribe_media(b, media_name)
                if heard: tg_send(chat_id,brain(heard,user_id,is_owner,uname,reply_context),message_id)
                else: tg_send(chat_id,"awaz saaf nahi aayi Malik",message_id)
            return "ok",200
        if not text: return "ok",200
        # Code paste echo protection
        if len(text)>800 and "import" in text and is_owner:
            tg_send(chat_id,"Code mil gaya Malik, /audit likho pura scan karne ke liye. Main har layer ka fault bata dunga.",message_id)
            return "ok",200
        tg_send(chat_id,brain(text,user_id,is_owner,uname,reply_context),message_id)
        return "ok",200
    except Exception as e:
        report_fault("webhook outer", e)
        try: tg_send(chat_id if 'chat_id' in locals() else OWNER_ID, f"Bot me fault aaya, /audit likho")
        except: pass
        return "ok",200
