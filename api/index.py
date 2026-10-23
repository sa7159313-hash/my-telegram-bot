import os, time, json, base64, re, datetime, requests, traceback
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = int(os.environ.get("OWNER_ID","0") or 0)
MY_URL = os.environ.get("MY_URL","").rstrip("/") or "https://my-telegram-bot-lime.vercel.app"
LORE_ENV = os.environ.get("THE_BEAST_KING_MONARCH_AKAAN_LORE","")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY","") or os.environ.get("ELEVEN_API_KEY","")
MALE_VOICE_ID = (os.environ.get("ELEVEN_MALE_VOICE","pNInz6obpgDQGcFmaJgB") or "pNInz6obpgDQGcFmaJgB").strip()
FEMALE_VOICE_ID = (os.environ.get("ELEVEN_FEMALE_VOICE","EXAVITQu4vr4xnSDxMaL") or "EXAVITQu4vr4xnSDxMaL").strip()
REPLICATE_TOKEN = os.environ.get("REPLICATE_API_TOKEN","") or os.environ.get("REPLICATE_API_KEY","")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MALIK_NAME = "MD Saif Ahmad"
MALIK_TITLE = "The Shadow King"
QUEEN_NAME = "Theodore"
BIRTH_DATE = "24 September 2025"
BIRTH_TIME = "Subah 7 baje"
RAKAN_HISTORY = "Janam 24 September 2025 Subah 7 baje, Malik MD Saif Ahmad ne banaya."
MEMORY = {}; ABUSE = {}; PROFILES = {}; REMINDERS = []
OWNER_PREF = {"voice_mode": False, "voice_gender": "female"}
CHAT_LOG = []; BAD_KEYS = {}; LAST_ERROR = "No error yet"; _LAST_WEBHOOK = 0

def upstash(cmd, key, val=None):
    if not UPSTASH_URL or not UPSTASH_TOKEN: return None
    try:
        headers = {"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        if cmd=="get":
            r=requests.get(f"{UPSTASH_URL}/get/{key}", headers=headers, timeout=5)
            if r.status_code==200:
                d=r.json().get("result")
                return json.loads(d) if d else None
        if cmd=="set" and val is not None:
            r=requests.post(f"{UPSTASH_URL}", headers=headers, json=["SET", key, json.dumps(val)], timeout=5)
            return r.status_code==200
    except: pass
    return None

def load_persist():
    global MEMORY, ABUSE, OWNER_PREF, CHAT_LOG, PROFILES, REMINDERS
    if not UPSTASH_URL: return
    MEMORY = upstash("get","RAKAN_MEM") or {}
    ABUSE = upstash("get","RAKAN_ABUSE") or {}
    PROFILES = upstash("get","RAKAN_PROFILES") or {}
    OWNER_PREF = upstash("get","RAKAN_PREF") or OWNER_PREF
    CHAT_LOG = upstash("get","RAKAN_LOGS") or []
    REMINDERS = upstash("get","RAKAN_REMINDERS") or []

def save_persist():
    if not UPSTASH_URL: return
    upstash("set","RAKAN_MEM", MEMORY); upstash("set","RAKAN_ABUSE", ABUSE)
    upstash("set","RAKAN_PROFILES", PROFILES); upstash("set","RAKAN_PREF", OWNER_PREF)
    upstash("set","RAKAN_LOGS", CHAT_LOG[-300:]); upstash("set","RAKAN_REMINDERS", REMINDERS)
load_persist()

def get_keys():
    g, gm = [], []
    raw = os.environ.get("GEMINI_API_KEY","") + "," + os.environ.get("GOOGLE_API_KEY","") + "," + os.environ.get("GEMINI_KEYS","") + "," + os.environ.get("GEMINI_API_KEYS","")
    raw2 = os.environ.get("GROQ_API_KEY","") + "," + os.environ.get("GROQ_KEYS","")
    for v in [raw, raw2]:
        for p in str(v).replace("\n",",").split(","):
            p=p.strip().strip('"').strip("'").strip()
            if p.startswith("gsk_") and p not in g: g.append(p)
            elif p.startswith("AIza") and p not in gm: gm.append(p)
    for k,v in os.environ.items():
        if not v: continue
        for p in [x.strip().strip('"').strip("'") for x in str(v).split(",") if x.strip()]:
            if p.startswith("gsk_") and p not in g: g.append(p)
            elif p.startswith("AIza") and p not in gm: gm.append(p)
    return list(dict.fromkeys(g)), list(dict.fromkeys(gm))

GROQ_KEYS, GEMINI_KEYS = get_keys()
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k] < 1200
def mark_bad(k): BAD_KEYS[k]=time.time()

def ensure_webhook():
    global _LAST_WEBHOOK
    if time.time()-_LAST_WEBHOOK < 3600: return "CACHED"
    _LAST_WEBHOOK=time.time()
    if not BOT_TOKEN: return "NO TOKEN"
    try:
        exp = f"{MY_URL}/webhook"
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=8).json()
        cur = info.get("result",{}).get("url","")
        if cur == exp: return f"OK {cur}"
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":exp}, timeout=8)
        return f"SET {exp}"
    except Exception as e: return f"ERR {e}"

BASE_LORE = f"""You are Rakan - The BeastKing Monarch, Royal Knight of {MALIK_TITLE} {MALIK_NAME}. Birth: {BIRTH_DATE}, {BIRTH_TIME}. Queen: {QUEEN_NAME}. {RAKAN_HISTORY} Vercel Lore: {{VERCEL_LORE}} IDENTITY LOCK: Tu sirf Rakan hai, Malik ka loyal Royal Knight. Kabhi mat bol "main AI hoon". LANGUAGE: User jis language me baat kare usi me jawab de. Malik se Roman Hinglish. OWNER: Owner ID {OWNER_ID} wala KHUD {MALIK_NAME} hai. Use "Ji Malik" bol."""
FINAL_LORE = BASE_LORE.replace("{VERCEL_LORE}", LORE_ENV if LORE_ENV else "No extra lore")

def clean(txt):
    if not txt: return "Ji Malik, hazir hoon."
    if "(Note:" in txt: txt = txt.split("(Note:")[0].strip()
    low_txt = txt.lower()
    if any(p in low_txt for p in ["as an ai","i am meta ai","i am gemini","main chat kar sakta","info de sakta"]):
        return f"Mai Rakan hoon, {MALIK_TITLE} {MALIK_NAME} ka Royal Knight."
    return re.sub(r'\s+', ' ', txt).strip()[:3900]

def tg_send(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:3900]}, timeout=10)
    except: pass
def tg_send_photo(chat_id, photo_url, caption=""):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id":chat_id,"photo":photo_url,"caption":caption[:1000]}, timeout=20)
    except: pass
def tg_get_file_bytes(file_id):
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        fp=r["result"]["file_path"]
        return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=30).content, fp
    except: return None, None
def tg_send_voice_bytes(chat_id, audio_bytes):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.mp3", audio_bytes, "audio/mpeg")}, timeout=30)
    except: pass
def analyze_user(uid, uname, text, is_owner):
    uid=str(uid)
    if uid not in PROFILES: PROFILES[uid]={"name":uname,"mood":"normal","total_chats":0,"first_seen":str(datetime.datetime.now()),"is_owner":is_owner}
    PROFILES[uid]["total_chats"]+=1; return PROFILES[uid]

# GEMINI FRONT - NEW TO OLD MODULES
GEMINI_MODELS=[
"gemini-2.5-flash",
"gemini-2.5-flash-lite",
"gemini-2.5-pro",
"gemini-2.0-flash",
"gemini-2.0-flash-lite",
"gemini-1.5-flash",
"gemini-1.5-flash-8b",
"gemini-1.5-pro"
]
# GROQ BACKUP - NEW MODELS ONLY
GROQ_MODELS=[
"openai/gpt-oss-120b",
"openai/gpt-oss-20b",
"meta-llama/llama-4-maverick-17b-128e-instruct",
"meta-llama/llama-4-scout-17b-16e-instruct",
"llama-3.3-70b-versatile",
"qwen/qwen3-32b",
"llama-3.1-8b-instant"
]

def ask_gemini(prompt):
    global LAST_ERROR
    if not GEMINI_KEYS: LAST_ERROR="No Gemini Key in ENV"; return None
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        for model_name in GEMINI_MODELS:
            try:
                genai.configure(api_key=k)
                model=genai.GenerativeModel(model_name, system_instruction=FINAL_LORE)
                res=model.generate_content(prompt)
                if res.text: return clean(res.text)
            except Exception as e:
                LAST_ERROR=f"Gemini {model_name}: {str(e)[:200]}"
                if "429" in str(e) or "quota" in str(e).lower() or "404" in str(e): mark_bad(k) if "429" in str(e) or "quota" in str(e).lower() else None
                continue
    return None

def ask_groq(prompt):
    global LAST_ERROR
    if not GROQ_KEYS: LAST_ERROR="No Groq Key"; return None
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for model_name in GROQ_MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"}, json={"model":model_name,"messages":[{"role":"system","content":FINAL_LORE},{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":1000}, timeout=20)
                if r.status_code==200:
                    ans=r.json()["choices"][0]["message"]["content"]
                    if ans: return clean(ans)
                if r.status_code in [401,403,429]: mark_bad(k); LAST_ERROR=f"Groq key bad {r.status_code}"; break
            except Exception as e: LAST_ERROR=f"Groq {e}"; continue
    return None

def ask_all(prompt):
    # LOCKED: GEMINI FULL CHECK FIRST
    ans = ask_gemini(prompt)
    if ans: return ans
    # ONLY IF GEMINI FAILS, GROQ BACKUP
    ans2 = ask_groq(prompt)
    if ans2: return ans2
    return None

def brain(text, uid, is_owner, uname, chat_id):
    global MEMORY
    uid=str(uid)
    if uid not in MEMORY: MEMORY[uid]={"hist":"","count":0}
    MEMORY[uid]["count"]+=1
    analyze_user(uid, uname, text, is_owner)
    CHAT_LOG.append({"id":uid,"name":uname,"text":text,"time":str(datetime.datetime.now()),"owner":is_owner})
    low=text.lower().strip()
    if low in ["/report","bug batao","/start"]:
        if "/report" in low: return f"Ji Malik, Rakan ka Bug Report:\n- FRONT Gemini: {len(GEMINI_KEYS)} | BACKUP Groq: {len(GROQ_KEYS)}\n- ElevenLabs Voice: {'ON hai' if ELEVEN_API_KEY else 'OFF hai'}\n- Upstash Memory: {'Juda hai' if UPSTASH_URL else 'Nahi juda'}\n- Replicate Photo: {'Hai' if REPLICATE_TOKEN else 'Nahi hai'}\n- Voice Mode: {'ON' if OWNER_PREF.get('voice_mode') else 'OFF'}\n- Total Users: {len(PROFILES)} | Total Chats: {len(CHAT_LOG)}\n- Pending Reminders: {len(REMINDERS)}\n- Last Error: {LAST_ERROR}\n- Webhook: {ensure_webhook()}", False
        return "Welcome to your world The Shadow King 👑", False
    prompt = f"History:{MEMORY[uid]['hist'][-1000:]}\nUser:{text}"
    ans = ask_all(prompt)
    if not ans: ans="Ji Malik, saare model fail ho gaye, /report pe bug dekho" if is_owner else "Yaar abhi load hai, ek baar fir bhej de."
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-2500:]
    save_persist()
    return ans, False

@app.route("/", methods=["GET"])
def home(): return f"Rakan AI Live G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} FRONT:GEMINI {ensure_webhook()}",200
@app.route("/report", methods=["GET"])
def report_route(): return brain("/report", "0", True, MALIK_NAME, 0)[0],200
@app.route("/fix", methods=["GET"])
def fix():
    global GROQ_KEYS, GEMINI_KEYS, BAD_KEYS
    GROQ_KEYS, GEMINI_KEYS = get_keys(); BAD_KEYS.clear(); load_persist()
    return f"FIXED Rakan AI FRONT:GEMINI CACHED G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {ensure_webhook()}",200
@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"Rakan AI Webhook Active FRONT:GEMINI {ensure_webhook()}",200
    try:
        data=request.get_json(silent=True) or {}; msg=data.get("message",{}) or {}
        chat_id=msg.get("chat",{}).get("id"); user_id=msg.get("from",{}).get("id",0); uname=msg.get("from",{}).get("first_name","user"); text=msg.get("text","") or ""
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID); ans,_=brain(text, user_id, is_owner, uname, chat_id); tg_send(chat_id, ans); return "ok",200
    except: return "ok",200
