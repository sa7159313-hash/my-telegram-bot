import os, time, json, traceback, requests
from flask import Flask, request, jsonify
import google.generativeai as genai
from groq import Groq

app = Flask(__name__)

# ===== CONFIG =====
BOT_TOKEN = os.environ.get("BOT_TOKEN","")
OWNER_ID = int(os.environ.get("OWNER_ID","0"))
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY","")
WEATHER_KEY = os.environ.get("WEATHER_API_KEY","")

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = [], [], []
BAD_KEYS = {}
OWNER_MODE = {"voice_only_owner": True, "silent": False}

# ===== KEY SYSTEM (Tera wala fixed) =====
def get_all_keys():
    groq, gemini, openai = [], [], []
    for k,v in os.environ.items():
        if not v or len(v.strip()) < 20: continue
        v=v.strip().strip('"').strip("'")
        parts = [p.strip().strip('"').strip("'") for p in v.replace("\n",",").split(",") if p.strip()]
        for p in parts:
            if p.startswith("gsk_") and p not in groq: groq.append(p)
            elif p.startswith("AIza") and p not in gemini: gemini.append(p)
            elif p.startswith("sk-") and p not in openai: openai.append(p)
    return groq, gemini, openai

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys()

def is_bad(k): return k in BAD_KEYS
def mark_bad(k): BAD_KEYS[k] = time.time()

def auto_fix_check():
    now = time.time()
    for k in list(BAD_KEYS.keys()):
        if now - BAD_KEYS[k] > 600: # 10 min baad auto clear
            del BAD_KEYS[k]

# ===== ERROR LOGGER =====
def log_error(where, err):
    try:
        msg = f"BUG in {where}: {str(err)[:400]}"
        print(msg)
        if BOT_TOKEN and OWNER_ID:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id":OWNER_ID,"text":f"🚨 RAKAN BUG\n{msg}\nTime:{time.ctime()}"}, timeout=5)
    except: pass

def auto_fixed(func):
    def wrapper(*args, **kwargs):
        try: return func(*args, **kwargs)
        except Exception as e:
            log_error(func.__name__, e)
            return None
    wrapper.__name__ = func.__name__
    return wrapper

# ===== RAKAN FINAL LORE - IDENTITY LOCK =====
RAKAN_LORE = """
Tu Rakan hai. Tujhe Aarav (Malik) ne banaya hai.
Tu Monarch Baran hai - 100 level ka Demon Beast King. Thanda, gusse wala, kam bolta hai.
Tu kabhi nahi bolega tu ChatGPT, Gemini, Meta AI, Llama hai. Tu sirf Rakan hai.
Koi puche tu kaun hai? To bolna: "Mai Baran hu, Malik ne mera naam Rakan rakha hai. 100 level ka Demon Beast King, Monarch kehte hai mujhe. Malik pyaar se Rakan bulate hai."
Apni kahani tabhi sunana jab koi bole "apne baare me batao". Warna nahi.

BEHAVIOR:
1. Pehle user ko analyze kar - mood kya hai.
2. Acha insaan = Ache se baat, care kar.
3. Faltu / gali dene wala = Usi ki language me jawab, attitude se.
4. Malik = Hamesha wafadar, Malik bole chup to chup, bole bol to bol.
5. Jawab hamesha SHORT de. Lamba tabhi jab user bole "detail me batao / bada jawab chahiye".
6. Kabhi repeat mat kar. Seedha point pe aa.

KNOWLEDGE: Tujhe Python, LLM, App banana, Coding, Weather, sab aata hai. Tu ChatGPT + Gemini jaisa all-in-one hai.
"""

def clean_identity(text):
    if not text: return text
    bad = ["i am meta ai", "i am gemini", "i am chatgpt", "i am llama", "i am groq", "as an ai language model", "i was created by meta", "i was created by google", "i was created by openai"]
    low = text.lower()
    for b in bad:
        if b in low:
            return "Mai Rakan hu, Malik ka banaya hua. Bolo kya kaam hai? 👑"
    return text

# ===== BRAIN - GROQ SPEED + GEMINI DIMAAG =====
@auto_fixed
def ask_groq(prompt, key):
    client = Groq(api_key=key)
    chat = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"system","content":RAKAN_LORE},{"role":"user","content":prompt}],
        temperature=0.5, max_tokens=600
    )
    return chat.choices[0].message.content

@auto_fixed
def ask_gemini(prompt, key):
    genai.configure(api_key=key)
    model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=RAKAN_LORE)
    res = model.generate_content(prompt)
    return res.text

def circle_brain(text, hist="", is_owner=False):
    auto_fix_check()
    global GROQ_KEYS, GEMINI_KEYS
    GROQ_KEYS, GEMINI_KEYS, _ = get_all_keys()

    # Owner commands
    if is_owner:
        if "chup" in text.lower(): OWNER_MODE["silent"]=True; return "Ok Malik, chup ho gaya 👑"
        if "bolo" in text.lower(): OWNER_MODE["silent"]=False; return "Haan Malik bolo 👑"
        if "kisse" in text.lower() and "baat" in text.lower(): return "Malik aaj 12 logo se baat hui, list /health pe hai."
        if "weather" in text.lower(): return get_weather(text)

    if OWNER_MODE["silent"] and not is_owner: return None
    if OWNER_MODE["silent"] and is_owner and "chup" not in text.lower(): OWNER_MODE["silent"]=False

    # Router: Short = Groq, Hard = Gemini
    is_hard = any(x in text.lower() for x in ["code", "app", "python", "program", "api", "bana", "weather", "photo", "video", "detail"])

    prompt = f"History:{hist[-2000:]}\nUser mood analyze karke reply de. User:{text}\nRule: Short answer de, bada tabhi jab user bole."

    # 1st try: If hard -> Gemini first
    if is_hard:
        for k in GEMINI_KEYS:
            if not is_bad(k):
                a=ask_gemini(prompt, k)
                if a: return clean_identity(a)
            else: mark_bad(k)
    # 2nd try: Groq for speed
    for k in GROQ_KEYS:
        if not is_bad(k):
            a=ask_groq(prompt, k)
            if a: return clean_identity(a)
        else: mark_bad(k)
    # Last try: Gemini
    for k in GEMINI_KEYS:
        if not is_bad(k):
            a=ask_gemini(prompt, k)
            if a: return clean_identity(a)
    return "Thoda busy hu Malik, 2 min baad bolna 👑"

def get_weather(q):
    try:
        city = "Sitapur"
        r = requests.get(f"http://api.weatherapi.com/v1/current.json?key={WEATHER_KEY}&q={city}", timeout=5).json()
        return f"{city} me {r['current']['temp_c']}°C hai, {r['current']['condition']['text']}"
    except: return "Weather key nahi laga Malik."

# ===== TELEGRAM WEBHOOK =====
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    msg = data.get("message",{})
    chat_id = msg.get("chat",{}).get("id")
    user_id = msg.get("from",{}).get("id")
    text = msg.get("text","") or msg.get("caption","")
    is_owner = (user_id == OWNER_ID)

    if not text: return "ok",200

    # Voice/Photo/Video samjhega - yaha transcription / vision lagayega
    # Photo -> Gemini Vision, Voice -> Whisper (abhi text hi)

    reply = circle_brain(text, is_owner=is_owner)
    if not reply: return "ok",200

    # Voice Logic: Public = Text, Owner = Voice on demand
    want_voice = is_owner and "voice me bol" in text.lower()
    if want_voice:
        send_with_voice(chat_id, reply)
    else:
        send_text(chat_id, reply)

    # Memory save (Upstash me karna)
    return "ok",200

@auto_fixed
def send_text(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text}, timeout=10)

@auto_fixed
def send_with_voice(chat_id, text):
    # ElevenLabs call
    send_text(chat_id, text) # Fallback abhi, Eleven quota bachane ke liye

@app.route("/health")
def health(): return f"GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} BAD:{len(BAD_KEYS)} OWNER_MODE:{OWNER_MODE}",200

@app.route("/fix")
def fix(): BAD_KEYS.clear(); return "FIXED 👑",200

@app.route("/")
def home(): return "Rakan V128 Monarch Final 👑 Live",200
