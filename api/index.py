import os, time, json, re, datetime, requests, traceback
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

MALIK_NAME="MD Saif Ahmad"; MALIK_TITLE="The Shadow King"; QUEEN_NAME="Theodore"
MEMORY={}; ABUSE={}; PROFILES={}; REMINDERS=[]; CHAT_LOG=[]; BAD_KEYS={}; LAST_ERROR="No error"; _LAST_WEBHOOK=0

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
    global MEMORY,ABUSE,PROFILES,CHAT_LOG,REMINDERS
    if not UPSTASH_URL: return
    MEMORY=upstash("get","RAKAN_MEM") or {}; ABUSE=upstash("get","RAKAN_ABUSE") or {}
    PROFILES=upstash("get","RAKAN_PROFILES") or {}; CHAT_LOG=upstash("get","RAKAN_LOGS") or []
    REMINDERS=upstash("get","RAKAN_REMINDERS") or []
def save_persist():
    if not UPSTASH_URL: return
    upstash("set","RAKAN_MEM",MEMORY); upstash("set","RAKAN_ABUSE",ABUSE)
    upstash("set","RAKAN_PROFILES",PROFILES); upstash("set","RAKAN_LOGS",CHAT_LOG[-400:]); upstash("set","RAKAN_REMINDERS",REMINDERS)
load_persist()

def get_keys():
    g,gm=[],[]; 
    for k,v in os.environ.items():
        if not v: continue
        raw=str(v); parts=[p.strip().strip('"').strip("'") for p in raw.replace("\n",",").split(",") if p.strip()]
        for p in parts:
            if "GEMINI" in k.upper() and len(p)>20 and p not in gm: gm.append(p)
            if "GROQ" in k.upper() and len(p)>10 and p not in g: g.append(p)
            if p.startswith("gsk_") and p not in g: g.append(p)
            if p.startswith("AIza") and p not in gm: gm.append(p)
            if p.startswith("AQ.") and p not in gm: gm.append(p)
    return list(dict.fromkeys(g)),list(dict.fromkeys(gm))
GROQ_KEYS,GEMINI_KEYS=get_keys()
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<900
def mark_bad(k): BAD_KEYS[k]=time.time()
def ensure_webhook():
    global _LAST_WEBHOOK
    if time.time()-_LAST_WEBHOOK<3600: return "CACHED"
    _LAST_WEBHOOK=time.time()
    if not BOT_TOKEN: return "NO TOKEN"
    try:
        exp=f"{MY_URL}/webhook"; requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":exp}, timeout=8); return f"OK"
    except: return "ERR"

def get_ist_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
def get_ist_str():
    return get_ist_now().strftime("%d %b %Y, %I:%M %p IST, %A")
def get_future_ist(minutes=30):
    return (get_ist_now() + datetime.timedelta(minutes=minutes)).strftime("%I:%M %p IST")

# === FIX 1: LORE SE "Haan bolo Malik, Gussa kyu" WALA EXAMPLE HATAYA ===
def get_lore_fresh():
    ist = get_ist_str()
    # Ab lore me koi example phrase nahi hai jo loop kare
    base = f"""You are Rakan - The BeastKing Monarch, Knight of Malik {MALIK_NAME}. You are human-like, loyal, short, direct.
Current IST: {ist}. Tomorrow will be {(get_ist_now()+datetime.timedelta(days=1)).strftime('%A %d %b %Y')}.

STRICT RULES - IF YOU BREAK, YOU FAIL:
- NEVER start every message with "Haan bolo Malik", "Haan Malik", "Gussa kyu?", "system ka clock IST pe set hai", "haath jorna band karo". These are BANNED.
- Be natural. If Malik says "Maderchod", just say "bolo kya kaam hai?" or "ha bolo?" - 4-5 words, no lecture, no haath jod emoji.
- For /report, don't say "kya report karna hai Batao main dekh leta hoon". Give real report.
- If asked time, give {ist} only, don't add 10:45 PM. If asked "30 min baad", give {get_future_ist(30)}.
- If user replied to a message, understand that reply.
- Language: Roman Hinglish with Malik.
- Extra Lore: {LORE_ENV}
"""
    return base

def clean(txt):
    if not txt: return "bolo?"
    # FIX 2: Clean me se loop phrases nikal diye
    txt = re.sub(r'Haan bolo Malik.*?\?','', txt, flags=re.IGNORECASE)
    txt = re.sub(r'Haan Malik, kya report.*','', txt, flags=re.IGNORECASE)
    txt = re.sub(r'system ka clock IST pe set hai.*','', txt, flags=re.IGNORECASE)
    txt = re.sub(r'Gussa kyu.*?\?','', txt, flags=re.IGNORECASE)
    txt = re.sub(r'\s+',' ',txt).strip()
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

GROQ_MODELS=["openai/gpt-oss-120b","meta-llama/llama-4-maverick-17b-128e-instruct","llama-3.3-70b-versatile","llama-3.1-8b-instant"]
GEMINI_MODELS=["gemini-2.5-flash","gemini-1.5-flash"]

def ask_groq(prompt):
    lore = get_lore_fresh()
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in GROQ_MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"},
                                json={"model":m,"messages":[{"role":"system","content":lore},{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":800}, timeout=20)
                if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                if r.status_code in [401,403,429]: mark_bad(k); break
            except: continue
    return None
def ask_gemini(prompt):
    lore = get_lore_fresh()
    for k in GEMINI_KEYS:
        for m in GEMINI_MODELS:
            try:
                genai.configure(api_key=k); model=genai.GenerativeModel(m, system_instruction=lore)
                res=model.generate_content(prompt); 
                if res.text: return clean(res.text)
            except: continue
    return None
def ask_all(prompt): return ask_gemini(prompt) or ask_groq(prompt)
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

    # FIX 3: /report ka loop khatam - ab real report dega
    if low in ["/report","report"]:
        ist = get_ist_str()
        return f"Report: G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} Time:{ist} Memory:{MEMORY[uid]['count']} msgs. Bolo aur kya chahiye?"

    # FIX 4: Gaali pe ab "Haan bolo Malik Gussa kyu" nahi bolega - seedha short
    gali = ["maderchod","madarchod","bhosdike","gandu","beti chod","behenchod"]
    is_gali = any(g in low for g in gali)
    if is_gali and is_owner:
        # Seedha AI ko bhi bol diya ki ye phrase mat bol
        p = f"User (Malik) said: '{text}'. Reply in 5-6 words Roman Hinglish, chill. BANNED PHRASES: Haan bolo Malik, Gussa kyu, system ka clock, haath jorna. Just say 'bolo kya kaam hai' type short. History: {MEMORY[uid]['hist'][-500:]}"
        ans = ask_all(p) or "bolo kya kaam hai?"
        MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-4000:]; save_persist(); return ans
    if is_gali and not is_owner:
        ABUSE[uid]=ABUSE.get(uid,0)+1
        if ABUSE[uid]==1: return "gali mat de bhai"
        return "tameez se bol"

    if low in ["/start","start"]: return "Welcome to your world The Shadow King 👑" if is_owner else f"Welcome {uname}"
    if low in ["hey","hi","hello"]: return "hey bolo kya haal hai?" if is_owner else f"hey {uname} bolo?"

    # FIX 5: Time fresh + 30 min future fix
    if "time kya" in low or "waqt kya" in low or "tarik" in low:
        return f"{get_ist_str()}"
    if "30 min" in low or "30 minute" in low or "abhi 30" in low:
        return f"Abhi {get_ist_str()}, 30 min baad {get_future_ist(30)} hoga."
    if "kal kaun sa din" in low or "kal koun sa din" in low:
        tomorrow = get_ist_now() + datetime.timedelta(days=1)
        return f"Kal {tomorrow.strftime('%A, %d %b %Y')} hai."
    if "tumne kitne baje" in low or "kitne baje message" in low:
        return f"Maine {get_ist_str()} pe dekha tha."

    full = f"IST:{get_ist_str()} 30mFuture:{get_future_ist(30)} Owner:{is_owner} Name:{uname} Reply:{reply_context} Hist:{MEMORY[uid]['hist'][-2500:]} Msg:{text} -> Short, natural, Roman Hinglish. BANNED: Haan bolo Malik, Gussa kyu, system ka clock."
    ans = ask_all(full) or "bolo?"
    ans = clean(ans)
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-4000:]; save_persist(); return ans

@app.route("/", methods=["GET"])
def home(): return f"Rakan Live G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {get_ist_str()} {ensure_webhook()}",200
@app.route("/fix", methods=["GET"])
def fix():
    global GROQ_KEYS,GEMINI_KEYS,BAD_KEYS
    if str(request.args.get("id",""))!=OWNER_ID: return "Access Denied",403
    GROQ_KEYS,GEMINI_KEYS=get_keys(); BAD_KEYS.clear(); load_persist(); return f"FIXED {get_ist_str()}",200
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
                q=text if text else "Is photo me kya hai batao"
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
                else: tg_send(chat_id,"awaz saaf nahi aayi",message_id)
            return "ok",200
        if not text: return "ok",200
        tg_send(chat_id,brain(text,user_id,is_owner,uname,reply_context),message_id)
        return "ok",200
    except: print(traceback.format_exc()); return "ok",200
