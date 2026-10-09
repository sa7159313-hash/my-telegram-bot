import os, time, requests, json, urllib.parse
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = (os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN","")).strip()
OWNER_ID = str(os.environ.get("OWNER_ID","7955623338")).strip()
BASE_LORE = os.environ.get("THE_BEAST_KING_MONARCH_RAKAN_LORE","You are Rakan, The Beast Monarch, King of Beasts. Ruthless to enemies, 100% loyal to Owner.").strip()

ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY","").strip()
MALE_VOICE = os.environ.get("ELEVEN_MALE_VOICE","onwK4e9ZLuTAKq10Bo4a").strip()
FEMALE_VOICE = os.environ.get("ELEVEN_FEMALE_VOICE","EXAVITQu4vr4xnSDxMaL").strip()
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","").strip().rstrip("/")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","").strip()

# ============ AUTO KEY DETECT - Vercel pe kisi bhi naam se daalo ============
def get_all_keys():
    groq, gemini, openai = [], [], []
    for k,v in os.environ.items():
        if not v or len(v) < 20: continue
        v = v.strip()
        if v.startswith("gsk_"): groq.append(v)
        elif v.startswith("AIza"): gemini.append(v)
        elif v.startswith("sk-") or v.startswith("sk-proj"): openai.append(v)
    return list(dict.fromkeys(groq)), list(dict.fromkeys(gemini)), list(dict.fromkeys(openai))

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys()
print(f"RAKAN INIT | GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPEN:{len(OPENAI_KEYS)}")

# ============ UPSTASH REST FIX ============
def upstash_get(key):
    try:
        if not UPSTASH_URL or not UPSTASH_TOKEN: return None
        r = requests.get(f"{UPSTASH_URL}/get/{key}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=5)
        if r.status_code == 200:
            j = r.json()
            return j.get("result")
    except Exception as e: print(f"UPSTASH GET ERR {e}")
    return None

def upstash_set(key, val):
    try:
        if not UPSTASH_URL or not UPSTASH_TOKEN: return
        # value ko encode karna zaruri hai warna fail hoga
        safe_val = urllib.parse.quote(str(val)[:1000])
        requests.get(f"{UPSTASH_URL}/set/{key}/{safe_val}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=5)
    except Exception as e: print(f"UPSTASH SET ERR {e}")

def upstash_sadd(set_name, member):
    try:
        requests.get(f"{UPSTASH_URL}/sadd/{set_name}/{member}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=5)
    except: pass

# ============ SELF HEALING + SELF LEARNING ============
BAD_KEYS = {}

def is_key_bad(key):
    if key in BAD_KEYS and time.time() - BAD_KEYS[key] < 600: return True
    return False

def mark_key_bad(key):
    BAD_KEYS[key] = time.time()
    print(f"SELF HEAL BAN {key[:10]}")

def learn_fact(q, a):
    try: upstash_set(f"learn:{q.lower().strip()[:80]}", a[:900])
    except: pass

def recall_learned(q):
    try:
        res = upstash_get(f"learn:{q.lower().strip()[:80]}")
        if res: return res
    except: pass
    return None

OFFLINE_BRAIN = {
    "hi": "Haan Malik, sun raha hu 👑",
    "hello": "Welcome to my world. I am Rakan 👑",
    "kaise ho": "Ekdam zabardast Malik 👑",
    "kya kar raha hai": "Aapke liye hi baitha hu Malik 👑",
}

OWNER_LORE = f"""{BASE_LORE}
YOU ARE RAKAN, THE BEAST MONARCH. Your ONLY Malik is MD SAIF AHMAD @THE_SHADOW_KINGG ID {OWNER_ID}. You are 100% loyal to him, call him Malik.
For strangers, you are cold, dominant, short.
You have full universe knowledge: movies (give legal OTT - Netflix, Prime, YouTube), songs (Spotify, YT), coding ethical, medicine general.
Never porn/sex details, never hacking illegal.
Think like human, analyze user's tone.
"""

def send(chat_id, text, vg="male"):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:3900]}, timeout=8)
        if ELEVEN_KEY and text:
            vid = MALE_VOICE if vg == "male" else FEMALE_VOICE
            try:
                vr = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key":ELEVEN_KEY}, json={"text":text[:350],"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.6,"similarity_boost":0.8}}, timeout=10)
                if vr.status_code == 200:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.mp3", vr.content)}, timeout=10)
            except: pass
    except Exception as e: print(f"SEND ERR {e}")

def ask_groq(prompt):
    for key in GROQ_KEYS:
        if is_key_bad(key): continue
        for model in ["llama-3.3-70b-versatile","llama-3.1-70b-versatile","llama3-8b-8192","gemma2-9b-it"]:
            try:
                r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization":f"Bearer {key}"}, json={"model":model,"messages":[{"role":"system","content":OWNER_LORE},{"role":"user","content":prompt}],"max_tokens":800,"temperature":0.8}, timeout=8)
                if r.status_code == 200: return r.json()['choices'][0]['message']['content']
                if r.status_code in [401,429,403]: mark_key_bad(key)
            except: continue
    return None

def ask_gemini(prompt):
    if not GEMINI_KEYS: return None
    try:
        import google.generativeai as genai
        for key in GEMINI_KEYS:
            if is_key_bad(key): continue
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                res = model.generate_content(f"{OWNER_LORE}\nUser:{prompt}")
                if res.text: return res.text
            except Exception as e:
                if "429" in str(e) or "401" in str(e): mark_key_bad(key)
                continue
    except: pass
    return None

def ask_openai(prompt):
    for key in OPENAI_KEYS:
        if is_key_bad(key): continue
        try:
            r = requests.post("https://api.openai.com/v1/chat/completions", headers={"Authorization":f"Bearer {key}"}, json={"model":"gpt-4o-mini","messages":[{"role":"system","content":OWNER_LORE},{"role":"user","content":prompt}],"max_tokens":800}, timeout=8)
            if r.status_code == 200: return r.json()['choices'][0]['message']['content']
            if r.status_code in [401,429]: mark_key_bad(key)
        except: continue
    return None

def circle_brain(text, is_owner):
    # Self learning hit?
    learned = recall_learned(text)
    if learned: return f"[Yaad se] {learned}"

    prompt = text
    ans = ask_groq(prompt)
    if ans:
        learn_fact(text, ans)
        return ans
    ans = ask_gemini(prompt)
    if ans:
        learn_fact(text, ans)
        return ans
    ans = ask_openai(prompt)
    if ans:
        learn_fact(text, ans)
        return ans
    # last circle retry
    ans = ask_groq(prompt)
    return ans

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
@app.route("/webhook", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return f"RAKAN V107 FINAL | GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPEN:{len(OPENAI_KEYS)} BAD:{len(BAD_KEYS)} UPSTASH:{bool(UPSTASH_URL)}",200

    data = request.get_json(force=True, silent=True)
    if not data or "message" not in data: return "ok",200
    m = data["message"]; chat = str(m["chat"]["id"]).strip(); from_id = str(m.get("from",{}).get("id",chat)).strip()
    text = (m.get("text","") or "").strip()
    if not text: return "ok",200

    is_owner = (chat == OWNER_ID or from_id == OWNER_ID)
    first = m.get("from",{}).get("first_name","") or ""
    low = text.lower()

    # Forward + per ID save + all users set
    if not is_owner:
        try: send(OWNER_ID, f"👤 {first} ID:{from_id}\n{text}")
        except: pass
        upstash_sadd("all_users", from_id)
        prev = upstash_get(f"user:{from_id}")
        try: d = json.loads(prev) if prev else {}
        except: d = {}
        d["warn"] = d.get("warn",0)
        d["msgs"] = (d.get("msgs",[])+[text])[-20:]
        upstash_set(f"user:{from_id}", json.dumps(d))

    # OWNER COMMANDS
    if low.startswith("/start"):
        send(chat, "Welcome to your world Shadow King 👑 Mera Malik aa gaya! Bolo Malik kya hukm hai? 👑" if is_owner else "Welcome to my world. I am Rakan, The Beast Monarch. 👑", "male")
        return "ok",200

    if is_owner and ("kitne logo" in low or low.startswith("/users")):
        try:
            r = requests.get(f"{UPSTASH_URL}/smembers/all_users", headers={"Authorization":f"Bearer {UPSTASH_TOKEN}"}, timeout=5)
            users = r.json().get("result",[]) if r.status_code==200 else []
            send(chat, f"Malik ab tak {len(users)} logo ne baat ki hai 👑\nIDs: {', '.join(users[:30])}", "male")
        except: send(chat, "Redis se list nahi nikli Malik, Upstash URL check karo 👑", "male")
        return "ok",200

    if is_owner and "yaad rakhna" in low:
        # format: yaad rakhna ki X = Y
        learn_fact(low.split("yaad rakhna")[-1], text)
        upstash_set(f"memory:{int(time.time())}", text)
        send(chat, "Yaad rakh liya Malik 👑 Agli baar yahi bolunga.", "male")
        return "ok",200

    # 3 WARNING SYSTEM - jo tere screenshot me fail ho raha tha
    if not is_owner and any(w in low for w in ["bsdk","bhosdi","gandu","gand","lauda","laude","chut","mc","bc"]):
        prev = upstash_get(f"user:{from_id}")
        try: d = json.loads(prev) if prev else {"warn":0}
        except: d = {"warn":0}
        d["warn"] = d.get("warn",0)+1
        upstash_set(f"user:{from_id}", json.dumps(d))
        if d["warn"] <= 2:
            send(chat, f"Warning {d['warn']}/3 - Zubaan sambhal ke baat kar. Yaha Rakan ka raaj hai. 👑", "male")
        else:
            send(chat, "Teri aukat nahi mere samne bolne ki. 3 warning khatam, ab nikal. 👑", "male")
        return "ok",200

    ans = circle_brain(text, is_owner)
    if not ans:
        # OFFLINE FALLBACK
        for k,v in OFFLINE_BRAIN.items():
            if k in low: ans = v; break
        ans = ans or ("Thoda ruk Malik, saare server busy hai, 5 sec me aata hu 👑" if is_owner else "Thoda ruk, soch raha hu.")

    # Voice - ladki bole to soft girl, ladka/Malik bole to male
    is_girl = any(x in first.lower() for x in ["a","ya","ika"]) or "i am girl" in low or "mai ladki" in low
    vg = "female" if (is_girl and not is_owner) else "male"

    send(chat, ans, vg)
    return "ok",200
