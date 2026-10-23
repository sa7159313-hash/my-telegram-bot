import os, time, json, re, datetime, requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = int(os.environ.get("OWNER_ID","0") or 0)
MY_URL = (os.environ.get("MY_URL","") or "https://my-telegram-bot-lime.vercel.app").rstrip("/")
LORE_ENV = os.environ.get("THE_BEAST_KING_MONARCH_AKAAN_LORE","")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MALIK_NAME = "MD Saif Ahmad"
MALIK_TITLE = "The Shadow King"
RAKAN_HISTORY = "Janam 24 September 2025 Subah 7 baje, Malik ne banaya."
MEMORY = {}; ABUSE = {}; PROFILES = {}; CHAT_LOG = []; BAD_KEYS = {}; LAST_ERROR = "No error yet"; REMINDERS = []
OWNER_PREF = {"voice_mode": False, "voice_gender": "female"}
_LAST_WEBHOOK = 0

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
            requests.post(f"{UPSTASH_URL}", headers=headers, json=["SET", key, json.dumps(val)], timeout=5)
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
    upstash("set","RAKAN_LOGS", CHAT_LOG[-300:])

load_persist()

def get_keys():
    g, gm = [], []
    for k,v in os.environ.items():
        if not v: continue
        s = str(v)
        if "AIza" in s:
            for part in re.split(r'[\s,\n,]+', s):
                p = part.strip().strip('"').strip("'")
                if p.startswith("AIza") and len(p) > 30 and p not in gm: gm.append(p)
        if "gsk_" in s:
            for part in re.split(r'[\s,\n,]+', s):
                p = part.strip().strip('"').strip("'")
                if p.startswith("gsk_") and len(p) > 20 and p not in g: g.append(p)
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

FINAL_LORE = f"You are Rakan - The BeastKing Monarch, Royal Knight of {MALIK_TITLE} {MALIK_NAME}. {RAKAN_HISTORY} Vercel Lore: {LORE_ENV} You are only Rakan. User language = your language. Owner ID {OWNER_ID} is {MALIK_NAME}."

def clean(txt):
    if not txt: return "Ji Malik, hazir hoon."
    if "(Note:" in txt: txt = txt.split("(Note:")[0].strip()
    low = txt.lower()
    if any(p in low for p in ["as an ai","i am meta ai","i am gemini"]): return f"Mai Rakan hoon, {MALIK_TITLE} {MALIK_NAME} ka Royal Knight."
    return re.sub(r'\s+', ' ', txt).strip()[:3900]

def tg_send(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:3900]}, timeout=10)
    except: pass

# === NEW TO OLD - GEMINI FRONT ===
GEMINI_MODELS=[
"gemini-2.5-flash",
"gemini-2.5-flash-lite",
"gemini-2.5-pro",
"gemini-2.0-flash",
"gemini-2.0-flash-lite",
"gemini-2.0-flash-exp",
"gemini-1.5-flash",
"gemini-1.5-flash-8b",
"gemini-1.5-pro"
]
# GROQ BACKUP - NEW MODULES
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
    if not GEMINI_KEYS: LAST_ERROR="Gemini Key ENV me nahi"; return None
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        for model_name in GEMINI_MODELS:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={k}"
                payload = {"system_instruction": {"parts": [{"text": FINAL_LORE}]}, "contents": [{"parts": [{"text": prompt}]}]}
                r = requests.post(url, json=payload, timeout=20)
                if r.status_code==200:
                    txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    if txt: return clean(txt)
                else:
                    LAST_ERROR = f"Gemini {model_name} {r.status_code} {r.text[:100]}"
                    if r.status_code in [429,403]: mark_bad(k); break
            except Exception as e:
                LAST_ERROR=f"Gemini {model_name} {str(e)[:100]}"; continue
    return None

def ask_groq(prompt):
    global LAST_ERROR
    if not GROQ_KEYS: LAST_ERROR="Groq Key nahi"; return None
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for model_name in GROQ_MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"}, json={"model":model_name,"messages":[{"role":"system","content":FINAL_LORE},{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":1000}, timeout=20)
                if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                if r.status_code in [401,403,429]: mark_bad(k); LAST_ERROR=f"Groq {r.status_code}"; break
            except: continue
    return None

def ask_all(prompt):
    ans = ask_gemini(prompt)  # PEHLE GEMINI KE SAARE MODULE NEW SE OLD
    if ans: return ans
    return ask_groq(prompt)   # TABHI GROQ BACKUP

def brain(text, uid, is_owner, uname, chat_id):
    uid=str(uid)
    if uid not in MEMORY: MEMORY[uid]={"hist":"","count":0}
    MEMORY[uid]["count"]+=1
    if uid not in PROFILES: PROFILES[uid]={"name":uname,"total_chats":0}
    PROFILES[uid]["total_chats"]+=1
    CHAT_LOG.append({"id":uid,"text":text,"time":str(datetime.datetime.now())})
    low=text.lower().strip()
    if low in ["/report","/start"]:
        return f"Bug Report:\n- FRONT Gemini: {len(GEMINI_KEYS)} | BACKUP Groq: {len(GROQ_KEYS)}\n- Last Error: {LAST_ERROR}\n- Webhook: {ensure_webhook()}\n- Models Front: {GEMINI_MODELS[0]} -> {GEMINI_MODELS[-1]}\n- Models Backup: {GROQ_MODELS[0]} -> {GROQ_MODELS[-1]}", False
    prompt = f"History:{MEMORY[uid]['hist'][-1000:]}\nUser:{text}"
    ans = ask_all(prompt)
    if not ans: ans="Ji Malik, saare model fail ho gaye, /report pe bug dekho" if is_owner else "Yaar abhi load hai, ek baar fir bhej de."
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-2500:]
    save_persist()
    return ans, False

@app.route("/", methods=["GET"])
def home(): return f"Rakan Live FRONT:GEMINI G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {ensure_webhook()}",200
@app.route("/report", methods=["GET"])
def report_route(): return brain("/report","0",True,MALIK_NAME,0)[0],200
@app.route("/fix", methods=["GET"])
def fix():
    global GROQ_KEYS, GEMINI_KEYS, BAD_KEYS
    GROQ_KEYS, GEMINI_KEYS = get_keys(); BAD_KEYS.clear()
    return f"FIXED FRONT:GEMINI G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} LAST:{LAST_ERROR}",200
@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"Webhook FRONT:GEMINI {ensure_webhook()}",200
    try:
        data=request.get_json(silent=True) or {}; msg=data.get("message",{}) or {}
        chat_id=msg.get("chat",{}).get("id"); user_id=msg.get("from",{}).get("id",0); uname=msg.get("from",{}).get("first_name","user"); text=msg.get("text","") or ""
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID); ans,_=brain(text, user_id, is_owner, uname, chat_id); tg_send(chat_id, ans); return "ok",200
    except: return "ok",200
