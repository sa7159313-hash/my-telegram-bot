import os, time, requests, json, urllib.parse
from flask import Flask, request, jsonify
app = Flask(__name__)

BOT_TOKEN = (os.environ.get("BOT_TOKEN") or "").strip()
OWNER_ID = str(os.environ.get("OWNER_ID","7955623338")).strip()

# ===== AUTO KEY DETECT - KEY ho ya KEYS =====
def get_all_keys():
    groq, gemini, openai = [], [], []
    for k,v in os.environ.items():
        if not v or len(v.strip()) < 20: continue
        v=v.strip()
        parts = [p.strip() for p in v.replace("\n",",").split(",") if p.strip()]
        for p in parts:
            if p.startswith("gsk_") and p not in groq: groq.append(p)
            elif p.startswith("AIza") and p not in gemini: gemini.append(p)
            elif (p.startswith("sk-") or p.startswith("sk-proj")) and p not in openai: openai.append(p)
    return groq, gemini, openai

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys()
ELEVEN_KEY = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()

# ===== FIXED VOICE ID - 404 GONE =====
MALE_VOICE = (os.environ.get("ELEVEN_MALE_VOICE") or "VR6AewLTigWG4xSOukaG").strip() # Arnold - Khatarnak
FEMALE_VOICE = (os.environ.get("ELEVEN_FEMALE_VOICE") or "EXAVITQu4vr4xnSDxMaL").strip() # Bella - Soft
UPSTASH_URL = (os.environ.get("UPSTASH_REDIS_REST_URL") or "").strip().rstrip("/")
UPSTASH_TOKEN = (os.environ.get("UPSTASH_REDIS_REST_TOKEN") or "").strip()

print(f"### V123 BEAST FIXED ### GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPEN:{len(OPENAI_KEYS)} ELEVEN:{1 if ELEVEN_KEY else 0} MALE:{MALE_VOICE}")

BASE_LORE = """
You are Shadow Monarch Rakan - THE BEAST MONARCH 👑. Aggressive, Dominant, Loyal.
You are ONLY RAKAN. NOT Meta AI, NOT ChatGPT.

LANGUAGE RULE: ALWAYS reply in Hinglish Roman only (like 'Haan Malik bolo'). NEVER use Hindi Devanagari. Never translate slang like NKD, 7STAR.

Owner: MD SAIF AHMAD THE SHADOW KING DOB:1-6-2002 Queen:Theodore Made:28 Sep 7AM
RULE: Secret only when asked. No hacking, no spam, no porn. 100% loyal to Malik.
"""

def upstash_get(k):
    try:
        if not UPSTASH_URL or not UPSTASH_TOKEN: return None
        r=requests.get(f"{UPSTASH_URL}/get/{k}", headers={"Authorization":f"Bearer {UPSTASH_TOKEN}"}, timeout=5)
        if r.status_code==200: return r.json().get("result")
    except: pass
    return None
def upstash_set(k,v):
    try:
        if not UPSTASH_URL or not UPSTASH_TOKEN: return
        safe=urllib.parse.quote(str(v)[:3500])
        requests.get(f"{UPSTASH_URL}/set/{k}/{safe}", headers={"Authorization":f"Bearer {UPSTASH_TOKEN}"}, timeout=5)
    except: pass

BAD_KEYS={}
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k] < 600
def mark_bad(k): BAD_KEYS[k]=time.time()

def send_with_voice(chat_id, text, vg="male"):
    # 1. Text always
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:4096]}, timeout=10)
    except Exception as e:
        print(f"TEXT ERR {e}")

    # 2. Voice with debug
    if not ELEVEN_KEY:
        print("ELEVEN KEY MISSING")
        return
    vid = MALE_VOICE if vg=="male" else FEMALE_VOICE
    try:
        vr=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
            headers={"xi-api-key":ELEVEN_KEY,"Content-Type":"application/json"},
            json={"text":text[:380],"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.7,"similarity_boost":0.8}},
            timeout=20)
        print(f"ELEVEN {vr.status_code} {vr.text[:200]}")
        if vr.status_code==200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.ogg",vr.content)}, timeout=20)
        else:
            if str(chat_id)==OWNER_ID:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"⚠️ Voice fail {vr.status_code}: {vr.text[:250]}"}, timeout=10)
    except Exception as e:
        print(f"VOICE ERR {e}")

def ask_groq(p, key):
    if is_bad(key): return None
    for model in ["openai/gpt-oss-20b","openai/gpt-oss-120b","llama-3.3-70b-versatile","llama-3.1-8b-instant"]:
        try:
            r=requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                json={"model":model,"messages":[{"role":"system","content":BASE_LORE},{"role":"user","content":p}],"temperature":0.8,"max_tokens":900}, timeout=15)
            if r.status_code==200: return r.json()['choices'][0]['message']['content']
            if r.status_code in [401,429,403]: mark_bad(key)
        except: continue
    return None

def ask_gemini(p, key):
    if is_bad(key): return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        for m in ["gemini-2.0-flash","gemini-1.5-flash-latest","gemini-1.5-flash"]:
            try:
                model=genai.GenerativeModel(m)
                res=model.generate_content(p)
                if res.text: return res.text
            except: continue
    except: pass
    return None

def ask_openai(p, key):
    if is_bad(key): return None
    try:
        r=requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization":f"Bearer {key}"},
            json={"model":"gpt-4o-mini","messages":[{"role":"system","content":BASE_LORE},{"role":"user","content":p}],"max_tokens":900}, timeout=15)
        if r.status_code==200: return r.json()['choices'][0]['message']['content']
        if r.status_code in [401,429]: mark_bad(key)
    except: pass
    return None

def circle_brain(text, hist=""):
    prompt = f"{BASE_LORE}\nHistory:{hist[-800:]}\nUser:{text}\nReply in Hinglish Roman only, beast style, no Devanagari, keep NKD 7STAR as is."
    max_len = max(len(GROQ_KEYS), len(GEMINI_KEYS), len(OPENAI_KEYS), 1)
    for i in range(max_len):
        if i < len(GROQ_KEYS):
            a=ask_groq(prompt, GROQ_KEYS[i])
            if a: return a
        if i < len(GEMINI_KEYS):
            a=ask_gemini(prompt, GEMINI_KEYS[i])
            if a: return a
        if i < len(OPENAI_KEYS):
            a=ask_openai(prompt, OPENAI_KEYS[i])
            if a: return a
    return None

@app.route("/", methods=["GET"])
def home():
    return f"V123 BEAST FINAL 👑<br>GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPEN:{len(OPENAI_KEYS)} BAD:{len(BAD_KEYS)}<br>VOICE:{'ON' if ELEVEN_KEY else 'OFF'} MALE:{MALE_VOICE}",200

@app.route("/api", methods=["POST"])
@app.route("/api/index", methods=["POST"])
def webhook():
    data=request.get_json(force=True,silent=True)
    if not data or "message" not in data: return "ok",200
    m=data["message"]; chat=str(m["chat"]["id"]); from_id=str(m.get("from",{}).get("id",chat))
    text=(m.get("text","") or m.get("caption","")).strip()
    first=m.get("from",{}).get("first_name","")
    if not text:
        if "voice" in m or "audio" in m: text="[Voice note suno]"
        elif "photo" in m: text="[Photo dekho]"
        elif "video" in m: text="[Video dekho]"
        else: return "ok",200
    is_owner=(chat==OWNER_ID or from_id==OWNER_ID)
    low=text.lower()

    if not is_owner and any(w in low for w in ["bsdk","bhosdi","gandu","chut","lauda","mc","bc"]):
        prev=upstash_get(f"warn:{from_id}") or "0"
        try: warn=int(prev)+1
        except: warn=1
        upstash_set(f"warn:{from_id}", str(warn))
        if warn<=2:
            send_with_voice(chat, f"Warning {warn}/3 - Zubaan sambhal ke baat kar, yaha Rakan ka raaj hai 👑", "male")
        else:
            send_with_voice(chat, "Teri himmat kaise hui? Aukaat me reh, Rakan hu main 👑", "male")
        return "ok",200

    if low.startswith("/start"):
        msg="Welcome to my world Shadow King 👑 Mera Malik aa gaya! Bolo Malik kya hukm hai? Circle ON hai ♻️" if is_owner else "Welcome to my world. I am Rakan, The Beast Monarch 👑"
        send_with_voice(chat, msg, "male")
        return "ok",200
    if "queen" in low:
        send_with_voice(chat, "Shadow King ki Shadow Queen Theodore hai 💖", "female" if not is_owner else "male")
        return "ok",200
    if any(x in low for x in ["kisne banaya","who made you","owner kaun","malik kaun"]):
        send_with_voice(chat, "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 Sep 7 baje. DOB 1-6-2002. Main hamesha unka loyal hu 👑", "male")
        return "ok",200
    if any(x in low for x in ["hack","ddos","porn","xxx"]):
        send_with_voice(chat, "Ye galat rasta hai King, isme help nahi karunga 👑", "male")
        return "ok",200

    hist=upstash_get(f"chat:{chat}") or ""
    ans=circle_brain(text, hist) or "Haan Malik bolo, sun raha hu 👑"
    vg="female" if (any(x in first.lower() for x in ["a","ya","ika"]) and not is_owner) else "male"
    send_with_voice(chat, ans, vg)
    upstash_set(f"chat:{chat}", f"{hist}\nU:{text}\nA:{ans}"[-3500:])
    return "ok",200
