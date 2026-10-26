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
        if "flask" in e: suggest="app=Flask(__name__) check karo"
        if "gsk_" in e or "groq" in e or "429" in e: suggest="Groq key block, /fix?id=OWNER_ID"
        if "upstash" in e: suggest="UPSTASH url/token check"
        if OWNER_ID!="0":
            tg_send(OWNER_ID, f"🚨 Fault\n📍{where}\n📄{file_name}:{line_no}\n💥{exc_val}\n💡{suggest}\n⏰{get_ist_str()}")
    except: pass

def full_system_audit():
    faults=[]
    faults.append({"layer":"CODE IDENTITY","status":"OK","info":f"Rakan BeastKing Monarch Bot. Owner {MALIK_NAME} aka {MALIK_TITLE}. Flask/Groq/Gemini/OpenAI/Vercel/Telegram. Isi ka hai."})
    if not BOT_TOKEN: faults.append({"layer":"ENV BOT_TOKEN","status":"FAULT","line":"ENV","current":"Missing","fix":"Vercel me BOT_TOKEN daalo"})
    if OWNER_ID=="0": faults.append({"layer":"ENV OWNER_ID","status":"FAULT","line":"ENV","fix":"OWNER_ID set karo"})
    try:
        if importlib.util.find_spec("flask") is None: faults.append({"layer":"requirements.txt","status":"FAULT","line":"requirements.txt:1","fix":"Flask==3.0.0"})
        if importlib.util.find_spec("google.generativeai") is None: faults.append({"layer":"requirements.txt","status":"FAULT","line":"requirements.txt:2","fix":"google-generativeai==0.8.3"})
    except Exception as e: faults.append({"layer":"requirements","status":"FAULT","info":str(e)})
    if not UPSTASH_URL: faults.append({"layer":"UPSTASH REDIS","status":"WARN","line":"ENV","fix":"UPSTASH URL daalo warna memory save nahi hogi"})
    try: json.dumps(MEMORY)
    except: faults.append({"layer":"MEMORY JSON","status":"FAULT","line":"MEMORY dict","fix":"MEMORY clear /fix hit karo"})
    g,gm,go=get_keys()
    if len([k for k in g if k not in BAD_KEYS])==0: faults.append({"layer":"GROQ KEYS","status":"FAULT","line":"get_keys()","current":f"0/{len(g)}","fix":"Nayi GROQ key daalo"})
    if len([k for k in gm if k not in BAD_KEYS])==0: faults.append({"layer":"GEMINI KEYS","status":"FAULT","line":"get_keys()","fix":"Nayi GEMINI key"})
    if "can't create or run" in str(MEMORY): faults.append({"layer":"LORE LOOP","status":"FAULT","line":"MEMORY hist","fix":"MEMORY clear"})
    if len([f for f in faults if f["status"]=="FAULT"])==0: faults.append({"layer":"ALL","status":"OK","info":"100% fit"})
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

# SHORT LORE - + wala fault khatam
BASE_LORE = f"You are Rakan, BeastKing Monarch. Creator is {MALIK_NAME} aka {MALIK_TITLE}. You are made by Malik on Vercel Flask Groq Gemini. You are NOT made by OpenAI. Extra lore: {LORE_ENV}"

def get_lore_fresh():
    ist=get_ist_str(); future=get_future_ist(30)
    return f"""{BASE_LORE}
IST:{ist} Future:{future}
RULES: 1) Reply 1-2 lines short like friend, Hindi/Urdu mix. 2) If good/hii/ok with no context, ask 'Ha bolo? Kaunsa kaam?' No tutorial. 3) Who made you? Answer 'Malik MD Saif Ahmad ne, The Shadow King ne'. 4) Never say 'I can't create app' or 'OpenAI engineers' or long essay. 5) If code pasted, say 'Code mil gaya Malik' only."""

def clean(txt):
    try:
        if not txt: return "bolo?"
        txt=re.sub(r"I can't create or run the app.*","",txt,flags=re.IGNORECASE)
        txt=re.sub(r"Haan bolo Malik,? Gussa kyu.*","",txt,flags=re.IGNORECASE)
        txt=re.sub(r"\s+"," ",txt).strip()
        if "10:45 PM" in txt: txt=txt.replace("10:45 PM", get_ist_str())
        if len(txt)>700: txt=txt[:700]  # 300 se 700 kiya - cut fix
        return txt if txt else "Ha bolo Malik?"
    except: return "bolo?"

def tg_get_file_bytes(fid):
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}", timeout=10).json()
        fp=r["result"]["file_path"]; return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=30).content
    except: return None

GROQ_MODELS=["openai/gpt-oss-120b","llama-3.3-70b-versatile","llama-3.1-8b-instant","gemma2-9b-it"]
GEMINI_MODELS=["gemini-2.5-flash","gemini-2.0-flash","gemini-1.5-flash"]
OPENAI_MODELS=["gpt-4o-mini"]

def my_own_ai(text):
    low=text.lower().strip()
    if low in ["q","qq"]: return "kyun? bolo kya hua?"
    if low in ["k"]: return "kya?"
    if low in ["good","ok","okkk","okk","hii","hello"] and len(low)<6: return "Ha bolo Malik? Kaunsa kaam hai?"
    if "time kya" in low: return f"{get_ist_str()}"
    if "30 min" in low: return f"Abhi {get_ist_str()}, 30 min baad {get_future_ist(30)} hoga."
    return None

def ask_groq(prompt):
    try:
        lore=get_lore_fresh()
        for k in GROQ_KEYS:
            if is_bad(k): continue
            for m in GROQ_MODELS:
                try:
                    r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":lore},{"role":"user","content":prompt}],"temperature":0.25,"max_tokens":220}, timeout=15)
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
                    r=requests.post(OPENAI_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":lore},{"role":"user","content":prompt}],"temperature":0.25,"max_tokens":220}, timeout=15)
                    if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                    if r.status_code in [401,403,429]: mark_bad(k); break
                except: continue
    except: pass
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
                    if "429" in str(e): mark_bad(k); break
                    continue
    except: pass
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
    except: pass
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

        if len(text)>800 and ("import os" in text or "def report_fault" in text):
            return "Code mil gaya Malik, scan karne ke liye /audit likho."

        # === DIRECT FIX FOR PHOTO WALA FAULT - MEMORY SE PEHLE CHECK ===
        if any(x in low for x in ["who is create you","who created you","who made you","kisne banaya","tumko kisne banaya","tumhe kisne banaya"]):
            return f"Malik {MALIK_NAME} ne banaya hai, {MALIK_TITLE} ne Vercel pe Flask, Groq, Gemini se."

        if "visale yaar" in low:
            return "Visale yaar matlab bahut hi kareeb, dil se juda dost Malik."

        if "queen ka naam" in low or "md saif ke queen" in low:
            # LORE_ENV me queen naam ho to wahi, warna generic
            q = "Malik ki queen ka naam private hai Malik, LORE_ENV me set karo to bata dunga."
            if "queen" in LORE_ENV.lower():
                # try to extract from lore
                q = LORE_ENV
            return q[:200]

        if low in ["ha fix karo","han fix karo","fix karo","yes fix","ha kar do"] and is_owner and PENDING_FIX:
            f=PENDING_FIX; PENDING_FIX=None
            if f["layer"] in ["MEMORY JSON","LORE LOOP","ALL"]: MEMORY.clear(); ABUSE.clear(); save_persist(); return f"Done Malik, {f['layer']} clear kar diya."
            if "KEYS" in f["layer"]: BAD_KEYS.clear(); return f"Done Malik, {f['layer']} ke BAD keys clear."
            return f"Done Malik, {f['layer']} ka fix ENV me karna hai: {f.get('fix','')}"

        if low in ["/audit","audit","/diagnose","diagnose"]:
            faults=full_system_audit()
            msg=f"🔍 Audit {get_ist_str()}\n\n"
            for i,f in enumerate(faults,1):
                msg+=f"{i}. {f['layer']} - {f['status']}\n   Line:{f.get('line','-')}\n   {f.get('info',f.get('current',''))}\n   Fix:{f.get('fix','')}\n\n"
            real=[x for x in faults if x["status"]=="FAULT"]
            if real and is_owner:
                PENDING_FIX=real[0]
                msg+=f"⚠️ Pehla fault: {PENDING_FIX['layer']} at {PENDING_FIX.get('line','')}\nFix kar du? Type 'ha fix karo'"
            return msg[:3900]

        if low in ["/report","report"]:
            g_ok=len([k for k in GROQ_KEYS if not is_bad(k)]); gm_ok=len([k for k in GEMINI_KEYS if not is_bad(k)])
            return f"Report Malik G:{g_ok}/{len(GROQ_KEYS)} GM:{gm_ok}/{len(GEMINI_KEYS)} Time:{get_ist_str()} Last:{LAST_ERROR[:60]}"

        if low in ["/start","start"]: return "Welcome to your world The Shadow King 👑 - Hazir hu Malik" if is_owner else f"Welcome {uname}, bolo?"
        if "kiska code" in low or "kis ka code" in low or "ye code kya" in low:
            return f"Ye Rakan BeastKing Monarch ka code hai Malik, {MALIK_NAME} aka {MALIK_TITLE} ka, Flask+Groq+Gemini+Vercel wala. Isi ka hai."
        if "app create nhi" in low or "app nahi banana" in low:
            MEMORY[uid]["hist"]=""; return "Samjha Malik, app nahi banana. Bolo phir kya kaam hai?"

        full=f"IST:{get_ist_str()} Owner:{is_owner} Name:{uname} Hist:{MEMORY[uid]['hist'][-800:]} Msg:{text} -> 1-2 lines short friend"
        ans=ask_all(full) or "Ha bolo Malik?"
        ans=clean(ans); MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-2500:]; save_persist(); return ans
    except Exception as e:
        report_fault(f"brain {uid}", e); return "Fault aaya Malik, /audit likho"

@app.route("/", methods=["GET"])
def home():
    try: 
        # ensure webhook
        if BOT_TOKEN and MY_URL:
            try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":f"{MY_URL}/webhook"}, timeout=5)
            except: pass
        return f"Rakan V7 Fixed Live G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {get_ist_str()}",200
    except: return "Error",200

@app.route("/fix", methods=["GET"])
def fix():
    try:
        global GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS,BAD_KEYS
        if str(request.args.get("id",""))!=OWNER_ID: return "Access Denied",403
        GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys(); BAD_KEYS.clear(); load_persist(); save_persist()
        return f"FIXED V7 {get_ist_str()} G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} Last:{LAST_ERROR}",200
    except Exception as e: return f"Fix err {e}",200

@app.route("/audit", methods=["GET"])
def audit_route():
    try:
        if str(request.args.get("id",""))!=OWNER_ID: return "Access Denied",403
        return jsonify({"time":get_ist_str(),"code":"Rakan V7","faults":full_system_audit()}),200
    except Exception as e: return jsonify({"error":str(e)}),200

@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return "Webhook OK "+get_ist_str(),200
    try:
        data=request.get_json(silent=True) or {}; msg=data.get("message",{}) or {}
        chat_id=msg.get("chat",{}).get("id"); user_id=str(msg.get("from",{}).get("id",0)); uname=msg.get("from",{}).get("first_name","user")
        text=msg.get("text","") or msg.get("caption","") or ""; message_id=msg.get("message_id")
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID)
        if is_owner: uname=MALIK_NAME
        reply_context=""; reply_msg=msg.get("reply_to_message")
        if reply_msg and reply_msg.get("text"): reply_context=f"Replied to: {reply_msg.get('text','')[:200]}"
        if msg.get("photo"):
            b=tg_get_file_bytes(msg["photo"][-1]["file_id"])
            if b:
                q=text if text else "Is photo me kya hai short me"
                v=ask_gemini_vision(b,q)
                if v: tg_send(chat_id,v,message_id)
                else: tg_send(chat_id,brain(text or "photo",user_id,is_owner,uname,reply_context),message_id)
                return "ok",200
        media_id=None
        if msg.get("voice"): media_id=msg["voice"]["file_id"]
        elif msg.get("audio"): media_id=msg["audio"]["file_id"]
        elif msg.get("video"): media_id=msg["video"]["file_id"]
        if media_id:
            b=tg_get_file_bytes(media_id)
            if b:
                heard=transcribe_media(b)
                if heard: tg_send(chat_id,brain(heard,user_id,is_owner,uname,reply_context),message_id)
                else: tg_send(chat_id,"awaz saaf nahi aayi Malik",message_id)
            return "ok",200
        if not text: return "ok",200
        if len(text)>800 and "import" in text and is_owner:
            tg_send(chat_id,"Code mil gaya Malik, /audit likho pura scan ke liye.",message_id)
            return "ok",200
        tg_send(chat_id,brain(text,user_id,is_owner,uname,reply_context),message_id)
        return "ok",200
    except Exception as e:
        report_fault("webhook", e)
        return "ok",200