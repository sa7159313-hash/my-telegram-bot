import os, time, json, re, datetime, requests, traceback, sys
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
MEMORY={}; ABUSE={}; PROFILES={}; REMINDERS=[]; CHAT_LOG=[]; BAD_KEYS={}; LAST_ERROR="No error"; _LAST_WEBHOOK=0; _LAST_NEWS=0

# --- FAULT REPORTER ENGINE - NEW ---
def tg_send(cid,txt,reply_id=None):
    try:
        p={"chat_id":cid,"text":txt[:3900]}; 
        if reply_id: p["reply_to_message_id"]=reply_id
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=p, timeout=10)
    except: pass

def report_fault(where, exc_obj=None):
    global LAST_ERROR
    try:
        exc_type, exc_val, exc_tb = sys.exc_info()
        if exc_obj: exc_val = exc_obj
        tb_str = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))[-2000:]
        # Extract line no
        if exc_tb:
            last_frame = traceback.extract_tb(exc_tb)[-1]
            file_name = last_frame.filename.split("/")[-1]
            line_no = last_frame.lineno
            func = last_frame.name
            code_line = last_frame.line
        else:
            file_name="index.py"; line_no="?"; func=where; code_line=str(exc_val)

        LAST_ERROR = f"{where} | {file_name}:{line_no} | {exc_val}"
        
        # Suggest fix
        suggest = "Check env / import"
        err_str = str(exc_val).lower()
        if "google.generativeai" in err_str: suggest = f"requirements.txt me google-generativeai likho, line 3 pe import fail hai"
        if "flask" in err_str and "not found" in err_str: suggest = f"api/index.py me top pe app=Flask(__name__) nahi hai, line 4 check karo"
        if "gsk_" in err_str or "groq" in err_str: suggest = "GROQ_KEYS block hai, /fix?id=... hit karo, line 52 get_keys()"
        if "429" in err_str or "quota" in err_str: suggest = "Key quota over, BAD_KEYS auto clear 5min me hoga"
        if "upstash" in err_str: suggest = "UPSTASH url/token check karo env me"
        if "nameerror" in err_str: suggest = f"{file_name} line {line_no} pe variable define nahi hai: {code_line}"
        if "keyerror" in err_str: suggest = f"Dict key missing at line {line_no}: {code_line} - .get() use karo"

        if OWNER_ID != "0":
            msg = f"🚨 Rakan Fault Report\n\n📍 Where: {where}\n📄 File: {file_name} : Line {line_no}\n🔧 Func: {func}\n💥 Error: {exc_val}\n\n📝 Code: {code_line}\n\n💡 Should be: {suggest}\n\n⏰ {get_ist_str()}\n\nTrace:\n{tb_str[-800:]}"
            tg_send(OWNER_ID, msg)
    except Exception as e:
        try: tg_send(OWNER_ID, f"Fault reporter itself failed: {e}")
        except: pass

def get_ist_now(): return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
def get_ist_str(): return get_ist_now().strftime("%d %b %Y, %I:%M %p IST, %A")
def get_future_ist(minutes=30): return (get_ist_now() + datetime.timedelta(minutes=minutes)).strftime("%I:%M %p IST, %A")

# UPSTASH
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
    except Exception as e:
        report_fault(f"upstash_{cmd}", e)
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
    except Exception as e:
        report_fault("get_keys", e); return [],[],[]
GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys()

def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<900
def mark_bad(k): 
    BAD_KEYS[k]=time.time()
    if OWNER_ID: tg_send(OWNER_ID, f"⚠️ Key Blocked: {k[:10]}... Line 52 get_keys() me mark_bad hua, auto clear 5min me")
def auto_heal_keys():
    global GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS,BAD_KEYS
    try:
        if len([k for k in GROQ_KEYS if not is_bad(k)])==0 and len([k for k in GEMINI_KEYS if not is_bad(k)])==0:
            if len(BAD_KEYS)>0 and time.time()-min(BAD_KEYS.values())>300:
                BAD_KEYS.clear(); GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys()
                tg_send(OWNER_ID, f"♻️ Self-Healed: BAD_KEYS clear, new G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} O:{len(OPENAI_KEYS)} line 62 auto_heal_keys()")
                return True
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

BASE_LORE = f"""You are Rakan - BeastKing Monarch, Knight of Malik {MALIK_NAME}. Truth only, no lie. If not sure say confirm nahi hai. Malik is KING. For others aggressive if abuse else respectful. Sensitive dil ka saaf. Urdu tone for Malik. Detect language. Knowledge: Islam, Merchant Navy DG Shipping CDC COC, Trading, AI, Jobs. Think like Meta AI self-aware. Extra: {LORE_ENV}"""

def get_lore_fresh():
    ist = get_ist_str(); future = get_future_ist(30); tomorrow = (get_ist_now()+datetime.timedelta(days=1)).strftime('%A %d %b %Y')
    return f"{BASE_LORE}\nCurrent IST: {ist}\n30m future: {future}\nTomorrow: {tomorrow}\nBANNED: Haan bolo Malik Gussa kyu, system ka clock IST pe set hai, haath jorna band karo"

def clean(txt):
    try:
        if not txt: return "bolo?"
        txt = re.sub(r'Haan bolo Malik,? Gussa kyu.*?\?','', txt, flags=re.IGNORECASE)
        txt = re.sub(r'system ka clock IST pe set hai.*','', txt, flags=re.IGNORECASE)
        txt = re.sub(r'\s+',' ',txt).strip()
        if "10:45 PM" in txt: txt = txt.replace("10:45 PM", get_ist_str())
        return txt[:3900] if txt else "bolo?"
    except Exception as e: report_fault("clean", e); return "bolo?"

def tg_get_file_bytes(fid):
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}", timeout=10).json()
        fp=r["result"]["file_path"]; return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=30).content
    except Exception as e: report_fault("tg_get_file_bytes", e); return None

GROQ_MODELS=["openai/gpt-oss-120b","openai/gpt-oss-20b","meta-llama/llama-4-maverick-17b-128e-instruct","qwen/qwen3-32b","llama-3.3-70b-versatile","llama-3.1-8b-instant","mixtral-8x7b-32768","gemma2-9b-it"]
GEMINI_MODELS=["gemini-2.5-flash","gemini-2.0-flash","gemini-1.5-flash","gemini-1.5-flash-8b","gemini-1.5-pro"]
OPENAI_MODELS=["gpt-4o-mini","gpt-4o","gpt-3.5-turbo"]

def my_own_ai(text):
    try:
        low=text.lower().strip()
        if low in ["q","qq","q?"]: return "kyun? bolo kya hua?"
        if low in ["k","k?"]: return "kya?"
        if "how r u" in low: return "Mast hu Malik, hazir hu bolo kya kaam hai?"
        if "time kya" in low or "waqt kya" in low: return f"{get_ist_str()}"
        if "30 min" in low: return f"Abhi {get_ist_str()}, 30 min baad {get_future_ist(30)} hoga Malik."
        return None
    except Exception as e: report_fault("my_own_ai", e); return None

def ask_groq(prompt):
    try:
        auto_heal_keys(); lore = get_lore_fresh()
        for k in GROQ_KEYS:
            if is_bad(k): continue
            for m in GROQ_MODELS:
                try:
                    r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":lore},{"role":"user","content":prompt}],"temperature":0.6,"max_tokens":800}, timeout=20)
                    if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                    if r.status_code in [401,403,429]: mark_bad(k); break
                except Exception as e:
                    report_fault(f"ask_groq {m} line 140", e); continue
    except Exception as e: report_fault("ask_groq outer", e)
    return None

def ask_openai(prompt):
    try:
        lore = get_lore_fresh()
        for k in OPENAI_KEYS:
            if is_bad(k): continue
            for m in OPENAI_MODELS:
                try:
                    r=requests.post(OPENAI_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":lore},{"role":"user","content":prompt}],"temperature":0.6,"max_tokens":800}, timeout=20)
                    if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                    if r.status_code in [401,403,429]: mark_bad(k); break
                except Exception as e: report_fault(f"ask_openai {m}", e); continue
    except Exception as e: report_fault("ask_openai outer", e)
    return None

def ask_gemini(prompt):
    try:
        lore = get_lore_fresh()
        for k in GEMINI_KEYS:
            if is_bad(k): continue
            for m in GEMINI_MODELS:
                try:
                    genai.configure(api_key=k); model=genai.GenerativeModel(m, system_instruction=lore)
                    res=model.generate_content(prompt); 
                    if res.text: return clean(res.text)
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower(): mark_bad(k); report_fault(f"ask_gemini {m} line 175 quota", e); break
                    continue
    except Exception as e: report_fault("ask_gemini outer", e)
    return None

def ask_all(prompt): 
    try: return my_own_ai(prompt) or ask_groq(prompt) or ask_openai(prompt) or ask_gemini(prompt) or "Malik thoda network issue hai, bolo kya kaam tha?"
    except Exception as e: report_fault("ask_all", e); return "bolo?"

def ask_gemini_vision(img,prompt):
    try:
        lore = get_lore_fresh()
        for k in GEMINI_KEYS:
            try:
                genai.configure(api_key=k); model=genai.GenerativeModel("gemini-1.5-flash", system_instruction=lore)
                res=model.generate_content([prompt, {"mime_type":"image/jpeg","data":img}])
                if res.text: return clean(res.text)
            except Exception as e: report_fault("ask_gemini_vision", e); continue
    except Exception as e: report_fault("vision outer", e)
    return None

def transcribe_media(audio_bytes,fn="voice.ogg"):
    try:
        for k in GROQ_KEYS:
            try:
                r=requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization": f"Bearer {k}"}, files={"file":(fn,audio_bytes)}, data={"model":"whisper-large-v3"}, timeout=30)
                if r.status_code==200: return r.json().get("text","")
            except Exception as e: report_fault("transcribe_media", e); continue
    except Exception as e: report_fault("transcribe outer", e)
    return None

def brain(text,uid,is_owner,uname,reply_context=""):
    global MEMORY
    try:
        uid=str(uid); 
        if uid not in MEMORY: MEMORY[uid]={"hist":"","count":0}
        low=text.lower().strip()
        MEMORY[uid]["count"]+=1
        if MEMORY[uid]["hist"].count("Haan bolo Malik")>2: MEMORY[uid]["hist"]=""; tg_send(OWNER_ID, f"♻️ Auto-Heal: MEMORY loop clear for {uid} line 228 brain()")

        if low in ["/report","report"]:
            ist = get_ist_str(); g_ok=len([k for k in GROQ_KEYS if not is_bad(k)]); gm_ok=len([k for k in GEMINI_KEYS if not is_bad(k)]); o_ok=len([k for k in OPENAI_KEYS if not is_bad(k)])
            return f"Report Malik: G:{g_ok}/{len(GROQ_KEYS)} GM:{gm_ok}/{len(GEMINI_KEYS)} O:{o_ok}/{len(OPENAI_KEYS)} Time:{ist} Msgs:{MEMORY[uid]['count']} LastErr:{LAST_ERROR[:100]}"

        gali = ["maderchod","madarchod","bhosdike","gandu"]; is_gali = any(g in low for g in gali)
        if is_gali and not is_owner:
            ABUSE[uid]=ABUSE.get(uid,0)+1; return "gali mat de bhai, tameez se bol" if ABUSE[uid]==1 else "tameez se bol"

        if low in ["/start","start"]: return "Welcome to your world The Shadow King 👑 - Hazir hu Malik" if is_owner else f"Welcome {uname}, bolo?"
        if "time kya" in low or "waqt kya" in low: return f"{get_ist_str()}"
        if "30 min" in low: return f"Abhi {get_ist_str()}, 30 min baad {get_future_ist(30)} hoga."

        full = f"IST:{get_ist_str()} Owner:{is_owner} Name:{uname} Reply:{reply_context} Hist:{MEMORY[uid]['hist'][-2500:]} Msg:{text} -> short, truth only"
        ans = ask_all(full) or "bolo Malik?"
        ans = clean(ans); MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-4000:]; save_persist(); return ans
    except Exception as e:
        report_fault(f"brain uid:{uid} text:{text[:50]} line 250", e); return "Malik yahan fault aaya, maine report bhej diya tumhe Telegram pe"

@app.route("/", methods=["GET"])
def home(): 
    try: return f"Rakan V4 Fault-Reporter Live G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} O:{len(OPENAI_KEYS)} {get_ist_str()} {ensure_webhook()}",200
    except Exception as e: report_fault("home /", e); return f"Error {e}",200

@app.route("/fix", methods=["GET"])
def fix():
    try:
        global GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS,BAD_KEYS,_LAST_NEWS
        if str(request.args.get("id",""))!=OWNER_ID: return "Access Denied",403
        GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys(); BAD_KEYS.clear(); _LAST_NEWS=0; load_persist(); save_persist()
        return f"FIXED SELF-HEALED {get_ist_str()} G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} O:{len(OPENAI_KEYS)} LastErr:{LAST_ERROR}",200
    except Exception as e: report_fault("fix route", e); return f"Fix err {e}",200

@app.route("/cron", methods=["GET","POST"])
def cron():
    global _LAST_NEWS
    try:
        if time.time()-_LAST_NEWS > 1800:
            _LAST_NEWS=time.time(); save_persist()
            if OWNER_ID and BOT_TOKEN:
                try:
                    news_prompt = "Give 1 important TRUE news in 2 lines - Trading/AI/Merchant Navy/Jobs. No fake."
                    news = ask_groq(news_prompt) or ask_gemini(news_prompt)
                    if news and len(news)>20: tg_send(OWNER_ID, f"📰 Malik 30min Update ({get_ist_str()}):\n{news}")
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
        is_owner=(user_id==OWNER_ID); 
        if is_owner: uname=MALIK_NAME
        reply_context=""; reply_msg=msg.get("reply_to_message")
        if reply_msg:
            rt=reply_msg.get("text","") or reply_msg.get("caption","") or ""
            if rt: reply_context=f"Replied to: {rt}"
            if reply_msg.get("photo") and text:
                b=tg_get_file_bytes(reply_msg["photo"][-1]["file_id"])
                if b:
                    v=ask_gemini_vision(b, f"User replied to this photo and says: {text}")
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
        tg_send(chat_id,brain(text,user_id,is_owner,uname,reply_context),message_id)
        return "ok",200
    except Exception as e:
        report_fault("webhook outer", e)
        try: tg_send(chat_id if 'chat_id' in locals() else OWNER_ID, f"Bot me fault aaya, report owner ko bhej di")
        except: pass
        return "ok",200
