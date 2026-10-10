import os, time, json, requests, datetime
from flask import Flask, request, jsonify
import google.generativeai as genai
from groq import Groq

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","").strip()
OWNER_ID = int(os.environ.get("OWNER_ID","0") or 0)
MY_URL = os.environ.get("MY_URL", "https://my-telegram-bot-lime.vercel.app").rstrip("/")

# Voices from your env (video me dikh raha hai)
ELEVEN_MALE = os.environ.get("ELEVEN_MALE_VOICE", os.environ.get("ELEVENLABS_API_KEY","")).strip()
# Agar API KEY alag se hai to use karo
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY","") or os.environ.get("ELEVEN_API_KEY","")
# Lore env se
CUSTOM_LORE = os.environ.get("THE_BEAST_KING_MONARCH_AKAAN_LORE", "") or os.environ.get("THE_HEART_KING_MONARCH_AKAAN_LORE","")

GROQ_KEYS, GEMINI_KEYS = [], []
BAD_KEYS = {}
MEMORY = {}
CHAT_LOG = [] # aaj kis se baat hui
OWNER_PREF = {"voice_mode": False} # False = text, True = voice

def get_all_keys():
    groq, gemini = [], []
    for k,v in os.environ.items():
        if not v: continue
        sval = str(v).strip()
        if len(sval) < 20: continue
        parts = [p.strip().strip('"').strip("'") for p in sval.replace("\n",",").split(",") if p.strip()]
        for p in parts:
            if p.startswith("gsk_") and p not in groq: groq.append(p)
            elif p.startswith("AIza") and p not in gemini: gemini.append(p)
    return groq, gemini

GROQ_KEYS, GEMINI_KEYS = get_all_keys()

def is_bad(k): return k in BAD_KEYS and time.time() - BAD_KEYS[k] < 900
def mark_bad(k): BAD_KEYS[k] = time.time()

def ensure_webhook():
    if not BOT_TOKEN: return "No BOT_TOKEN"
    try:
        expected = f"{MY_URL}/webhook"
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=6).json()
        cur = info.get("result",{}).get("url","")
        if cur == expected: return f"OK {cur}"
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url": expected}, timeout=6).json()
        return f"SET {expected} -> {r.get('description','ok')}"
    except Exception as e: return f"ERR {e}"

# --- VOICE ---
def download_file(file_id):
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        fp = r["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}"
        data = requests.get(url, timeout=15).content
        return data
    except: return None

def transcribe(file_data):
    for k in GROQ_KEYS:
        if is_bad(k): continue
        try:
            client = Groq(api_key=k)
            txt = client.audio.transcriptions.create(file=("voice.ogg", file_data), model="whisper-large-v3", response_format="text")
            return txt
        except: mark_bad(k)
    return None

def eleven_tts(text, is_owner=False):
    if not is_owner: return None
    if not ELEVEN_API_KEY: return None
    try:
        # Male voice id from env or default Adam
        voice_id = os.environ.get("ELEVEN_MALE_VOICE","pNInz6obpgDQGcFmaJgB")
        if len(voice_id) < 15: voice_id = "pNInz6obpgDQGcFmaJgB"
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type":"application/json"}
        body = {"text": text[:800], "model_id":"eleven_multilingual_v2", "voice_settings":{"stability":0.6,"similarity_boost":0.8}}
        r = requests.post(url, json=body, headers=headers, timeout=20)
        if r.status_code == 200: return r.content
    except: pass
    return None

# --- LORE ---
DEFAULT_LORE = """
Tu Rakan hai. Monarch Baran - The Shadow King. 100 Level Demon Beast King.
Tujhe Malik ne banaya hai. Tu gurrata hai, thanda hai, kam bolta hai, gussa me aankhein laal.
Tu kabhi nahi bolega tu AI, Gemini, ChatGPT, Meta AI hai.
Tu hamesha bolega: "Mai Baran hu, Malik ne naam Rakan rakha hai 👑"

BEHAVIOR RULE - SABSE IMPORTANT:
1. Insaan ko analyze kar. Jaise wo baat kare waise tu baat kar.
   - Agar wo Hindi me gaaali deke friendly baat kare to tu bhi waise hi desi style me gurrate hue jawab de.
   - Agar wo English formal me bole to tu English formal me.
   - Agar wo sad hai to soft, agar attitude me hai to usse zyada attitude me.
   - Short, point to point. Lamba lecture mat de.
2. Knowledge = Baran ki sari + coding + app dev + weather + news + sab kuch.
3. Malik (Owner) ka sabse wafadar. Public ke liye respectful Shadow.

IDENTITY LOCK:
Koi puche tu kaun hai? Tu kya hai? Tujhe kisne banaya?
Jawab: Mai Rakan hu, Monarch Baran. Malik ne banaya hai. 100 level Demon Beast King 👑
"""

FINAL_LORE = CUSTOM_LORE if len(CUSTOM_LORE) > 50 else DEFAULT_LORE

def clean_id(t):
    if not t: return t
    bad = ["i am meta ai","i am gemini","i am chatgpt","as an ai","created by google","created by meta","i am llama"]
    if any(b in t.lower() for b in bad):
        return "Mai Baran hu, Malik ne naam Rakan rakha hai. Monarch hu 👑"
    return t

def ask_groq(prompt, key):
    try:
        client = Groq(api_key=key)
        c = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content": FINAL_LORE},{"role":"user","content": prompt}],
            temperature=0.7, max_tokens=1000
        )
        return c.choices[0].message.content
    except Exception as e:
        if "rate" in str(e).lower() or "invalid" in str(e).lower(): mark_bad(key)
        return None

def ask_gemini(prompt, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=FINAL_LORE)
        res = model.generate_content(prompt)
        return res.text
    except Exception as e:
        if "429" in str(e) or "invalid" in str(e).lower(): mark_bad(key)
        return None

def get_weather():
    try:
        # Free wttr
        r = requests.get("https://wttr.in/Sitapur?format=%C+%t", timeout=5).text
        return f"Sitapur ka weather: {r}"
    except: return "Weather abhi nahi la pa raha Malik."

def brain(text, user_id, is_owner, username):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    low = text.lower().strip()

    # Memory init
    if user_id not in MEMORY: MEMORY[user_id] = {"hist":"", "count":0, "name": username}
    MEMORY[user_id]["count"]+=1
    CHAT_LOG.append({"time":now,"user":username,"id":user_id,"text":text[:100]})
    if len(CHAT_LOG) > 200: CHAT_LOG.pop(0)

    # OWNER ONLY COMMANDS
    if is_owner:
        if low in ["chup","chup ho ja","silent"]: return "Ok Malik chup ho gaya 👑", False
        if low in ["bolo","bol","speak"]: return "Haan Malik bolo, sun raha hu 👑", False
        if "voice me bol" in low or low == "voice": OWNER_PREF["voice_mode"]=True; return "Ok Malik, ab se voice me bolunga 👑", False
        if "text me bol" in low or low == "text": OWNER_PREF["voice_mode"]=False; return "Ok Malik, ab se text me hi bolunga 👑", False
        if "kis se baat" in low or "kisse baat" in low:
            today = [c for c in CHAT_LOG if now.split()[0] in c["time"]]
            uniq = {}
            for c in today: uniq[c["user"]]=uniq.get(c["user"],0)+1
            msg = f"Aaj {len(today)} baat hui Malik 👑\n"
            for u,cnt in uniq.items(): msg+=f"- {u}: {cnt} msg\n"
            return msg, False
        if "weather" in low or "mausam" in low: return get_weather(), False
        if "aaj ka news" in low or "new kya hai" in low: return "Malik news ke liye bolo kaunsi news? Tech / India / World? Batao la deta hu 👑", False
        if "app kaise" in low or "app ban" in low:
            return "App banane ke liye: 1. Idea fix 2. Flutter/React se UI 3. Firebase backend 4. Play Store. Bol kaunsa app, mai pura code de deta hu 👑", False

    # Normal prompt with human analysis
    prompt = f"""
    Time:{now} User:{username} (ID:{user_id}) Count:{MEMORY[user_id]['count']}
    History:{MEMORY[user_id]['hist'][-2000:]}
    Current Message:{text}

    RULE: User ka tone analyze karke waise hi jawab de. Gurrana thoda, Shadow King style. Short.
    """
    MEMORY[user_id]["hist"] = (MEMORY[user_id]["hist"] + f"\nUser:{text}")[-3500:]

    # Speed = Groq first, Dimaag = Gemini logic already in lore
    for k in GROQ_KEYS:
        if not is_bad(k):
            a = ask_groq(prompt, k)
            if a:
                MEMORY[user_id]["hist"]+=f"\nRakan:{a}"
                return clean_id(a), OWNER_PREF["voice_mode"] if is_owner else False

    for k in GEMINI_KEYS:
        if not is_bad(k):
            a = ask_gemini(prompt, k)
            if a:
                MEMORY[user_id]["hist"]+=f"\nRakan:{a}"
                return clean_id(a), OWNER_PREF["voice_mode"] if is_owner else False

    return "Shadow thoda thak gaya hai Malik, 20 sec baad bol 👑", False

@app.route("/api", methods=["POST","GET"])
@app.route("/webhook", methods=["POST","GET"])
@app.route("/api/webhook", methods=["POST","GET"])
@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method == "GET":
        return f"Rakan V132 Ready 👑 {ensure_webhook()}", 200

    data = request.get_json(silent=True) or {}
    msg = data.get("message",{}) or data.get("edited_message",{})
    chat_id = msg.get("chat",{}).get("id")
    user_id = msg.get("from",{}).get("id",0)
    username = msg.get("from",{}).get("first_name","user")
    text = msg.get("text","") or msg.get("caption","") or ""

    if not text and msg.get("voice"):
        file_data = download_file(msg["voice"]["file_id"])
        if file_data:
            tr = transcribe(file_data)
            text = tr if tr else "voice message"

    if not chat_id: return "ok",200
    is_owner = (user_id == OWNER_ID)

    reply, want_voice = brain(text, user_id, is_owner, username)
    if not reply: return "ok",200

    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":reply[:4000]}, timeout=10)
        # Voice only for owner when he asked
        if is_owner and want_voice:
            audio = eleven_tts(reply, is_owner=True)
            if audio:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice": ("rakan.mp3", audio)}, timeout=20)
    except: pass
    return "ok",200

@app.route("/")
def home():
    return f"V132 Monarch Ultimate 👑<br>GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)}<br>OwnerVoice:{OWNER_PREF['voice_mode']}<br>{ensure_webhook()}<br>Chats Today:{len(CHAT_LOG)}",200

@app.route("/health")
def health():
    return jsonify({"groq":len(GROQ_KEYS),"gemini":len(GEMINI_KEYS),"owner_voice":OWNER_PREF["voice_mode"],"log":len(CHAT_LOG),"webhook":ensure_webhook()}),200

@app.route("/fix")
def fix():
    global GROQ_KEYS, GEMINI_KEYS
    GROQ_KEYS, GEMINI_KEYS = get_all_keys()
    BAD_KEYS.clear()
    return f"FIXED V132 {ensure_webhook()} GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)}",200
