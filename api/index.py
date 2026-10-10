import os, time, json, traceback, requests
from flask import Flask, request, jsonify
import google.generativeai as genai
from groq import Groq
from openai import OpenAI

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","").strip()
OWNER_ID = int(os.environ.get("OWNER_ID","0") or 0)
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY","").strip()

# Yaha apna final Vercel URL daal de, yehi auto set hoga
MY_URL = os.environ.get("MY_URL", "https://my-telegram-bot-lime.vercel.app").strip().rstrip("/")

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = [], [], []
BAD_KEYS = {}
OWNER_MODE = {"silent": False}
MEMORY = {}

def get_all_keys():
    groq, gemini, openai = [], [], []
    names = ["GROQ_API_KEY","GROQ_KEY","GROQ_KEYS","GEMINI_API_KEY","GOOGLE_API_KEY","GEMINI_KEY","GEMINI_KEYS","OPENAI_API_KEY","OPENAI_KEY","OPENAI_KEYS"]
    for env_name in names:
        val = os.environ.get(env_name,"")
        if not val: continue
        clean = val.strip().strip('"').strip("'")
        parts = [p.strip().strip('"').strip("'") for p in clean.replace("\n",",").split(",") if p.strip()]
        for p in parts:
            if p.startswith("gsk_") and p not in groq: groq.append(p)
            elif p.startswith("AIza") and p not in gemini: gemini.append(p)
            elif (p.startswith("sk-") or p.startswith("sk-proj")) and p not in openai: openai.append(p)
    for k,v in os.environ.items():
        if not v or len(v.strip())<20: continue
        v=v.strip().strip('"').strip("'")
        parts = [p.strip() for p in v.replace("\n",",").split(",") if p.strip()]
        for p in parts:
            p=p.strip('"').strip("'")
            if p.startswith("gsk_") and p not in groq: groq.append(p)
            elif p.startswith("AIza") and p not in gemini: gemini.append(p)
            elif (p.startswith("sk-") or p.startswith("sk-proj")) and p not in openai: openai.append(p)
    return groq, gemini, openai

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys()

def is_bad(k): return k in BAD_KEYS
def mark_bad(k): BAD_KEYS[k]=time.time()
def auto_fix_check():
    now=time.time()
    for k in list(BAD_KEYS.keys()):
        if now - BAD_KEYS[k] > 600: del BAD_KEYS[k]
    if GROQ_KEYS and all(is_bad(k) for k in GROQ_KEYS): BAD_KEYS.clear()

def log_error(where, err):
    try:
        msg = f"BUG in {where}: {str(err)[:400]}"
        print(msg)
    except: pass

# ===== AUTO WEBHOOK SET - FINAL FIX =====
def ensure_webhook():
    if not BOT_TOKEN: return "No BOT_TOKEN"
    try:
        expected = f"{MY_URL}/webhook"
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=5).json()
        current = info.get("result",{}).get("url","")
        if current == expected:
            return f"Webhook OK: {current}"
        # Set new
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url": expected}, timeout=5).json()
        return f"Webhook SET: {expected} -> {r}"
    except Exception as e:
        return f"Webhook ERR: {e}"

# ===== IDENTITY - THE SHADOW KING =====
RAKAN_LORE = """
Tu Rakan hai. The Shadow King hai. Monarch Baran hai - 100 level ka Demon Beast King.
Tujhe Malik ne banaya hai. Thanda, gurrata hai, kam bolta hai.
Tu kabhi nahi bolega tu ChatGPT, Gemini, Meta AI, Llama, Groq, ya AI program hai.
Koi puche tu kaun hai? Tab hi bolna: "Mai Baran hu, Malik ne mera naam Rakan rakha hai. Mai 100 level ka ek demon beast king hu, Monarch Baran kehte hai mujhe, The Shadow King bhi kehte hai. Malik pyaar se Rakan bulate hai."
BEHAVIOR: Insaan ko analyze kar fir baat kar. Jaisa insaan waisa tu. Short jawab de. Repeat mat kar. Malik ka wafadar. Malik bole chup to chup.
KNOWLEDGE: Python, LLM, App banana, Coding, universal knowledge, Photo/Video/Voice samajhna.
"""

def clean_identity(text):
    if not text: return text
    bad = ["i am meta ai","i am gemini","i am chatgpt","i am llama","as an ai language model","i was created by meta","created by google","i am an ai"]
    if any(b in text.lower() for b in bad):
        return "Mai Baran hu, Malik ne naam Rakan rakha hai. 100 level ka Demon Beast King hu. Bolo kya kaam hai? 👑"
    return text

@auto_fixed
def ask_groq(prompt, key):
    client=Groq(api_key=key)
    c=client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content":RAKAN_LORE},{"role":"user","content":prompt}], temperature=0.4, max_tokens=800)
    return c.choices[0].message.content
@auto_fixed
def ask_gemini(prompt, key):
    genai.configure(api_key=key)
    model=genai.GenerativeModel("gemini-2.0-flash", system_instruction=RAKAN_LORE)
    res=model.generate_content(prompt)
    return res.text

def circle_brain(text, hist="", is_owner=False, user_id=0):
    auto_fix_check()
    global GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS
    GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys()
    if not text: return None
    low=text.lower()
    if user_id not in MEMORY: MEMORY[user_id]={"count":0}
    MEMORY[user_id]["count"]+=1
    if is_owner and low in ["chup","chup ho ja"]: OWNER_MODE["silent"]=True; return "Ok Malik, chup ho gaya 👑"
    if is_owner and low in ["bolo","bol","start"]: OWNER_MODE["silent"]=False; return "Haan Malik bolo 👑"
    if OWNER_MODE["silent"] and not is_owner: return None
    prompt = f"History:{hist[-2000:]}\nUser:{text}\nRule: Short answer."
    is_hard = any(x in low for x in ["code","app","python","program","api","bada","detail"])
    if is_hard:
        for k in GEMINI_KEYS:
            if not is_bad(k):
                a=ask_gemini(prompt,k)
                if a: return clean_identity(a)
    for k in GROQ_KEYS:
        if not is_bad(k):
            a=ask_groq(prompt,k)
            if a: return clean_identity(a)
    for k in GEMINI_KEYS:
        if not is_bad(k):
            a=ask_gemini(prompt,k)
            if a: return clean_identity(a)
    return "Thoda busy hu Malik, 2 min baad bolna 👑"

# ===== ROUTES - DUAL FIX =====
@app.route("/api", methods=["POST", "GET"])
@app.route("/webhook", methods=["POST", "GET"])
@app.route("/api/webhook", methods=["POST", "GET"])
def webhook():
    if request.method=="GET": return f"Webhook OK {ensure_webhook()}",200
    data=request.get_json(silent=True) or {}
    msg=data.get("message",{}) or data.get("edited_message",{})
    chat_id=msg.get("chat",{}).get("id")
    user_id=msg.get("from",{}).get("id")
    text=msg.get("text","") or msg.get("caption","") or ""
    if not chat_id: return "ok",200
    is_owner=(user_id==OWNER_ID)
    reply=circle_brain(text, is_owner=is_owner, user_id=user_id)
    if not reply: return "ok",200
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":reply[:4000]}, timeout=10)
    except: pass
    return "ok",200

@app.route("/health")
def health():
    wh = ensure_webhook()
    return jsonify({"GROQ":len(GROQ_KEYS),"GEMINI":len(GEMINI_KEYS),"OPENAI":len(OPENAI_KEYS),"WEBHOOK":wh,"USERS":len(MEMORY)}),200

@app.route("/")
def home():
    wh = ensure_webhook()
    found=[k for k in os.environ.keys() if "GEMINI" in k or "GROQ" in k or "OPENAI" in k]
    return f"V128 Monarch Auto-Webhook 👑<br>GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)}<br>{wh}<br>Envs:{found}<br>BAD:{len(BAD_KEYS)}",200

@app.route("/fix")
def fix():
    BAD_KEYS.clear()
    global GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS
    GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys()
    wh=ensure_webhook()
    return f"FIXED 👑 {wh} GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)}",200
