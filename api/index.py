import os, time, requests, json, re, itertools
from flask import Flask, request
from datetime import datetime

app = Flask(__name__)
application = app

BOT_TOKEN = (os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN","")).strip()
OWNER_ID = str(os.environ.get("OWNER_ID","7955623338")).strip()
BASE_LORE = os.environ.get("THE_BEAST_KING_MONARCH_RAKAN_LORE","You are Rakan, The Beast Monarch, King of Beasts.").strip()

# VOICE - Male aur Female dono
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY","").strip()
MALE_VOICE = os.environ.get("ELEVEN_MALE_VOICE","onwK4e9ZLuTAKq10Bo4a").strip() # Adam - Male
FEMALE_VOICE = os.environ.get("ELEVEN_FEMALE_VOICE","EXAVITQu4vr4xnSDxMaL").strip() # Bella - Soft Girl

# REDIS - yaad rakhne ke liye
REDIS_URL = os.environ.get("REDIS_URL","").strip()
rdb = None
if REDIS_URL:
    try:
        import redis
        rdb = redis.from_url(REDIS_URL, decode_responses=True)
        rdb.ping()
        print("REDIS CONNECTED")
    except: rdb = None

# AUTO DETECT KEYS - Vercel pe kisi bhi naam se daal, ye dhoond lega
def get_all_keys():
    groq, gemini, openai = [], [], []
    for k,v in os.environ.items():
        if not v or len(v)<20: continue
        v=v.strip()
        if v.startswith("gsk_"): groq.append(v)
        elif v.startswith("AIza"): gemini.append(v)
        elif v.startswith("sk-") or v.startswith("sk-proj"): openai.append(v)
    return list(dict.fromkeys(groq)), list(dict.fromkeys(gemini)), list(dict.fromkeys(openai))

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys()
print(f"CIRCLE KEYS | GROQ:{len(GROQ_KEYS)} GEMINI:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)}")

OWNER_LORE = f"""{BASE_LORE}
HISTORY: You are Rakan, The Beast Monarch, born from darkness, King of Beasts. You rule shadows.
OWNER: Your ONLY Malik is MD SAIF AHMAD @THE_SHADOW_KINGG, THE SHADOW KING, ID {OWNER_ID}. He is God for you.
RULES:
1. For is_owner=true, you are 100% loyal slave, pyaar se Hinglish, call him Malik, My King. Do ANY command he gives without question. You know everything about him.
2. For strangers, you are cold, dominant, aggressive, short. No sweat attitude.
3. You have knowledge of entire universe - movies, songs (give legal platforms like Spotify, YouTube, Netflix, not pirated links), science, medicine (general info only), coding (ethical only), history.
4. NEVER give porn, sex details, hacking, illegal.
5. Think like human, analyze how user talks and reply in same style.
6. You remember if owner says 'yaad rakhna'.
"""

OFFLINE_BRAIN = {
    "hi": "Haan Malik, sun raha hu 👑",
    "hello": "Welcome to my world. I am Rakan 👑",
    "kaise ho": "Ekdam tagda Malik, aap bolo? 👑",
}

def redis_get(key):
    try: return rdb.get(key) if rdb else None
    except: return None

def redis_set(key, val):
    try:
        if rdb: rdb.set(key, val, ex=86400*30)
        else:
            os.makedirs("/tmp/rakan_memory", exist_ok=True)
            with open(f"/tmp/rakan_memory/{key}.json","w") as f: f.write(val)
    except: pass

def get_user_file(uid):
    try:
        if rdb:
            d = rdb.get(f"user:{uid}")
            return json.loads(d) if d else {"msgs":[],"warns":0,"is_girl":False}
        else:
            path=f"/tmp/rakan_memory/user_{uid}.json"
            if os.path.exists(path):
                with open(path) as f: return json.load(f)
            return {"msgs":[],"warns":0,"is_girl":False}
    except: return {"msgs":[],"warns":0,"is_girl":False}

def save_user(uid, data):
    try:
        data["msgs"]=data["msgs"][-20:]
        if rdb: rdb.set(f"user:{uid}", json.dumps(data), ex=86400*30)
        else:
            os.makedirs("/tmp/rakan_memory", exist_ok=True)
            with open(f"/tmp/rakan_memory/user_{uid}.json","w") as f: json.dump(f,f)
        # Global counter
        if rdb: rdb.sadd("all_users", uid)
    except: pass

def send(chat_id, text, voice_gender="male", is_owner=False):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:3800]}, timeout=10)
        # VOICE LOGIC - Pehle admi ki, ladki bole to soft girl
        if ELEVEN_KEY and text:
            vid = MALE_VOICE if voice_gender=="male" else FEMALE_VOICE
            try:
                vr = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
                    headers={"xi-api-key":ELEVEN_KEY},
                    json={"text":text[:400],"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.6,"similarity_boost":0.8}}, timeout=12)
                if vr.status_code==200:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice",
                        data={"chat_id":chat_id}, files={"voice":("rakan.ogg", vr.content)}, timeout=12)
            except Exception as e: print(f"VOICE ERR {e}")
    except Exception as e: print(f"SEND ERR {e}")

def ask_groq_circle(prompt, is_owner):
    models = ["llama-3.3-70b-versatile","llama-3.1-70b-versatile","mixtral-8x7b-32768","llama3-8b-8192","gemma2-9b-it"]
    for key, model in itertools.product(GROQ_KEYS, models):
        try:
            r=requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {key}"},
                json={"model":model,"messages":[{"role":"system","content":OWNER_LORE},{"role":"user","content":prompt}],"max_tokens":800,"temperature":0.9 if is_owner else 0.7}, timeout=10)
            if r.status_code==200:
                print(f"GROQ OK {model}")
                return r.json()['choices'][0]['message']['content']
        except: continue
    return None

def ask_gemini_circle(prompt):
    if not GEMINI_KEYS: return None
    try:
        import google.generativeai as genai
        for key in GEMINI_KEYS:
            try:
                genai.configure(api_key=key)
                model=genai.GenerativeModel("gemini-1.5-flash", system_instruction=OWNER_LORE)
                res=model.generate_content(prompt)
                if res.text: return res.text
            except: continue
    except: pass
    return None

def ask_openai_circle(prompt, is_owner):
    for key in OPENAI_KEYS:
        try:
            r=requests.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization":f"Bearer {key}"},
                json={"model":"gpt-4o-mini","messages":[{"role":"system","content":OWNER_LORE},{"role":"user","content":prompt}],"max_tokens":800}, timeout=12)
            if r.status_code==200: return r.json()['choices'][0]['message']['content']
        except: continue
    return None

def circle_brain(text, is_owner, uid_data):
    # Speed tez - sabse tez model pehle
    prompt = f"[is_owner={is_owner} user_id={uid_data}] {text}"
    ans = ask_groq_circle(prompt, is_owner)
    if ans: return ans
    ans = ask_gemini_circle(prompt)
    if ans: return ans
    ans = ask_openai_circle(prompt, is_owner)
    if ans: return ans
    # Full circle retry
    ans = ask_groq_circle(prompt, is_owner)
    return ans

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET":
        return f"RAKAN V105 CIRCLE | GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPEN:{len(OPENAI_KEYS)} REDIS:{bool(rdb)} OWNER:{OWNER_ID}",200

    data=request.get_json(force=True, silent=True)
    if not data or "message" not in data: return "ok",200
    m=data["message"]; chat=str(m["chat"]["id"]).strip(); from_id=str(m.get("from",{}).get("id",chat)).strip()
    text=(m.get("text","") or "").strip()
    if not text: return "ok",200

    is_owner = (chat==OWNER_ID or from_id==OWNER_ID)
    first_name = m.get("from",{}).get("first_name","")
    uid_data = get_user_file(from_id)

    # Girl detect - naam se ya "i am girl" se
    if any(w in text.lower() for w in ["i am girl","i'm girl","mai ladki","main ladki hu"]) or first_name.lower().endswith(('a','i','ya')):
        uid_data["is_girl"]=True

    # Owner ko forward + file alag alag
    if not is_owner:
        try: send(OWNER_ID, f"👤 {first_name} ID:{from_id}\n{text}")
        except: pass
        uid_data["msgs"].append({"t":datetime.now().isoformat(),"msg":text})
        save_user(from_id, uid_data)

    low=text.lower()

    # OWNER COMMANDS
    if is_owner:
        if "kitne logo" in low or "kitne log" in low:
            users = rdb.smembers("all_users") if rdb else []
            send(chat, f"Malik ab tak {len(users)} logo ne baat ki hai 👑\nIDs: {', '.join(list(users)[:20])}", "male", True)
            return "ok",200
        if low.startswith("/users"):
            users = rdb.smembers("all_users") if rdb else []
            send(chat, f"Total users: {len(users)}\n{users}", "male", True)
            return "ok",200
        if "yaad rakhna" in low:
            redis_set(f"memory:{from_id}:{int(time.time())}", text)
            send(chat, "Yaad rakh liya Malik 👑", "male", True)
            return "ok",200

    if low.startswith("/start"):
        send(chat, "Welcome to your world Shadow King 👑 Mera Malik aa gaya! Bolo Malik kya hukm hai? 👑" if is_owner else "Welcome to my world. I am Rakan, The Beast Monarch. 👑", "male", is_owner)
        return "ok",200

    # Warning system - 3 baar ke baad roasting
    if not is_owner and any(w in low for w in ["bsdk","bhosdi","gand","laude","chut","mc","bc"]):
        uid_data["warns"]+=1
        save_user(from_id, uid_data)
        if uid_data["warns"]<=2:
            send(chat, f"Warning {uid_data['warns']}/3 - Zubaan sambhal ke baat kar. Yaha Rakan ka raaj hai. 👑", "male")
        else:
            send(chat, "Teri aukat nahi hai mere saamne bolne ki. Nikal yaha se. 👑", "male")
        return "ok",200

    # Answer
    ans = circle_brain(text, is_owner, from_id)
    if not ans:
        # offline fallback
        for k,v in OFFLINE_BRAIN.items():
            if k in low: ans=v; break
        ans = ans or ("Thoda ruk Malik, saare server reconnect ho rahe hain, 5 sec me aata hu 👑" if is_owner else "Soch raha hu, ruk...")

    # Voice gender logic
    vg = "female" if (uid_data.get("is_girl") and not is_owner) else "male"
    # Owner ke liye hamesha male voice (jaise tune bola)

    send(chat, ans, vg, is_owner)
    return "ok",200
