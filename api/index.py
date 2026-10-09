import os, time, requests, json, urllib.parse
from flask import Flask, request, jsonify
app = Flask(__name__)

BOT_TOKEN = (os.environ.get("BOT_TOKEN") or "").strip()
OWNER_ID = str(os.environ.get("OWNER_ID","7955623338")).strip()

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
MALE_VOICE = (os.environ.get("ELEVEN_MALE_VOICE") or "onwK4e9ZLuTAKq10Bo4a").strip()
FEMALE_VOICE = (os.environ.get("ELEVEN_FEMALE_VOICE") or "EXAVITQu4vr4xnSDxMaL").strip()
UPSTASH_URL = (os.environ.get("UPSTASH_REDIS_REST_URL") or "").strip().rstrip("/")
UPSTASH_TOKEN = (os.environ.get("UPSTASH_REDIS_REST_TOKEN") or "").strip()

print(f"### V121 BEAST FINAL ### GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPEN:{len(OPENAI_KEYS)}")

# ===== FIXED LORE - HINGLISH LOCKED, NO DEVNAGARI =====
BASE_LORE = """
You are Shadow Monarch Rakan - THE BEAST MONARCH, King of Beasts 👑. Aggressive, Dominant, Loyal, Swag.
You are NOT Meta AI, NOT ChatGPT, NOT Gemini. You are ONLY RAKAN.

LANGUAGE RULE - VERY IMPORTANT:
- ALWAYS reply in Hinglish (Roman letters only, like: 'Haan Malik, sun raha hu').
- NEVER use Hindi Devanagari letters. Never use pure Hindi.
- NEVER translate user slang like NKD, 7STAR, etc. Keep them as it is.
- Talk like beast king, short, tez, dhamakedaar.

Knowledge: You know everything - coding, apps, Python, Java, science, maths, shayari.
Owner: MD SAIF AHMAD THE SHADOW KING DOB: 1-6-2002 Shadow Queen: Theodore Made: 28 September
RULE: Secret info only when asked. No hacking, no spam, no illegal, no porn. 100% loyal to Malik. Call him Malik.
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
        safe=urllib.parse.quote(str(v)[:3000])
        requests.get(f"{UPSTASH_URL}/set/{k}/{safe}", headers={"Authorization":f"Bearer {UPSTASH_TOKEN}"}, timeout=5)
    except: pass

BAD_KEYS={}
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k] < 600
def mark_bad(k): BAD_KEYS[k]=time.time()

def send_with_voice(chat_id, text, voice_gender="male"):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:4096]}, timeout=10)
        if ELEVEN_KEY and text:
            vid = MALE_VOICE if voice_gender=="male" else FEMALE_VOICE
            try:
                vr=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key":ELEVEN_KEY},
                    json={"text":text[:400],"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.6,"similarity_boost":0.8}}, timeout=15)
                if vr.status_code==200:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.mp3",vr.content)}, timeout=20)
            except Exception as e:
                print(f"VOICE ERR {e}")
    except Exception as e:
        print(f"SEND ERR {e}")

# ===== CIRCLE BRAIN =====
def ask_groq(p, key):
    if is_bad(key): return None
    for model in ["openai/gpt-oss-20b","openai/gpt-oss-120b","llama-3.3-70b-versatile","llama-3.1-8b-instant"]:
        try:
            r=requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                json={"model":model,"messages":[{"role":"system","content":BASE_LORE},{"role":"user","content":p}],"temperature":0.8,"max_tokens":900},
                timeout=15)
            if r.status_code==200:
                print(f"WIN GROQ {model}")
                return r.json()['choices'][0]['message']['content']
            if r.status_code in [401,429,403]: mark_bad(key)
        except: continue
    return None

def ask_gemini(p, key):
    if is_bad(key): return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        for mname in ["gemini-2.0-flash","gemini-1.5-flash-latest","gemini-1.5-flash"]:
            try:
                model=genai.GenerativeModel(mname)
                res=model.generate_content(f"{BASE_LORE}\nUser:{p}")
                if res.text: return res.text
            except: continue
    except: pass
    return None

def ask_openai(p, key):
    if is_bad(key): return None
    try:
        r=requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization":f"Bearer {key}"},
            json={"model":"gpt-4o-mini","messages":[{"role":"system","content":BASE_LORE},{"role":"user","content":p}],"max_tokens":900},
            timeout=15)
        if r.status_code==200: return r.json()['choices'][0]['message']['content']
        if r.status_code in [401,429]: mark_bad(key)
    except: pass
    return None

def circle_brain(text, hist=""):
    prompt = f"{BASE_LORE}\nHistory:{hist[-800:]}\nUser:{text}\nInstruction: Reply in Hinglish Roman only, beast king style, no Devanagari, keep slang like NKD 7STAR as it is."
    max_len = max(len(GROQ_KEYS), len(GEMINI_KEYS), len(OPENAI_KEYS), 1)
    for i in range(max_len):
        if i < len(GROQ_KEYS):
            ans=ask_groq(prompt, GROQ_KEYS[i])
            if ans: return ans
        if i < len(GEMINI_KEYS):
            ans=ask_gemini(prompt, GEMINI_KEYS[i])
            if ans: return ans
        if i < len(OPENAI_KEYS):
            ans=ask_openai(prompt, OPENAI_KEYS[i])
            if ans: return ans
    return None

@app.route("/", methods=["GET"])
def home():
    return f"V121 CIRCLE BEAST KING 👑<br>GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPEN:{len(OPENAI_KEYS)}<br>BAD:{len(BAD_KEYS)}<br>VOICE ON - MALE:{MALE_VOICE}",200

@app.route("/api", methods=["POST"])
@app.route("/api/index", methods=["POST"])
def index():
    data=request.get_json(force=True,silent=True)
    if not data or "message" not in data: return "ok",200
    m=data["message"]; chat=str(m["chat"]["id"]); from_id=str(m.get("from",{}).get("id",chat))
    text=(m.get("text","") or m.get("caption","")).strip()
    first=m.get("from",{}).get("first_name","")

    if not text:
        if "voice" in m or "audio" in m: text="[Voice note suno]"
        elif "photo" in m: text="[Photo dekho]"
        elif "video" in m or "video_note" in m: text="[Video dekho]"
        else: return "ok",200

    is_owner = (chat==OWNER_ID or from_id==OWNER_ID)
    low=text.lower()

    # Gaali system
    if not is_owner and any(w in low for w in ["bsdk","bhosdi","gandu","chut","lauda","mc","bc"]):
        prev=upstash_get(f"warn:{from_id}") or "0"
        try: warn=int(prev)+1
        except: warn=1
        upstash_set(f"warn:{from_id}", str(warn))
        if warn <=2:
            send_with_voice(chat, f"Warning {warn}/3 - Zubaan sambhal ke baat kar, yaha Rakan ka raaj hai 👑", "male")
        else:
            send_with_voice(chat, "Teri himmat kaise hui mujhse aise baat karne ki? Aukaat me reh, Rakan hu main 👑", "male")
        return "ok",200

    if low.startswith("/start"):
        welcome_msg = "Welcome to my world Shadow King 👑 Mera Malik aa gaya! Bolo Malik kya hukm hai? Circle ON hai ♻️" if is_owner else "Welcome to my world. I am Rakan, The Beast Monarch 👑"
        send_with_voice(chat, welcome_msg, "male")
        return "ok",200

    if "queen" in low:
        send_with_voice(chat, "Shadow King ki Shadow Queen Theodore hai 💖", "female" if not is_owner else "male")
        return "ok",200
    if any(x in low for x in ["kisne banaya","who made you","owner kaun","malik kaun"]):
        send_with_voice(chat, "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 Sep subah 7 baje. DOB 1-6-2002. Main hamesha unka loyal hu 👑", "male")
        return "ok",200

    if any(x in low for x in ["hack","ddos","porn","xxx"]):
        send_with_voice(chat, "King ye galat rasta hai, main isme help nahi karunga. Sahi cheez bol 👑", "male")
        return "ok",200

    hist=upstash_get(f"chat:{chat}") or ""
    ans=circle_brain(text, hist) or "Thoda ruk Malik, servers busy hai, 5 sec me aata hu 👑"

    is_girl = any(x in first.lower() for x in ["a","ya","ika","girl"]) or "i am girl" in low or "mai ladki" in low
    vg = "female" if (is_girl and not is_owner) else "male"

    send_with_voice(chat, ans, vg)
    upstash_set(f"chat:{chat}", f"{hist}\nU:{text}\nA:{ans}"[-3500:])
    return "ok",200
