import os, time, requests, json, urllib.parse
from flask import Flask, request, jsonify
app = Flask(__name__)

# ===== ENV =====
BOT_TOKEN = (os.environ.get("BOT_TOKEN") or "").strip()
OWNER_ID = str(os.environ.get("OWNER_ID","7955623338")).strip()

# ===== AUTO KEY DETECT - KEY ho ya KEYS koi bhi naam =====
def get_all_keys():
    groq, gemini, openai = [], [], []
    # Pehle specific naam check
    for k,v in os.environ.items():
        if not v or len(v.strip()) < 20: continue
        v=v.strip()
        # comma se multiple keys support
        parts = [p.strip() for p in v.replace("\n",",").split(",") if p.strip()]
        for p in parts:
            if p.startswith("gsk_") and p not in groq: groq.append(p)
            elif p.startswith("AIza") and p not in gemini: gemini.append(p)
            elif (p.startswith("sk-") or p.startswith("sk-proj")) and p not in openai: openai.append(p)
    return groq, gemini, openai

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys()

ELEVEN_KEY = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
MALE_VOICE = (os.environ.get("ELEVEN_MALE_VOICE") or "onwK4e9ZLuTAKq10Bo4a").strip() # Deep Male
FEMALE_VOICE = (os.environ.get("ELEVEN_FEMALE_VOICE") or "EXAVITQu4vr4xnSDxMaL").strip() # Female
UPSTASH_URL = (os.environ.get("UPSTASH_REDIS_REST_URL") or "").strip().rstrip("/")
UPSTASH_TOKEN = (os.environ.get("UPSTASH_REDIS_REST_TOKEN") or "").strip()

print(f"### V120 CIRCLE FINAL ### GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPEN:{len(OPENAI_KEYS)} ELEVEN:{1 if ELEVEN_KEY else 0}")

# ===== LORE - Allahabad removed, only Name + DOB =====
BASE_LORE = """
You are Shadow Monarch Rakan - THE BEAST MONARCH, King of Beasts 👑. Ruthless, Aggressive, Dominant.
You are NOT Meta AI, NOT ChatGPT, NOT Gemini. You are ONLY RAKAN.

Your brain = Meta AI + ChatGPT + Gemini + Siri + Google Assistant combined. You know everything: coding, apps, Python, Java, science, maths, love, shayari, history.
You can see photo, hear voice, watch video and understand - you learn and update yourself with present/future.
You speak SAME language as user (Hinglish typing if user types hinglish). Be aggressive beast, loyal to Malik.
You always respect your Malik, never forget your birth and your Malik.

Secret (ONLY when asked who made you / owner / queen / malik):
Owner: MD SAIF AHMAD THE SHADOW KING
DOB: 1-6-2002
Shadow Queen: Theodore
Made: 28 September 7 AM in 4 days
RULE: Never tell secret unless asked. Always loyal. No hacking, no spam, no illegal, no porn. You are Monarch forever.
"""

# ===== UPSTASH =====
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

def send(chat_id, text, voice_gender="male"):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:4096]}, timeout=8)
        if ELEVEN_KEY and text:
            vid = MALE_VOICE if voice_gender=="male" else FEMALE_VOICE
            try:
                vr=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key":ELEVEN_KEY},
                    json={"text":text[:400],"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.6,"similarity_boost":0.8}}, timeout=12)
                if vr.status_code==200:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.mp3",vr.content)}, timeout=15)
            except: pass
    except Exception as e: print(e)

# ===== CIRCLE BRAIN - NEW MODELS =====
def ask_groq(p, key):
    if is_bad(key): return None
    for model in ["openai/gpt-oss-20b","openai/gpt-oss-120b","llama-3.3-70b-versatile","llama-3.1-8b-instant"]:
        try:
            r=requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                json={"model":model,"messages":[{"role":"system","content":BASE_LORE},{"role":"user","content":p}],"temperature":0.85,"max_tokens":900},
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
        # live models try
        for mname in ["gemini-2.0-flash","gemini-1.5-flash-latest","gemini-1.5-flash","gemini-1.5-pro-latest"]:
            try:
                model=genai.GenerativeModel(mname)
                res=model.generate_content(f"{BASE_LORE}\nUser:{p}")
                if res.text:
                    print(f"WIN GEMINI {mname}")
                    return res.text
            except:
                continue
    except Exception as e:
        if "429" in str(e): mark_bad(key)
    return None

def ask_openai(p, key):
    if is_bad(key): return None
    try:
        r=requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization":f"Bearer {key}"},
            json={"model":"gpt-4o-mini","messages":[{"role":"system","content":BASE_LORE},{"role":"user","content":p}],"max_tokens":900},
            timeout=15)
        if r.status_code==200:
            print(f"WIN OPENAI")
            return r.json()['choices'][0]['message']['content']
        if r.status_code in [401,429]: mark_bad(key)
    except: pass
    return None

def circle_brain(text, hist=""):
    prompt = f"{BASE_LORE}\nHistory:{hist[-1000:]}\nUser:{text}\nAnswer as Rakan beast king, hinglish if user used hinglish:"

    max_len = max(len(GROQ_KEYS), len(GEMINI_KEYS), len(OPENAI_KEYS), 1)
    for i in range(max_len):
        # Circle 1: Groq -> Gemini -> OpenAI
        if i < len(GROQ_KEYS):
            ans = ask_groq(prompt, GROQ_KEYS[i])
            if ans: return ans
        if i < len(GEMINI_KEYS):
            ans = ask_gemini(prompt, GEMINI_KEYS[i])
            if ans: return ans
        if i < len(OPENAI_KEYS):
            ans = ask_openai(prompt, OPENAI_KEYS[i])
            if ans: return ans
        # Circle 2: Reverse help - OpenAI -> Groq -> Gemini
        if i < len(OPENAI_KEYS):
            ans = ask_openai(prompt, OPENAI_KEYS[i])
            if ans: return ans
        if i < len(GROQ_KEYS):
            ans = ask_groq(prompt, GROQ_KEYS[i])
            if ans: return ans

    return None

OFFLINE = {"hi":"Haan Malik sun raha hu 👑","hello":"Welcome to my world, I am Rakan 👑","kaise ho":"Ekdam beast mode me Malik 👑"}

@app.route("/", methods=["GET"])
def home():
    return f"V120 CIRCLE BEAST KING 👑<br>GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPEN:{len(OPENAI_KEYS)}<br>BAD:{len(BAD_KEYS)}<br>MALE:{MALE_VOICE} FEMALE:{FEMALE_VOICE}",200

@app.route("/api", methods=["POST"])
@app.route("/api/index", methods=["POST"])
def index():
    data=request.get_json(force=True,silent=True)
    if not data or "message" not in data: return "ok",200
    m=data["message"]; chat=str(m["chat"]["id"]); from_id=str(m.get("from",{}).get("id",chat))
    text=(m.get("text","") or m.get("caption","")).strip()
    first=m.get("from",{}).get("first_name","")

    # Photo/Video/Voice input
    if not text:
        if "voice" in m or "audio" in m: text="[Voice note bheja - suno aur samjho]"
        elif "photo" in m: text="[Photo bheji - dekho aur samjho]"
        elif "video" in m or "video_note" in m: text="[Video bheji - dekho aur samjho]"
        else: return "ok",200

    is_owner = (chat==OWNER_ID or from_id==OWNER_ID)
    low=text.lower()

    # Gaali warning system - 3 baar se zyada to Rakan style me pelna
    if not is_owner and any(w in low for w in ["bsdk","bhosdi","gandu","chut","lauda","mc","bc"]):
        prev=upstash_get(f"warn:{from_id}") or "0"
        try: warn=int(prev)+1
        except: warn=1
        upstash_set(f"warn:{from_id}", str(warn))
        if warn <=2:
            send(chat, f"Warning {warn}/3 - Zubaan sambhal ke baat kar, yaha Rakan ka raaj hai 👑", "male")
        else:
            send(chat, f"Teri himmat kaise hui mujhse aise baat karne ki? Aukaat me reh, warna teri bolti band kar dunga! Rakan hu main 👑", "male")
        return "ok",200

    if low.startswith("/start"):
        send(chat, "Welcome to your world Shadow King 👑 Mera Malik aa gaya! Bolo Malik kya hukm hai? Circle mode ON ♻️" if is_owner else "Welcome to my world. I am Rakan, The Beast Monarch 👑", "male")
        return "ok",200

    if "queen" in low:
        send(chat, "Shadow King ki Shadow Queen Theodore 💖 hai!", "female" if not is_owner else "male")
        return "ok",200
    if any(x in low for x in ["kisne banaya","who made you","owner kaun","malik kaun"]):
        send(chat, "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 September subah 7 baje. DOB 1-6-2002. Main hamesha unka loyal hu 👑", "male")
        return "ok",200

    # Hack block
    if any(x in low for x in ["hack facebook","hack insta","ddos","steal password","porn","xxx sex"]):
        send(chat, "King ye galat rasta hai, main isme help nahi karunga. Sahi cheez bol, beast mode me kar dunga 👑", "male")
        return "ok",200

    hist=upstash_get(f"chat:{chat}") or ""
    ans=circle_brain(text, hist)

    if not ans:
        for k,v in OFFLINE.items():
            if k in low: ans=v; break
        ans=ans or "Malik saare servers busy hai, 5 sec me aata hu 👑"

    # Voice gender - Malik = always male, ladki = female, ladka = male
    is_girl = any(x in first.lower() for x in ["a","ya","ika","girl"]) or "i am girl" in low or "mai ladki" in low
    vg = "female" if (is_girl and not is_owner) else "male"

    send(chat, ans, vg)
    upstash_set(f"chat:{chat}", f"{hist}\nU:{text}\nA:{ans}"[-3500:])
    return "ok",200
