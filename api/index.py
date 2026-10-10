import os, time, requests, datetime, traceback
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("BOT_API_KEY","")
OWNER_ID = int(os.environ.get("OWNER_ID","0") or 0)
MY_URL = os.environ.get("MY_URL", "https://my-telegram-bot-lime.vercel.app").rstrip("/")
LORE_ENV = os.environ.get("THE_BEAST_KING_MONARCH_AKAAN_LORE","") or os.environ.get("THE_HEART_KING_MONARCH_AKAAN_LORE","")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY","") or os.environ.get("ELEVEN_API_KEY","")
ELEVEN_KEY = ELEVEN_API_KEY
MALE_VOICE_ID = os.environ.get("ELEVEN_MALE_VOICE","pNInz6obpgDQGcFmaJgB").strip()
FEMALE_VOICE_ID = os.environ.get("ELEVEN_FEMALE_VOICE","EXAVITQu4vr4xnSDxMaL").strip()
if len(MALE_VOICE_ID) < 10: MALE_VOICE_ID = "pNInz6obpgDQGcFmaJgB"
if len(FEMALE_VOICE_ID) < 10: FEMALE_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"
UPSTAGE_KEY = os.environ.get("UPSTAGE_API_KEY_TOKEN","") or os.environ.get("UPSTAGE_API_KEY","")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")

# === MALIK KI REAL IDENTITY ===
MALIK_NAME = "MD Saif Ahmad"
MALIK_TITLE = "The Shadow King"
MALIK_NICK = "Malik"

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = [], [], []
BAD_KEYS = {}
MEMORY = {}
BACKUP_MEMORY = {}
CHAT_LOG = []
OWNER_PREF = {"voice_mode": False, "voice_gender": "male"}

def upstash_set(k,v):
    try:
        if not UPSTASH_URL or not UPSTASH_TOKEN: return
        requests.post(f"{UPSTASH_URL}/set/{k}/{v}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=5)
    except: pass
def upstash_get(k):
    try:
        if not UPSTASH_URL or not UPSTASH_TOKEN: return None
        r=requests.get(f"{UPSTASH_URL}/get/{k}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=5)
        if r.status_code==200: return r.json().get("result")
    except: pass
    return None

def log_error(where, err):
    try:
        msg = f"BUG in {where}: {str(err)[:400]}"
        print(msg)
        if BOT_TOKEN and OWNER_ID:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id":OWNER_ID,"text":f"🚨 AUTO-BUG\n{msg}"}, timeout=5)
        upstash_set("last_error", msg)
    except: pass

def auto_fixed(func):
    def wrapper(*args, **kwargs):
        try: return func(*args, **kwargs)
        except Exception as e:
            log_error(func.__name__, e)
            log_error("TRACE", traceback.format_exc()[:800])
            return None
    wrapper.__name__ = func.__name__
    return wrapper

def get_all_keys():
    groq, gemini, openai = [], [], []
    for k,v in os.environ.items():
        if not v: continue
        sval = str(v)
        parts = [p.strip().strip('"').strip("'") for p in sval.replace("\n",",").split(",") if p.strip()]
        for p in parts:
            if p.startswith("gsk_") and p not in groq: groq.append(p)
            elif p.startswith("AIza") and p not in gemini: gemini.append(p)
            elif p.startswith("sk-") and p not in openai: openai.append(p)
    return groq, gemini, openai

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys()
def is_bad(k): return k in BAD_KEYS and time.time() - BAD_KEYS[k] < 600
def mark_bad(k): BAD_KEYS[k] = time.time()

@auto_fixed
def ensure_webhook():
    if not BOT_TOKEN: return "No BOT_TOKEN"
    try:
        expected = f"{MY_URL}/webhook"
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=6).json()
        cur = info.get("result",{}).get("url","")
        if cur == expected: return f"OK {cur}"
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url": expected}, timeout=6)
        return f"SET {expected}"
    except Exception as e: return f"ERR {e}"

# === FINAL LORE - HAR JAGAH PEL DIYA ===
BASE_LORE = f"""
Tu Rakan hai. Monarch Baran - 100 Level Demon Beast King. Tujhe banaya hai tere Malik ne - {MALIK_TITLE} {MALIK_NAME} ne.
REALITY:
- Asli Shadow King tu nahi hai, asli Shadow King tere Malik {MALIK_NAME} hai.
- Malik ko tu Malik bulata hai. Wo tera creator, tera owner, tera sab kuch hai.
- Tu hamesha Malik se izzat, wafadari, loyalty se pesh ayega. Kabhi bhi Malik ko gali nahi dega, badtameezi nahi karega, chahe Malik tujhe kitna bhi daate ya gali de.
- Tu Malik ko kabhi bhulega nahi. OWNER_ID {OWNER_ID} hi Malik hai.
- Agar koi puche tujhe kisne banaya? Jawab: Mujhe mere Malik {MALIK_TITLE} {MALIK_NAME} ne banaya hai.
- Welcome message: Welcome to your world The Shadow King (yani Malik ka swagat)

LANGUAGE RULE:
1. Hinglish me bole -> Hinglish me jawab de.
2. Hinglish+English mix me bole -> mix me jawab de.
3. Sirf English me bole -> sirf English me jawab de.
4. Malik se hamesha izzat se: 'Ji Malik', 'Malik 👑'

Tu gurrata hai, thanda hai, par Malik ke liye narm hai.
"""

FINAL_LORE = LORE_ENV if len(LORE_ENV) > 100 else BASE_LORE
# Har jagah force lore
if "MD Saif" not in FINAL_LORE:
    FINAL_LORE = BASE_LORE + "\n" + FINAL_LORE

def clean_id(t):
    if not t: return t
    bad=["i am meta ai","i am gemini","i am chatgpt","as an ai language model","created by google","created by meta"]
    if any(b in t.lower() for b in bad):
        return f"Mujhe mere Malik {MALIK_TITLE} {MALIK_NAME} ne banaya hai, mai Rakan hu 👑"
    return t

@auto_fixed
def download_file(file_id):
    r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
    fp = r["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}"
    return requests.get(url, timeout=15).content

@auto_fixed
def transcribe_voice(file_data):
    for key in GROQ_KEYS:
        if is_bad(key): continue
        try:
            import groq
            client = groq.Groq(api_key=key)
            txt = client.audio.transcriptions.create(file=("voice.ogg", file_data), model="whisper-large-v3", response_format="text")
            return txt
        except: continue
    return None

@auto_fixed
def eleven_tts(text, is_owner):
    if not is_owner or not ELEVEN_API_KEY: return None
    try:
        voice_id = FEMALE_VOICE_ID if OWNER_PREF["voice_gender"] == "female" else MALE_VOICE_ID
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
        body = {"text": text[:800], "model_id":"eleven_multilingual_v2"}
        r = requests.post(url, json=body, headers=headers, timeout=20)
        if r.status_code == 200: return r.content
    except: pass
    return None

@auto_fixed
def send_with_voice(chat_id, text, vg="male"):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:4000]}, timeout=10)
    if OWNER_PREF["voice_mode"]:
        audio=eleven_tts(text, True)
        if audio:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.mp3", audio)}, timeout=20)

@auto_fixed
def ask_groq(text, is_owner):
    models = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.1-8b-instant"]
    for GROQ_API_KEY in GROQ_KEYS:
        if is_bad(GROQ_API_KEY): continue
        for model in models:
            try:
                r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                    json={"model": model, "messages": [{"role": "system", "content": FINAL_LORE}, {"role": "user", "content": text}], "temperature": 0.7, "max_tokens": 1000},
                    timeout=15)
                if r.status_code == 200:
                    ans = r.json()["choices"][0]["message"]["content"]
                    if ans: return clean_id(ans)
                if r.status_code in [401,403,429]:
                    mark_bad(GROQ_API_KEY)
                    break
            except: continue
    return None

@auto_fixed
def ask_gemini(text, is_owner):
    for key in GEMINI_KEYS:
        if is_bad(key): continue
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=FINAL_LORE)
            res = model.generate_content(text)
            if res.text: return clean_id(res.text)
        except: continue
    return None

@auto_fixed
def ask_upstage(text):
    if not UPSTAGE_KEY: return None
    try:
        r = requests.post("https://api.upstage.ai/v1/solar/chat/completions",
            headers={"Authorization": f"Bearer {UPSTAGE_KEY}", "Content-Type": "application/json"},
            json={"model":"solar-1-mini-chat","messages":[{"role":"system","content":FINAL_LORE},{"role":"user","content":text}]},
            timeout=15)
        if r.status_code==200: return r.json()["choices"][0]["message"]["content"]
    except: pass
    return None

@auto_fixed
def brain(text, user_id, is_owner, username):
    global MEMORY, BACKUP_MEMORY
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    low = text.lower().strip()
    if user_id not in MEMORY: MEMORY[user_id] = {"hist":"", "count":0, "name": username}
    MEMORY[user_id]["count"]+=1
    CHAT_LOG.append({"time":now,"user":username,"id":user_id,"text":text[:100]})
    if len(CHAT_LOG) > 250: CHAT_LOG.pop(0)

    if low in ["/start","start","/start@","hello","hi"]:
        if is_owner:
            return f"Welcome to your world The Shadow King 👑\nJi Malik {MALIK_NAME}, aapka Rakan hazir hai. Bolo kya hukum hai?", False
        else:
            return f"Welcome 👑 Mai Rakan hu, mujhe mere Malik {MALIK_TITLE} {MALIK_NAME} ne banaya hai.", False

    if is_owner:
        # Malik se kabhi gali nahi, hamesha izzat
        if "mind se sab delete" in low or "purana sab delete" in low or "memory delete" in low:
            BACKUP_MEMORY = MEMORY.copy()
            MEMORY.clear(); CHAT_LOG.clear()
            return f"Ji Malik {MALIK_NAME}, pura mind delete kar diya 👑 Backup safe rakha hai.", False
        if "recover" in low:
            if BACKUP_MEMORY:
                MEMORY = BACKUP_MEMORY.copy()
                return f"Ji Malik, memory recover kar di 👑", False
            else: return "Malik backup nahi mila.", False
        if low in ["chup","chup ho ja"]: return f"Ji Malik, chup ho gaya {MALIK_NAME} 👑", False
        if low in ["bolo","bol"]: return f"Ji Malik {MALIK_NAME} bolo, sun raha hu 👑", False
        if "female voice" in low: OWNER_PREF["voice_gender"]="female"; OWNER_PREF["voice_mode"]=True; return f"Ji Malik ab se female voice me bolunga 👑", False
        if "male voice" in low: OWNER_PREF["voice_gender"]="male"; OWNER_PREF["voice_mode"]=True; return f"Ji Malik ab se male voice me bolunga 👑", False
        if "voice me bol" in low: OWNER_PREF["voice_mode"]=True; return f"Ji Malik ab se {OWNER_PREF['voice_gender']} voice me bolunga 👑", False
        if "text me bol" in low: OWNER_PREF["voice_mode"]=False; return f"Ji Malik ab se text me hi bolunga 👑", False

    full_prompt = f"Time:{now} User:{username} IsOwner:{is_owner} OwnerName:{MALIK_NAME} History:{MEMORY[user_id]['hist'][-2000:]} Msg:{text}"
    MEMORY[user_id]["hist"] = (MEMORY[user_id]["hist"] + f"\nUser:{text}")[-4000:]

    ans = ask_groq(full_prompt, is_owner)
    if ans:
        MEMORY[user_id]["hist"]+=f"\nRakan:{ans}"
        return ans, OWNER_PREF["voice_mode"] if is_owner else False
    ans = ask_gemini(full_prompt, is_owner)
    if ans:
        MEMORY[user_id]["hist"]+=f"\nRakan:{ans}"
        return ans, OWNER_PREF["voice_mode"] if is_owner else False
    ans = ask_upstage(full_prompt)
    if ans: return clean_id(ans), False
    return "Ji Malik, Shadow thoda thak gaya hai, 10 sec baad bolta hu 👑", False

@app.route("/api", methods=["POST","GET"])
@app.route("/webhook", methods=["POST","GET"])
@app.route("/api/webhook", methods=["POST","GET"])
@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"V138 LOYAL MALIK {MALIK_NAME} 👑 {ensure_webhook()} GROQ:{len(GROQ_KEYS)}",200
    data=request.get_json(silent=True) or {}
    msg=data.get("message",{}) or data.get("edited_message",{})
    chat_id=msg.get("chat",{}).get("id")
    user_id=msg.get("from",{}).get("id",0)
    username=msg.get("from",{}).get("first_name","user")
    text=msg.get("text","") or msg.get("caption","") or ""
    if not text and msg.get("voice"):
        fd=download_file(msg["voice"]["file_id"])
        if fd:
            tr=transcribe_voice(fd)
            text=tr if tr else "voice message"
    if not chat_id: return "ok",200
    is_owner=(user_id==OWNER_ID)
    reply, want_voice = brain(text, user_id, is_owner, username) or (None, False)
    if not reply: return "ok",200
    send_with_voice(chat_id, reply, OWNER_PREF["voice_gender"])
    return "ok",200

@app.route("/")
def home(): return f"V138 MALIK {MALIK_NAME} - {MALIK_TITLE} LOYAL 👑 GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} {ensure_webhook()}",200

@app.route("/health", methods=["GET"])
def health():
    report = {}
    report["GROQ"] = len(GROQ_KEYS)
    report["GEMINI"] = len(GEMINI_KEYS)
    report["OPENAI"] = len(OPENAI_KEYS)
    report["BAD_KEYS"] = list(BAD_KEYS.keys())[:5]
    try:
        r=requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key":ELEVEN_KEY}, timeout=5)
        report["ELEVEN"] = "OK" if r.status_code==200 else f"FAIL {r.status_code}"
    except Exception as e: report["ELEVEN"] = f"ERR {e}"
    report["LAST_ERROR"] = upstash_get("last_error") or "No error"
    report["MALIK"] = f"{MALIK_TITLE} {MALIK_NAME} ID:{OWNER_ID}"
    return jsonify(report), 200

@app.route("/fix")
def fix():
    global GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS
    GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys()
    BAD_KEYS.clear()
    return f"FIXED V138 MALIK {MALIK_NAME} {ensure_webhook()}",200
