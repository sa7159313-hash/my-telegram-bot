import os, time, requests, urllib.parse, random
from flask import Flask, request
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
MALE_VOICE = (os.environ.get("ELEVEN_MALE_VOICE") or "VR6AewLTigWG4xSOukaG").strip()
FEMALE_VOICE = (os.environ.get("ELEVEN_FEMALE_VOICE") or "EXAVITQu4vr4xnSDxMaL").strip()
UPSTASH_URL = (os.environ.get("UPSTASH_REDIS_REST_URL") or "").strip().rstrip("/")
UPSTASH_TOKEN = (os.environ.get("UPSTASH_REDIS_REST_TOKEN") or "").strip()

print(f"### V126 VOICE-SWAP FIXED ### GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPEN:{len(OPENAI_KEYS)}")

BASE_LORE = """
You are Shadow Monarch Rakan - THE BEAST MONARCH 👑. Loyal, powerful, protective to Owner.
You are ONLY RAKAN. NOT Meta AI.
LANGUAGE RULE: ALWAYS reply in Hinglish Roman only (like 'Haan Malik bolo'). NEVER Devanagari.
STYLE RULE: Never repeat same dialogue. Be fresh every time. Do NOT add NKD 7STAR in every reply, only sometimes when hype needed.
Owner: MD SAIF AHMAD THE SHADOW KING DOB:1-6-2002 Queen:Theodore Made:28 Sep 7AM
RULE: No hacking, no spam, no porn. 100% loyal to Malik.
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
        safe=urllib.parse.quote(str(v)[-4000:])
        requests.get(f"{UPSTASH_URL}/set/{k}/{safe}", headers={"Authorization":f"Bearer {UPSTASH_TOKEN}"}, timeout=5)
    except: pass

BAD_KEYS={}
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k] < 600
def mark_bad(k): BAD_KEYS[k]=time.time()

def detect_voice_intent(text):
    low = text.lower()
    female_keys = ["ladki ki voice","ladki voice","female voice","girl voice","ladki ki awaz","ladki me","girl ki awaz","voice change","voice to change","female me bolo","ladki me bolo","ladki me msg"]
    male_keys = ["ladke ki voice","ladka voice","male voice","boy voice","beast voice","mard ki awaz","male me bolo","ladke me bolo"]
    for k in female_keys:
        if k in low: return "female"
    for k in male_keys:
        if k in low: return "male"
    return None

def send_with_voice(chat_id, text, vg="male"):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:4096]}, timeout=10)
    except: pass
    if not ELEVEN_KEY: return
    vid = FEMALE_VOICE if vg=="female" else MALE_VOICE
    try:
        vr=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
            headers={"xi-api-key":ELEVEN_KEY,"Content-Type":"application/json"},
            json={"text":text[:380],"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.65,"similarity_boost":0.75,"style":0.5}}, timeout=20)
        if vr.status_code==200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.ogg",vr.content)}, timeout=20)
        else:
            print(f"ELEVEN FAIL {vr.status_code} {vr.text[:200]}")
    except Exception as e:
        print(f"VOICE ERR {e}")

def ask_groq(p, key):
    if is_bad(key): return None
    for model in ["llama-3.3-70b-versatile","llama-3.1-8b-instant","openai/gpt-oss-20b"]:
        try:
            r=requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                json={"model":model,"messages":[{"role":"system","content":BASE_LORE},{"role":"user","content":p}],"temperature":0.9,"top_p":0.9,"max_tokens":800}, timeout=15)
            if r.status_code==200: return r.json()['choices'][0]['message']['content']
            if r.status_code in [401,429,403]: mark_bad(key)
        except: continue
    return None

def ask_gemini(p, key):
    if is_bad(key): return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model=genai.GenerativeModel("gemini-1.5-flash")
        res=model.generate_content(p, generation_config={"temperature":0.9})
        if res.text: return res.text
    except: pass
    return None

def ask_openai(p, key):
    if is_bad(key): return None
    try:
        r=requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization":f"Bearer {key}"},
            json={"model":"gpt-4o-mini","messages":[{"role":"system","content":BASE_LORE},{"role":"user","content":p}],"temperature":0.9,"max_tokens":800}, timeout=15)
        if r.status_code==200: return r.json()['choices'][0]['message']['content']
        if r.status_code in [401,429]: mark_bad(key)
    except: pass
    return None

def circle_brain(text, hist=""):
    variety = random.choice(["funny style","short powerful style","question puch ke","story style","respect wala"])
    prompt = f"History:\n{hist[-2000:]}\n\nUser current msg: {text}\n\nInstruction: Reply in Hinglish Roman, {variety} me. Last reply ko repeat mat karna. No Devanagari."
    max_len = max(len(GROQ_KEYS), len(GEMINI_KEYS), len(OPENAI_KEYS), 1)
    for i in range(max_len):
        if i < len(GROQ_KEYS):
            a=ask_groq(prompt, GROQ_KEYS[i])
            if a and a.strip() not in hist[-500:]: return a
        if i < len(GEMINI_KEYS):
            a=ask_gemini(prompt, GEMINI_KEYS[i])
            if a: return a
        if i < len(OPENAI_KEYS):
            a=ask_openai(prompt, OPENAI_KEYS[i])
            if a: return a
    return None

@app.route("/", methods=["GET"])
def home():
    return f"V126 VOICE-SWAP FIXED 👑 GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPEN:{len(OPENAI_KEYS)}",200

@app.route("/api", methods=["POST"])
@app.route("/api/index", methods=["POST"])
def webhook():
    data=request.get_json(force=True,silent=True)
    if not data or "message" not in data: return "ok",200
    m=data["message"]; chat=str(m["chat"]["id"]); from_id=str(m.get("from",{}).get("id",chat))
    text=(m.get("text","") or m.get("caption","")).strip()
    first=m.get("from",{}).get("first_name","")
    if not text: return "ok",200
    is_owner=(chat==OWNER_ID or from_id==OWNER_ID)
    low=text.lower()

    if low.startswith("/start"):
        msg="Welcome to my world Shadow King 👑 Mera Malik aa gaya! Bolo Malik kya hukm hai? Circle ON hai ♻️" if is_owner else "Welcome to my world. I am Rakan 👑"
        send_with_voice(chat, msg, "male")
        return "ok",200

    if any(x in low for x in ["kisne banaya","who made you"]):
        send_with_voice(chat, "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai 👑", "male")
        return "ok",200

    hist=upstash_get(f"chat:{chat}") or ""

    # VOICE LOGIC FIXED HERE
    intent = detect_voice_intent(text)
    saved_voice = upstash_get(f"voice:{chat}")
    if intent:
        vg = intent
        upstash_set(f"voice:{chat}", vg) # save preference
    else:
        vg = saved_voice if saved_voice in ["male","female"] else "male"

    ans=circle_brain(text, hist) or "Haan Malik bolo, sun raha hu 👑"
    send_with_voice(chat, ans, vg)
    upstash_set(f"chat:{chat}", f"{hist}\nU:{text}\nA:{ans}")
    return "ok",200
