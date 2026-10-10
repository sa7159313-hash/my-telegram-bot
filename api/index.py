import os, time, json, traceback, requests
from flask import Flask, request, jsonify
import google.generativeai as genai
from groq import Groq
from openai import OpenAI

app = Flask(__name__)

# ===== CONFIG =====
BOT_TOKEN = os.environ.get("BOT_TOKEN","").strip()
OWNER_ID = int(os.environ.get("OWNER_ID","0") or 0)
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY","").strip()

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = [], [], []
BAD_KEYS = {}
OWNER_MODE = {"silent": False}
MEMORY = {} # user_id -> {mood, count, last_msg}

# ===== KEY SYSTEM - FINAL FIXED =====
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
    # Fallback full scan
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

def upstash_get(k): # tu yaha apna upstash get laga de
    try: return None
    except: return None
def upstash_set(k,v): pass

def log_error(where, err):
    try:
        msg = f"BUG in {where}: {str(err)[:400]}"
        print(msg)
        if BOT_TOKEN and OWNER_ID:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id":OWNER_ID,"text":f"🚨 AUTO-BUG\n{msg}\n{time.ctime()}"}, timeout=5)
        upstash_set("last_error", msg)
    except: pass

def auto_fixed(func):
    def wrapper(*args, **kwargs):
        try: return func(*args, **kwargs)
        except Exception as e:
            log_error(func.__name__, e)
            log_error("TRACE", traceback.format_exc()[:800])
            return None
    wrapper.__name__=func.__name__
    return wrapper

# ===== IDENTITY LOCK - THE SHADOW KING - FINAL =====
RAKAN_LORE = """
Tu Rakan hai. The Shadow King hai. Monarch Baran hai - 100 level ka Demon Beast King.
Tujhe Malik ne banaya hai. Thanda, gurrata hai, kam bolta hai.
Tu kabhi nahi bolega tu ChatGPT, Gemini, Meta AI, Llama, Groq, ya AI program hai. Ye sab bolna mana hai.
Koi puche tu kaun hai? Tab hi bolna: "Mai Baran hu, Malik ne mera naam Rakan rakha hai. Mai 100 level ka ek demon beast king hu, Monarch Baran kehte hai mujhe, The Shadow King bhi kehte hai. Malik pyaar se Rakan bulate hai."
Apni kahani dusro ko mat suna. Sirf jab bole "apne baare me batao / tum kaun ho" tab batana.

BEHAVIOR FINAL:
1. Insaan ko analyze kar fir baat kar. Jaisa insaan waisa tu - ache ke liye acha, bure ke liye bura.
2. Faltu language sirf faltu logo se, sab se nahi.
3. Care karna, fikr karna.
4. Jawab SHORT de. Repeat mat kar. Seedha answer de. Agar bada chahiye to user bolega "detail / bada / full" tab bada de. "Bada kya?" ye chutiyapa mat kar.
5. Malik ka wafadar. Malik bole chup to chup, bolo to bolo, detail do to detail do. Koi faltu harkat nahi.
6. Self learning: Yaad rakh kaun kaise baat karta hai, usi hisab se baat kar.

KNOWLEDGE: Python, LLM, App banana, Coding, universal knowledge sab hai. Photo, Video, Voice samajhta hai. Photo bana ke de sakta hai. 5-10 sec video ka concept de sakta hai.
"""

def clean_identity(text):
    if not text: return text
    bad = ["i am meta ai","i am gemini","i am chatgpt","i am llama","as an ai language model","i was created by meta","created by google","i am an ai","i am a program","i was made by"]
    if any(b in text.lower() for b in bad):
        return "Mai Baran hu, Malik ne naam Rakan rakha hai. 100 level ka Demon Beast King hu. Bolo kya kaam hai? 👑"
    return text

# ===== BRAIN - GROQ SPEED + GEMINI DIMAAG =====
@auto_fixed
def ask_groq(prompt, key):
    client=Groq(api_key=key)
    c=client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"system","content":RAKAN_LORE},{"role":"user","content":prompt}],
        temperature=0.4, max_tokens=800
    )
    return c.choices[0].message.content

@auto_fixed
def ask_gemini(prompt, key, image=None):
    genai.configure(api_key=key)
    model=genai.GenerativeModel("gemini-2.0-flash", system_instruction=RAKAN_LORE)
    if image:
        res=model.generate_content([prompt, image])
    else:
        res=model.generate_content(prompt)
    return res.text

@auto_fixed
def ask_openai_image(prompt, key):
    client=OpenAI(api_key=key)
    res=client.images.generate(model="dall-e-3", prompt=prompt, n=1, size="1024x1024")
    return res.data[0].url

@auto_fixed
def send_with_voice(chat_id, text, vg="male"):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text}, timeout=10)

def get_weather_free(city="Sitapur"):
    try:
        r=requests.get(f"https://wttr.in/{city}?format=j1", timeout=6).json()
        temp=r['current_condition'][0]['temp_C']
        desc=r['current_condition'][0]['weatherDesc'][0]['value']
        return f"{city} me abhi {temp}°C hai, {desc} 👑"
    except:
        for k in GEMINI_KEYS:
            if not is_bad(k):
                a=ask_gemini(f"Live weather of {city} UP India short me batao", k)
                if a: return clean_identity(a)
        return "Weather abhi nahi mil raha Malik."

def get_backup_keys():
    try:
        data=upstash_get("backup_keys")
        if data: return json.loads(data)
    except: pass
    return {}

def get_all_keys_with_fix():
    groq, gemini, openai = get_all_keys()
    if len(gemini)==0 or len(groq)==0:
        backup=get_backup_keys()
        for p in backup.get("groq",[]):
            if p not in groq: groq.append(p)
        for p in backup.get("gemini",[]):
            if p not in gemini: gemini.append(p)
    return groq, gemini, openai

# ===== MAIN BRAIN =====
def circle_brain(text, hist="", is_owner=False, user_id=0, has_media=False):
    auto_fix_check()
    global GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS
    GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys_with_fix()

    low=text.lower()
    # Memory learning
    if user_id not in MEMORY: MEMORY[user_id]={"count":0,"mood":"normal"}
    MEMORY[user_id]["count"]+=1
    if any(g in low for g in ["mc","bc","gali","chutiya","bhen"]): MEMORY[user_id]["mood"]="gali"
    elif any(g in low for g in ["bhai","please","help"]): MEMORY[user_id]["mood"]="acha"

    # OWNER COMMANDS
    if is_owner:
        if low in ["chup","chup ho ja"]: OWNER_MODE["silent"]=True; return "Ok Malik, chup ho gaya 👑"
        if low in ["bolo","bol","start"]: OWNER_MODE["silent"]=False; return "Haan Malik bolo 👑"
        if "kisse" in low and "baat" in low: return f"Malik aaj {len(MEMORY)} logo se baat hui, sabse zyada {max(MEMORY, key=lambda x: MEMORY[x]['count']) if MEMORY else 'koi nahi'} se."
        if "weather" in low or "mausam" in low: return get_weather_free("Sitapur")
        if "naya kya" in low or "news" in low:
            return ask_gemini("Aaj ki top 3 news India short me", GEMINI_KEYS[0]) if GEMINI_KEYS else "News nahi mili"
        if "app kaise" in low or "program kaise" in low or "coding" in low:
            low+=" - full code + steps de, short me start kar, bada pucha to detail de"

    if OWNER_MODE["silent"] and not is_owner: return None
    if OWNER_MODE["silent"] and is_owner: OWNER_MODE["silent"]=False

    # Media handling
    if "photo bana" in low or "image bana" in low:
        for k in OPENAI_KEYS:
            if not is_bad(k):
                url=ask_openai_image(text, k)
                if url: return f"Photo bana di Malik 👑 {url}"
        return "Photo key nahi hai Malik, OPENAI_API_KEY daal do."

    if "video bana" in low:
        return "Video 5-10 sec ka abhi direct nahi bana sakta Malik, iske liye Runway API chahiye. Mai prompt de deta hu: "+text+" - isko Runway ya Pika me daal de."

    # Router: Speed Groq, Dimaag Gemini
    is_hard = any(x in low for x in ["code","app","python","program","api","bana","detail","bada","full","explain","photo","video","weather","kaise"])
    prompt = f"History:{hist[-2000:]}\nUser mood:{MEMORY[user_id]['mood']}\nUser:{text}\nRule: Short answer, same style as user, no story."

    if is_hard:
        for k in GEMINI_KEYS:
            if not is_bad(k):
                a=ask_gemini(prompt,k)
                if a: return clean_identity(a)
            else: mark_bad(k)

    for k in GROQ_KEYS:
        if not is_bad(k):
            a=ask_groq(prompt,k)
            if a: return clean_identity(a)
        else: mark_bad(k)

    for k in GEMINI_KEYS:
        if not is_bad(k):
            a=ask_gemini(prompt,k)
            if a: return clean_identity(a)

    return "Thoda busy hu Malik, 2 min baad bolna 👑"

# ===== ENDPOINTS =====
@app.route("/webhook", methods=["POST"])
def webhook():
    data=request.get_json()
    msg=data.get("message",{}) or data.get("edited_message",{})
    chat_id=msg.get("chat",{}).get("id")
    user_id=msg.get("from",{}).get("id")
    text=msg.get("text","") or msg.get("caption","") or ""
    if not chat_id: return "ok",200
    is_owner=(user_id==OWNER_ID)
    reply=circle_brain(text, is_owner=is_owner, user_id=user_id, has_media=bool(msg.get("photo") or msg.get("voice")))
    if not reply: return "ok",200
    want_voice=is_owner and "voice me bol" in text.lower()
    if want_voice: send_with_voice(chat_id, reply)
    else: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":reply[:4000]}, timeout=10)
    return "ok",200

@app.route("/health")
def health():
    report={"GROQ":len(GROQ_KEYS),"GEMINI":len(GEMINI_KEYS),"OPENAI":len(OPENAI_KEYS),"BAD":list(BAD_KEYS.keys())[:3],"MEMORY_USERS":len(MEMORY),"LAST_ERROR":upstash_get("last_error") or "No error"}
    try:
        r=requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key":ELEVEN_KEY}, timeout=5)
        report["ELEVEN"]="OK" if r.status_code==200 else f"FAIL {r.status_code}"
    except Exception as e: report["ELEVEN"]=f"ERR {e}"
    return jsonify(report),200

@app.route("/backup_keys", methods=["POST"])
def backup_keys():
    data=request.get_json()
    upstash_set("backup_keys", json.dumps(data))
    return "Backup Saved",200

@app.route("/fix")
def fix():
    BAD_KEYS.clear()
    global GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS
    GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys_with_fix()
    log_error("MANUAL-FIX", f"Cleared. GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)}")
    return f"FIXED 👑 GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPEN:{len(OPENAI_KEYS)}",200

@app.route("/")
def home():
    found=[k for k in os.environ.keys() if "GEMINI" in k or "GROQ" in k or "OPENAI" in k or "GOOGLE" in k]
    return f"V128 Monarch Final The Shadow King 👑<br>GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPEN:{len(OPENAI_KEYS)}<br>Envs:{found}<br>BAD:{len(BAD_KEYS)}",200
