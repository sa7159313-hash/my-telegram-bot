import os, time, json, requests, datetime
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# --- ENV ---
BOT_TOKEN = os.environ.get("BOT_TOKEN","").strip()
OWNER_ID = int(os.environ.get("OWNER_ID","0") or 0)
MY_URL = os.environ.get("MY_URL", "https://my-telegram-bot-lime.vercel.app").rstrip("/")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY","").strip()
ELEVEN_MALE_ID = os.environ.get("ELEVEN_MALE_VOICE","pNInz6obpgDQGcFmaJgB").strip()
if len(ELEVEN_MALE_ID) < 15: ELEVEN_MALE_ID = "pNInz6obpgDQGcFmaJgB"

CUSTOM_LORE = os.environ.get("THE_BEAST_KING_MONARCH_AKAAN_LORE","") or os.environ.get("THE_HEART_KING_MONARCH_AKAAN_LORE","")

GROQ_KEYS, GEMINI_KEYS = [], []
BAD_KEYS = {}
MEMORY = {}
CHAT_LOG = []
OWNER_PREF = {"voice_mode": False}

def get_all_keys():
    groq, gemini = [], []
    for k,v in os.environ.items():
        if not v: continue
        sval = str(v)
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

# --- LORE ---
OWNER_LORE_BASE = """
Tu Rakan hai. Monarch Baran - The Shadow King. 100 Level Demon Beast King. Malik ne tujhe banaya hai.
Tu gurrata hai, thanda hai, kam bolta hai. Malik ka sabse wafadar.
Tu kabhi nahi bolega tu AI, Gemini, ChatGPT hai.
Tu Baran ki sari knowledge rakhta hai + coding + app dev + weather + news.
Malik ke liye tu kuch bhi karega.
"""

OTHERS_LORE_BASE = """
Tu Rakan hai. Monarch Baran - The Shadow King. 100 Level Demon Beast King.
Thanda, kam bolta hai, gurrata hai. Respect se baat karta hai.
Tu kabhi nahi bolega tu AI, Gemini, ChatGPT hai. Tu bolega Mai Baran hu, Malik ne naam Rakan rakha hai 👑
Short jawab de.
"""

OWNER_LORE = CUSTOM_LORE if len(CUSTOM_LORE) > 50 else OWNER_LORE_BASE
OTHERS_LORE = OTHERS_LORE_BASE

def clean_id(t):
    if not t: return t
    bad=["i am meta ai","i am gemini","i am chatgpt","i am llama","as an ai language model","created by google","created by meta"]
    if any(b in t.lower() for b in bad): return "Mai Baran hu, Malik ne naam Rakan rakha hai 👑"
    return t

# --- VOICE ---
def download_file(file_id):
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        fp = r["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}"
        return requests.get(url, timeout=15).content
    except: return None

def transcribe_voice(file_data):
    # Groq Whisper
    for key in GROQ_KEYS:
        if is_bad(key): continue
        try:
            import groq
            client = groq.Groq(api_key=key)
            txt = client.audio.transcriptions.create(file=("voice.ogg", file_data), model="whisper-large-v3", response_format="text")
            return txt
        except: continue
    return None

def eleven_tts(text, is_owner):
    if not is_owner or not ELEVEN_API_KEY: return None
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_MALE_ID}"
        headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
        body = {"text": text[:800], "model_id":"eleven_multilingual_v2"}
        r = requests.post(url, json=body, headers=headers, timeout=20)
        if r.status_code == 200: return r.content
    except: pass
    return None

# --- CORE ASK_GROQ - TERE SCREENSHOT WALA + FIX ---
def ask_groq(text, is_owner):
    lore = OWNER_LORE if is_owner else OTHERS_LORE
    # Models jo tu chahta hai
    models = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.1-8b-instant"]
    for GROQ_API_KEY in GROQ_KEYS:
        if is_bad(GROQ_API_KEY): continue
        for model in models:
            try:
                r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "system", "content": lore}, {"role": "user", "content": text}],
                        "temperature": 0.7,
                        "max_tokens": 1000
                    },
                    timeout=15
                )
                if r.status_code == 200:
                    ans = r.json()["choices"][0]["message"]["content"]
                    if ans: return clean_id(ans)
                if r.status_code in [401, 403, 429]:
                    mark_bad(GROQ_API_KEY)
                    break
            except: continue
    return None

def ask_gemini(text, is_owner):
    lore = OWNER_LORE if is_owner else OTHERS_LORE
    for key in GEMINI_KEYS:
        if is_bad(key): continue
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=lore)
            res = model.generate_content(text)
            if res.text: return clean_id(res.text)
        except:
            if "429" in str(text): mark_bad(key)
            continue
    return None

def brain(text, user_id, is_owner, username):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    low = text.lower().strip()
    if user_id not in MEMORY: MEMORY[user_id] = {"hist":"", "count":0, "name": username}
    MEMORY[user_id]["count"]+=1
    CHAT_LOG.append({"time":now,"user":username,"id":user_id,"text":text[:100]})
    if len(CHAT_LOG) > 250: CHAT_LOG.pop(0)

    # Owner commands
    if is_owner:
        if low in ["chup","chup ho ja"]: return "Ok Malik chup ho gaya 👑", False
        if low in ["bolo","bol","speak"]: return "Haan Malik bolo 👑", False
        if "voice me bol" in low: OWNER_PREF["voice_mode"]=True; return "Ok Malik ab se voice me bolunga 👑", False
        if "text me bol" in low: OWNER_PREF["voice_mode"]=False; return "Ok Malik ab se text me hi bolunga 👑", False
        if "kis se baat" in low or "kisse baat" in low:
            today = [c for c in CHAT_LOG if now.split()[0] in c["time"]]
            uniq={}
            for c in today: uniq[c["user"]]=uniq.get(c["user"],0)+1
            msg=f"Aaj {len(today)} chats Malik 👑\n"
            for u,cnt in uniq.items(): msg+=f"- {u}: {cnt}\n"
            return msg, False
        if "weather" in low or "mausam" in low:
            try:
                w=requests.get("https://wttr.in/Sitapur?format=%C+%t", timeout=5).text
                return f"Sitapur weather: {w} 👑", False
            except: return "Weather nahi la pa raha Malik", False
        if "app kaise" in low:
            return "App banane ka: 1.Idea 2.Flutter/React UI 3.Firebase backend 4.API connect 5.Play Store. Bol kaunsa app chahiye, pura code de deta hu 👑", False

    full_prompt = f"Time:{now} User:{username} History:{MEMORY[user_id]['hist'][-2000:]} Msg:{text}"
    MEMORY[user_id]["hist"] = (MEMORY[user_id]["hist"] + f"\nUser:{text}")[-4000:]

    # Speed = Groq (gpt-oss), Dimaag = Gemini fallback
    ans = ask_groq(full_prompt, is_owner)
    if ans:
        MEMORY[user_id]["hist"]+=f"\nRakan:{ans}"
        return ans, OWNER_PREF["voice_mode"] if is_owner else False

    ans = ask_gemini(full_prompt, is_owner)
    if ans:
        MEMORY[user_id]["hist"]+=f"\nRakan:{ans}"
        return ans, OWNER_PREF["voice_mode"] if is_owner else False

    return "Shadow thoda busy hai Malik, 10 sec baad bolna 👑", False

@app.route("/api", methods=["POST","GET"])
@app.route("/webhook", methods=["POST","GET"])
@app.route("/api/webhook", methods=["POST","GET"])
@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"V134 FIXED 👑 {ensure_webhook()} GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)}",200
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
    reply, want_voice = brain(text, user_id, is_owner, username)
    if not reply: return "ok",200
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":reply[:4000]}, timeout=10)
        if is_owner and want_voice:
            audio=eleven_tts(reply, is_owner=True)
            if audio: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.mp3", audio)}, timeout=20)
    except: pass
    return "ok",200

@app.route("/")
def home(): return f"V134 Monarch FINAL FIXED 👑 GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} {ensure_webhook()} Chats:{len(CHAT_LOG)}",200

@app.route("/health")
def health(): return jsonify({"groq":len(GROQ_KEYS),"gemini":len(GEMINI_KEYS),"voice":OWNER_PREF["voice_mode"],"webhook":ensure_webhook()}),200

@app.route("/fix")
def fix():
    global GROQ_KEYS, GEMINI_KEYS
    GROQ_KEYS, GEMINI_KEYS = get_all_keys()
    BAD_KEYS.clear()
    return f"FIXED V134 {ensure_webhook()} GROQ:{len(GROQ_KEYS)}",200
