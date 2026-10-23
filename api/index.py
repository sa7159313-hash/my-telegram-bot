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
MALIK_NAME="MD Saif Ahmad"; MALIK_TITLE="The Shadow King"
MEMORY={}; BAD_KEYS={}; LAST_ERROR="No error yet"; CHAT_LOG=[]; PROFILES={}; OWNER_PREF={"voice_mode":False}
_LAST_WEBHOOK=0

def get_keys_DEBUG():
    env_list=[]
    g, gm = [], []
    for k,v in os.environ.items():
        if not v: continue
        s=str(v).strip()
        has_groq = "gsk_" in s
        has_gem = "AIza" in s
        if k.startswith("GEMINI") or k.startswith("GROQ") or has_gem or has_groq:
            env_list.append(f"{k}: len={len(s)} hasAIza={has_gem} hasGsk={has_groq} start={s[:4]}..{s[-4:]}")
        if has_gem:
            for part in re.split(r'[\s,\n,"]+', s):
                p=part.strip()
                if p.startswith("AIza") and len(p)>30 and p not in gm: gm.append(p)
        if has_groq:
            for part in re.split(r'[\s,\n,"]+', s):
                p=part.strip()
                if p.startswith("gsk_") and len(p)>20 and p not in g: g.append(p)
    # Direct name se bhi try
    for direct_key in ["GEMINI_API_KEY","GOOGLE_API_KEY","GEMINI_KEY","GOOGLE_GEMINI_KEY"]:
        v=os.environ.get(direct_key,"")
        if v and v.strip().startswith("AIza") and v.strip() not in gm:
            gm.append(v.strip())
            env_list.append(f"FOUND DIRECT {direct_key}")
    return g, gm, env_list

def get_keys():
    g,gm,_ = get_keys_DEBUG()
    return g,gm

GROQ_KEYS, GEMINI_KEYS = get_keys()
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<1200
def mark_bad(k): BAD_KEYS[k]=time.time()
def ensure_webhook():
    global _LAST_WEBHOOK
    if time.time()-_LAST_WEBHOOK<3600: return "CACHED"
    _LAST_WEBHOOK=time.time()
    if not BOT_TOKEN: return "NO TOKEN"
    try:
        exp=f"{MY_URL}/webhook"
        info=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=8).json()
        cur=info.get("result",{}).get("url","")
        if cur==exp: return f"OK {cur}"
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":exp}, timeout=8)
        return f"SET {exp}"
    except Exception as e: return f"ERR {e}"

FINAL_LORE=f"You are Rakan - The BeastKing Monarch, Royal Knight of {MALIK_TITLE} {MALIK_NAME}. Vercel Lore: {LORE_ENV} You are only Rakan. Owner ID {OWNER_ID} is {MALIK_NAME}."
def clean(txt):
    if not txt: return "Ji Malik, hazir hoon."
    if "(Note:" in txt: txt=txt.split("(Note:")[0].strip()
    if any(p in txt.lower() for p in ["as an ai","i am meta ai","i am gemini"]): return f"Mai Rakan hoon, {MALIK_TITLE} {MALIK_NAME} ka Royal Knight."
    return re.sub(r'\s+',' ',txt).strip()[:3900]
def tg_send(chat_id,text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:3900]}, timeout=10)
    except: pass

GEMINI_MODELS=["gemini-2.5-flash","gemini-2.5-flash-lite","gemini-2.5-pro","gemini-2.0-flash","gemini-1.5-flash","gemini-1.5-flash-8b","gemini-1.5-pro"]
GROQ_MODELS=["openai/gpt-oss-120b","openai/gpt-oss-20b","meta-llama/llama-4-maverick-17b-128e-instruct","meta-llama/llama-4-scout-17b-16e-instruct","llama-3.3-70b-versatile","llama-3.1-8b-instant"]

def ask_gemini(prompt):
    global LAST_ERROR
    if not GEMINI_KEYS: LAST_ERROR="Gemini Key ENV me nahi"; return None
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        for model_name in GEMINI_MODELS:
            try:
                url=f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={k}"
                payload={"system_instruction":{"parts":[{"text":FINAL_LORE}]},"contents":[{"parts":[{"text":prompt}]}]}
                r=requests.post(url, json=payload, timeout=20)
                if r.status_code==200:
                    txt=r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    if txt: return clean(txt)
                else:
                    LAST_ERROR=f"Gemini {model_name} {r.status_code} {r.text[:100]}"
                    if r.status_code in [429,403]: mark_bad(k); break
            except Exception as e: LAST_ERROR=f"Gemini {model_name} {str(e)[:100]}"; continue
    return None

def ask_groq(prompt):
    global LAST_ERROR
    if not GROQ_KEYS: LAST_ERROR="Groq Key nahi"; return None
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for model_name in GROQ_MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization":f"Bearer {k}"}, json={"model":model_name,"messages":[{"role":"system","content":FINAL_LORE},{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":1000}, timeout=20)
                if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                if r.status_code in [401,403,429]: mark_bad(k); break
            except: continue
    return None

def ask_all(p): return ask_gemini(p) or ask_groq(p)
def brain(text,uid,is_owner,uname,chat_id):
    uid=str(uid)
    if uid not in MEMORY: MEMORY[uid]={"hist":"","count":0}
    low=text.lower().strip()
    if low in ["/report","/start","/fix"]:
        g,gm,envs = get_keys_DEBUG()
        return f"Bug Report:\n- FRONT Gemini:{len(gm)} | BACKUP Groq:{len(g)}\n- Last Error:{LAST_ERROR}\n- Webhook:{ensure_webhook()}\n- ENV DEBUG:\n"+"\n".join(envs[:20]), False
    ans=ask_all(f"Hist:{MEMORY[uid]['hist'][-800:]} User:{text}") or "Load hai, fir bhej"
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-2500:]
    return ans, False

@app.route("/", methods=["GET"])
def home():
    g,gm,_=get_keys_DEBUG()
    return f"Rakan Live FRONT:GEMINI G:{len(g)} GM:{len(gm)} {ensure_webhook()}",200

@app.route("/debug", methods=["GET"])
def debug():
    g,gm,envs = get_keys_DEBUG()
    all_keys = list(os.environ.keys())
    return f"G:{len(g)} GM:{len(gm)}\nAll ENV Names:{','.join([k for k in all_keys if 'GEMINI' in k or 'GROQ' in k or 'MY_URL' in k])}\nDetails:\n"+"\n".join(envs)+f"\nLAST:{LAST_ERROR}",200

@app.route("/fix", methods=["GET"])
def fix():
    global GROQ_KEYS,GEMINI_KEYS,BAD_KEYS
    GROQ_KEYS,GEMINI_KEYS,_ = get_keys_DEBUG()
    BAD_KEYS.clear()
    return f"FIXED FRONT:GEMINI G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} LAST:{LAST_ERROR}",200

@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"Webhook {ensure_webhook()}",200
    try:
        data=request.get_json(silent=True) or {}; msg=data.get("message",{}) or {}
        chat_id=msg.get("chat",{}).get("id"); user_id=msg.get("from",{}).get("id",0); uname=msg.get("from",{}).get("first_name","user"); text=msg.get("text","") or ""
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID); ans,_=brain(text,user_id,is_owner,uname,chat_id); tg_send(chat_id,ans); return "ok",200
    except: return "ok",200
