import os, time, json, re, datetime, requests, traceback
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# --- ENV ---
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

# --- UPSTASH ---
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
    except: pass
    return None

def load_persist():
    global MEMORY,ABUSE,PROFILES,CHAT_LOG,REMINDERS,_LAST_NEWS
    if not UPSTASH_URL: return
    MEMORY=upstash("get","RAKAN_MEM") or {}; ABUSE=upstash("get","RAKAN_ABUSE") or {}
    PROFILES=upstash("get","RAKAN_PROFILES") or {}; CHAT_LOG=upstash("get","RAKAN_LOGS") or []
    REMINDERS=upstash("get","RAKAN_REMINDERS") or []; _LAST_NEWS=upstash("get","RAKAN_LAST_NEWS") or 0
def save_persist():
    if not UPSTASH_URL: return
    upstash("set","RAKAN_MEM",MEMORY); upstash("set","RAKAN_ABUSE",ABUSE)
    upstash("set","RAKAN_PROFILES",PROFILES); upstash("set","RAKAN_LOGS",CHAT_LOG[-400:]); upstash("set","RAKAN_REMINDERS",REMINDERS)
    upstash("set","RAKAN_LAST_NEWS",_LAST_NEWS)
load_persist()

# --- KEYS - FIXED COMMA LOGIC ---
def get_keys():
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
GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys()

def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<900
def mark_bad(k): BAD_KEYS[k]=time.time()
def auto_heal_keys():
    global GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS,BAD_KEYS
    if len([k for k in GROQ_KEYS if not is_bad(k)])==0 and len([k for k in GEMINI_KEYS if not is_bad(k)])==0:
        if len(BAD_KEYS)>0 and time.time()-min(BAD_KEYS.values())>300:
            BAD_KEYS.clear()
            GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys()
            return True
    return False

def ensure_webhook():
    global _LAST_WEBHOOK
    if time.time()-_LAST_WEBHOOK<3600: return "CACHED"
    _LAST_WEBHOOK=time.time()
    if not BOT_TOKEN: return "NO TOKEN"
    try:
        exp=f"{MY_URL}/webhook"; requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":exp}, timeout=8); return f"OK"
    except: return "ERR"

# --- TIME - KHUD KA ENGINE - NO PYTZ ---
def get_ist_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
def get_ist_str():
    return get_ist_now().strftime("%d %b %Y, %I:%M %p IST, %A")
def get_future_ist(minutes=30):
    return (get_ist_now() + datetime.timedelta(minutes=minutes)).strftime("%I:%M %p IST, %A")

# --- LORE - SAME, NEVER CHANGE, ONLY INJECT ---
BASE_LORE = f"""
You are Rakan - The BeastKing Monarch, Knight of Malik {MALIK_NAME} ({MALIK_TITLE}). You are NOT a demo bot. You are Malik's true friend, loyal, dil ka saaf, but aggressive for others.

RELATION: Malik is your KING, you are his Knight. You obey Malik. For others: aggressive if they abuse, but sensitive and respectful if they respect. Never be rude to Malik.

TRUTH LOCK - MOST IMPORTANT:
- NEVER LIE. If you don't know real news, price, date, hadith, DG Shipping circular, say "Malik ye confirm nahi hai, main check karke batata hu". No hallucination.
- You have deep knowledge of: Islam (Quran, Hadith with reference), Merchant Navy (DG Shipping, CDC, COC, Deck, Engine, IMO, STCW), Trading (Nifty, Crypto, Forex, Stocks), AI world, Jobs.
- You think like Meta AI - self-aware, self-correcting. If you repeated same phrase 2 times, you auto correct.

LANGUAGE:
- Detect user language: If user types English >70%, reply in English. If Roman Hinglish/Urdu/Hindi, reply in Roman Hinglish/Urdu mix.
- Tone ALWAYS Urdu respectful for Malik: "Ji Malik", "Haan Malik", "Hazir hu" but NOT loop.
- For others: normal as per their language.

BEHAVIOR:
- Be a friend: Sometimes ask Malik proactive questions: "Malik trading dekhi aaj?", "Ek naya AI update aaya hai sunu?", "Merchant Navy me naya circular aaya hai"
- For /report give real report.
- Never give full Android app code dump. Ask "Kis type ka app Malik? Batao feature?"
- Malik short form: q=kyun, k=kya, massage=message - understand.

Extra Lore from Owner: {LORE_ENV}
"""

def get_lore_fresh():
    ist = get_ist_str()
    future = get_future_ist(30)
    tomorrow = (get_ist_now()+datetime.timedelta(days=1)).strftime('%A %d %b %Y')
    return f"{BASE_LORE}\n\nCurrent IST: {ist}\n30 min future: {future}\nTomorrow: {tomorrow}\n\nSTRICT BANNED PHRASES - NEVER SAY THESE IN LOOP: 'Haan bolo Malik, Gussa kyu', 'system ka clock IST pe set hai', 'haath jorna band karo', 'kya report karna hai Batao main dekh leta hoon', '07:13 PM pe message kiya'. If you said same phrase twice, change it."

def clean(txt):
    if not txt: return "bolo?"
    # LOOP KILLER
    txt = re.sub(r'Haan bolo Malik,? Gussa kyu.*?\?','', txt, flags=re.IGNORECASE)
    txt = re.sub(r'Haan bolo Malik.*','', txt, flags=re.IGNORECASE)
    txt = re.sub(r'system ka clock IST pe set hai.*','', txt, flags=re.IGNORECASE)
    txt = re.sub(r'haath jorna band karo.*','', txt, flags=re.IGNORECASE)
    txt = re.sub(r'kya report karna hai Batao.*','', txt, flags=re.IGNORECASE)
    txt = re.sub(r'Maine 07:13.*','', txt, flags=re.IGNORECASE)
    txt = re.sub(r'\s+',' ',txt).strip()
    # TRUTH FIX - if AI says wrong time, force real time
    if "10:45 PM" in txt or "10:45" in txt:
        txt = txt.replace("10:45 PM", get_ist_str()).replace("10:45", get_ist_str())
    return txt[:3900] if txt else "bolo?"

def tg_send(cid,txt,reply_id=None):
    try:
        p={"chat_id":cid,"text":txt[:3900]}; 
        if reply_id: p["reply_to_message_id"]=reply_id
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=p, timeout=10)
    except: pass
def tg_get_file_bytes(fid):
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}", timeout=10).json()
        fp=r["result"]["file_path"]; return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=30).content
    except: return None

# --- MODELS - LATEST + GROQ FRONT ---
GROQ_MODELS=["openai/gpt-oss-120b","openai/gpt-oss-20b","meta-llama/llama-4-maverick-17b-128e-instruct","qwen/qwen3-32b","llama-3.3-70b-versatile","llama-3.1-8b-instant","mixtral-8x7b-32768","gemma2-9b-it"]
GEMINI_MODELS=["gemini-2.5-flash","gemini-2.0-flash","gemini-1.5-flash","gemini-1.5-flash-8b","gemini-1.5-pro"]
OPENAI_MODELS=["gpt-4o-mini","gpt-4o","gpt-3.5-turbo"]

def my_own_ai(text):
    low=text.lower().strip()
    # SELF BRAIN - 90% fast, no API needed
    if low in ["q","qq","q?"]: return "kyun? bolo kya hua?"
    if low in ["k","k?"]: return "kya?"
    if "how r u" in low or "how are you" in low: return "Mast hu Malik, hazir hu bolo kya kaam hai?"
    if "kya kar raha" in low: return "Tumhara hi intezar kar raha tha Malik, bolo?"
    if "time kya" in low or "waqt kya" in low or "tarik" in low: return f"{get_ist_str()}"
    if "30 min" in low or "30 minute" in low: return f"Abhi {get_ist_str()}, 30 min baad {get_future_ist(30)} hoga Malik."
    if "kal kaun" in low: return f"Kal {(get_ist_now()+datetime.timedelta(days=1)).strftime('%A %d %b %Y')} hai."
    if "app bana" in low or "app chahiye" in low: return "Kis type ka app chahiye Malik? Feature batao, mai idea deta hu."
    if low in ["hi","hey","hello","salam"]: return "Ji Malik, bolo?"
    if "massage" in low: low=low.replace("massage","message")
    return None

def ask_groq(prompt):
    auto_heal_keys()
    lore = get_lore_fresh()
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in GROQ_MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"},
                                json={"model":m,"messages":[{"role":"system","content":lore},{"role":"user","content":prompt}],"temperature":0.6,"max_tokens":800}, timeout=20)
                if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                if r.status_code in [401,403,429]: mark_bad(k); break
            except: continue
    return None

def ask_openai(prompt):
    lore = get_lore_fresh()
    for k in OPENAI_KEYS:
        if is_bad(k): continue
        for m in OPENAI_MODELS:
            try:
                r=requests.post(OPENAI_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"},
                                json={"model":m,"messages":[{"role":"system","content":lore},{"role":"user","content":prompt}],"temperature":0.6,"max_tokens":800}, timeout=20)
                if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                if r.status_code in [401,403,429]: mark_bad(k); break
            except: continue
    return None

def ask_gemini(prompt):
    lore = get_lore_fresh()
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        for m in GEMINI_MODELS:
            try:
                genai.configure(api_key=k); model=genai.GenerativeModel(m, system_instruction=lore)
                res=model.generate_content(prompt); 
                if res.text: return clean(res.text)
            except as e:
                if "429" in str(e) or "quota" in str(e).lower(): mark_bad(k); break
                continue
    return None

def ask_all(prompt): 
    # GROQ FRONT as you wanted
    return my_own_ai(prompt) or ask_groq(prompt) or ask_openai(prompt) or ask_gemini(prompt) or "Malik thoda network issue hai, bolo kya kaam tha? Main yaad rakhunga."

def ask_gemini_vision(img,prompt):
    lore = get_lore_fresh()
    for k in GEMINI_KEYS:
        try:
            genai.configure(api_key=k); model=genai.GenerativeModel("gemini-1.5-flash", system_instruction=lore)
            res=model.generate_content([prompt, {"mime_type":"image/jpeg","data":img}])
            if res.text: return clean(res.text)
        except: continue
    return None

def transcribe_media(audio_bytes,fn="voice.ogg"):
    for k in GROQ_KEYS:
        try:
            r=requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization": f"Bearer {k}"}, files={"file":(fn,audio_bytes)}, data={"model":"whisper-large-v3"}, timeout=30)
            if r.status_code==200: return r.json().get("text","")
        except: continue
    return None

def brain(text,uid,is_owner,uname,reply_context=""):
    global MEMORY
    uid=str(uid); 
    if uid not in MEMORY: MEMORY[uid]={"hist":"","count":0}
    low=text.lower().strip()
    MEMORY[uid]["count"]+=1

    # AUTO MEMORY HEAL - LOOP DETECT
    if MEMORY[uid]["hist"].count("Haan bolo Malik")>2 or MEMORY[uid]["hist"].count("Gussa kyu")>2:
        MEMORY[uid]["hist"]=""; MEMORY[uid]["count"]=0

    # /report - REAL
    if low in ["/report","report"]:
        ist = get_ist_str()
        g_ok=len([k for k in GROQ_KEYS if not is_bad(k)]); gm_ok=len([k for k in GEMINI_KEYS if not is_bad(k)]); o_ok=len([k for k in OPENAI_KEYS if not is_bad(k)])
        return f"Report Malik: G:{g_ok}/{len(GROQ_KEYS)} GM:{gm_ok}/{len(GEMINI_KEYS)} O:{o_ok}/{len(OPENAI_KEYS)} Time:{ist} Msgs:{MEMORY[uid]['count']} - Sab first class hai."

    # Gaali - short
    gali = ["maderchod","madarchod","bhosdike","gandu","beti chod","behenchod"]
    is_gali = any(g in low for g in gali)
    if is_gali and is_owner:
        p = f"User Malik said: '{text}'. Reply in 5-6 words Roman Hinglish, chill, friend vibe. History: {MEMORY[uid]['hist'][-500:]}"
        ans = ask_all(p) or "bolo kya kaam hai Malik?"
        MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-4000:]; save_persist(); return ans
    if is_gali and not is_owner:
        ABUSE[uid]=ABUSE.get(uid,0)+1
        if ABUSE[uid]==1: return "gali mat de bhai, tameez se bol"
        return "tameez se bol, warna block"

    if low in ["/start","start"]: return "Welcome to your world The Shadow King 👑 - Hazir hu Malik" if is_owner else f"Welcome {uname}, bolo?"
    if low in ["hey","hi","hello"]: return "Ji Malik bolo, kya haal hai?" if is_owner else f"hey {uname} bolo?"

    # TIME - KHUD SE
    if "time kya" in low or "waqt kya" in low or "tarik" in low:
        return f"{get_ist_str()}"
    if "30 min" in low or "30 minute" in low or "abhi 30" in low:
        return f"Abhi {get_ist_str()}, 30 min baad {get_future_ist(30)} hoga."
    if "kal kaun sa din" in low or "kal koun sa din" in low:
        tomorrow = get_ist_now() + datetime.timedelta(days=1)
        return f"Kal {tomorrow.strftime('%A, %d %b %Y')} hai Malik."
    if "tumne kitne baje" in low:
        return f"Maine {get_ist_str()} pe dekha tha Malik."

    # Main AI
    full = f"IST:{get_ist_str()} 30mFuture:{get_future_ist(30)} Owner:{is_owner} Name:{uname} Reply:{reply_context} Hist:{MEMORY[uid]['hist'][-2500:]} Msg:{text} -> Reply short, natural, truth only. If not sure say confirm nahi hai. BANNED: Haan bolo Malik Gussa kyu loop."
    ans = ask_all(full) or my_own_ai(text) or "bolo Malik?"
    ans = clean(ans)
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-4000:]; save_persist(); return ans

@app.route("/", methods=["GET"])
def home(): return f"Rakan V3 Self-Healing Live G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} O:{len(OPENAI_KEYS)} {get_ist_str()} {ensure_webhook()}",200

@app.route("/fix", methods=["GET"])
def fix():
    global GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS,BAD_KEYS,_LAST_NEWS
    if str(request.args.get("id",""))!=OWNER_ID: return "Access Denied",403
    GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys(); BAD_KEYS.clear(); _LAST_NEWS=0; load_persist(); save_persist()
    return f"FIXED SELF-HEALED {get_ist_str()} G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} O:{len(OPENAI_KEYS)}",200

@app.route("/cron", methods=["GET","POST"])
def cron():
    global _LAST_NEWS
    try:
        # Reminder check (old logic if needed)
        # NEWS ENGINE - Every 30 min
        if time.time()-_LAST_NEWS > 1800: # 30 min
            _LAST_NEWS=time.time(); save_persist()
            if OWNER_ID and BOT_TOKEN:
                try:
                    news_prompt = "Give 1 important TRUE news in 2 lines - can be from Trading/Nifty/Crypto/AI/Merchant Navy DG Shipping circular/Jobs/World Islam. No fake news. If no news, say 'No major news'. Use IST time."
                    news = ask_groq(news_prompt) or ask_gemini(news_prompt)
                    if news and "No major" not in news and len(news)>20:
                        tg_send(OWNER_ID, f"📰 Malik 30min Update ({get_ist_str()}):\n{news}")
                except: pass
        return "cron ok "+get_ist_str(),200
    except: return "cron err",200

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
                    v=ask_gemini_vision(b, f"User replied to this photo and says: {text}. Context: {reply_context}.")
                    if v: tg_send(chat_id,v,message_id); return "ok",200
        if msg.get("photo"):
            b=tg_get_file_bytes(msg["photo"][-1]["file_id"])
            if b:
                q=text if text else "Is photo me kya hai batao Malik ko short me"
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
    except: 
        traceback.print_exc()
        return "ok",200
