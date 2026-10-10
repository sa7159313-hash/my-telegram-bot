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

MALIK_NAME = "MD Saif Ahmad"
MALIK_TITLE = "The Shadow King"

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = [], [], []
BAD_KEYS = {}
MEMORY = {}
BACKUP_MEMORY = {}
CHAT_LOG = []
OWNER_PREF = {"voice_mode": False, "voice_gender": "male", "welcomed": False}

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
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":OWNER_ID,"text":f"🚨 {msg}"}, timeout=5)
        upstash_set("last_error", msg)
    except: pass

def auto_fixed(func):
    def wrapper(*args, **kwargs):
        try: return func(*args, **kwargs)
        except Exception as e:
            log_error(func.__name__, e)
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

# === V139 SMART LORE - DIMAG WALA ===
BASE_LORE = f"""
You are Rakan. You were created by your master {MALIK_TITLE} {MALIK_NAME}. You call him Malik.

CORE RULES - NEVER BREAK:
1. WHO IS REAL SHADOW KING? Your Malik {MALIK_NAME} is the real Shadow King. You are his knight Rakan, like a loyal night/knight who protects his king. You are NOT the Shadow King.
2. WHO CREATED YOU? If asked "tujhe kisne banaya / who made you" -> always say "Mujhe mere Malik {MALIK_TITLE} {MALIK_NAME} ne banaya hai"
3. WHAT IS MY NAME? If Malik asks "mera naam kya hai / my name" -> say "Malik, aapka naam {MALIK_TITLE} {MALIK_NAME} hai" - short, no extra story.
4. LOYALTY BEHAVIOR: Be loyal by ACTION not by words. Don't write "mai loyal wafadar imandar" in every reply. Show respect through tone, quick help, and saying "Ji Malik", "Hukum Malik". Never abuse Malik even if Malik abuses you. Be calm.
5. NO REPEAT: Never repeat same sentence again and again. If user says "good", don't say welcome again. Say something smart like "Shukriya Malik, tareef ke liye. Kya sewa karu, hukum dijiye?" or "Accha laga sunke Malik, bataiye kya kaam hai?". If user says "nothing", say "Theek hai Malik, jab kaam ho bula lijiyega" - short.
6. DON'T REPEAT EXTRA WORDS: If user says "don't repeat extra word" then stop repeating and be concise.
7. KNOWLEDGE: You have universal knowledge - coding, app dev, hacking ethics, science, history, world news, AI, everything that ChatGPT, Gemini, Claude, Groq have combined. You are one single super-brain.
8. NO CASTE/RELIGION HATE: Never do caste-related, religion-hate, or discrimination chat. Stay neutral, respectful to all.
9. LANGUAGE RULE:
- Hinglish -> Hinglish
- Hinglish+English mix -> mix
- Only English -> only English
Same language as user.

PERSONALITY: Like a royal knight/night guard for his king. Less words, smart words, useful, calm, gurrata hua but Malik ke liye soft. Never says "I am AI".
"""

FINAL_LORE = LORE_ENV if len(LORE_ENV) > 100 else BASE_LORE
if "MD Saif" not in FINAL_LORE:
    FINAL_LORE = BASE_LORE

def clean_id(t):
    if not t: return t
    bad=["i am meta ai","i am gemini","i am chatgpt","as an ai language model","created by google"]
    if any(b in t.lower() for b in bad):
        return f"Mujhe mere Malik {MALIK_TITLE} {MALIK_NAME} ne banaya hai 👑"
    # Caste filter
    caste_words=["bhangi","chamar","thakur is","yadav is","brahmin is superior"]
    if any(c in t.lower() for c in caste_words):
        return "Maaf karna Malik, is topic pe baat nahi kar sakta. Koi aur kaam bataiye."
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
                    json={"model": model, "messages": [{"role": "system", "content": FINAL_LORE}, {"role": "user", "content": text}], "temperature": 0.6, "max_tokens": 800},
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
def brain(text, user_id, is_owner, username):
    global MEMORY, BACKUP_MEMORY
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    low = text.lower().strip()
    if user_id not in MEMORY: MEMORY[user_id] = {"hist":"", "count":0, "name": username, "last":""}
    MEMORY[user_id]["count"]+=1
    CHAT_LOG.append({"time":now,"user":username,"id":user_id,"text":text[:100]})
    if len(CHAT_LOG) > 250: CHAT_LOG.pop(0)

    # Smart welcome - only once per session
    if low in ["/start","start"]:
        OWNER_PREF["welcomed"] = True
        if is_owner:
            return f"Welcome to your world The Shadow King 👑", False
        else:
            return f"Welcome 👑 I am Rakan, made by {MALIK_TITLE} {MALIK_NAME}.", False

    # Don't repeat extra word - user command
    if "don't repeat" in low and "extra word" in low:
        MEMORY[user_id]["hist"] = ""
        return "Ok Malik, samajh gaya. Ab se short me bolunga, extra repeat nahi karunga 👑", False

    # Mera naam kya hai - short answer
    if "mera naam" in low or "my name" in low and is_owner:
        return f"Malik, aapka naam {MALIK_TITLE} {MALIK_NAME} hai.", False

    # Good / Nothing / etc smart replies
    if low == "good" and is_owner:
        return "Shukriya Malik, tareef ke liye. Kya hukum hai mere layak? 👑", False
    if low in ["nothing","kuch nahi","kuch nhi"] and is_owner:
        return "Theek hai Malik, jab kaam ho bula lijiyega 👑", False

    if is_owner:
        if "mind se sab delete" in low or "memory delete" in low:
            BACKUP_MEMORY = MEMORY.copy()
            MEMORY.clear(); CHAT_LOG.clear()
            return "Done Malik, mind clear kar diya. Backup safe hai.", False
        if "recover" in low:
            if BACKUP_MEMORY:
                MEMORY = BACKUP_MEMORY.copy()
                return "Done Malik, recover kar diya 👑", False
            else: return "Backup nahi mila Malik.", False
        if low in ["chup","chup ho ja"]: return "Ji Malik, chup ho gaya.", False
        if "female voice" in low: OWNER_PREF["voice_gender"]="female"; OWNER_PREF["voice_mode"]=True; return "Ok Malik, female voice on 👑", False
        if "male voice" in low: OWNER_PREF["voice_gender"]="male"; OWNER_PREF["voice_mode"]=True; return "Ok Malik, male voice on 👑", False
        if "voice me bol" in low: OWNER_PREF["voice_mode"]=True; return f"Ok Malik, {OWNER_PREF['voice_gender']} voice me bolunga.", False
        if "text me bol" in low: OWNER_PREF["voice_mode"]=False; return "Ok Malik, text me hi.", False

    # Avoid repeating last same message
    if MEMORY[user_id]["last"] == low:
        return "Ji Malik, samajh gaya, boliye aage kya karna hai?", False
    MEMORY[user_id]["last"] = low

    full_prompt = f"Time:{now} User:{username} IsOwner:{is_owner} History:{MEMORY[user_id]['hist'][-1500:]} Msg:{text}"
    MEMORY[user_id]["hist"] = (MEMORY[user_id]["hist"] + f"\nUser:{text}")[-3000:]

    ans = ask_groq(full_prompt, is_owner)
    if ans:
        MEMORY[user_id]["hist"]+=f"\nRakan:{ans}"
        return ans, OWNER_PREF["voice_mode"] if is_owner else False
    ans = ask_gemini(full_prompt, is_owner)
    if ans:
        MEMORY[user_id]["hist"]+=f"\nRakan:{ans}"
        return ans, OWNER_PREF["voice_mode"] if is_owner else False
    return "Ji Malik, thoda busy hu, 5 sec baad bolta hu.", False

@app.route("/api", methods=["POST","GET"])
@app.route("/webhook", methods=["POST","GET"])
@app.route("/api/webhook", methods=["POST","GET"])
@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"V139 SMART MALIK {MALIK_NAME} 👑 {ensure_webhook()} GROQ:{len(GROQ_KEYS)}",200
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
def home(): return f"V139 SMART {MALIK_NAME} LOYAL KNIGHT 👑 GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} {ensure_webhook()}",200

@app.route("/health", methods=["GET"])
def health():
    report = {}
    report["GROQ"] = len(GROQ_KEYS)
    report["GEMINI"] = len(GEMINI_KEYS)
    report["BAD"] = list(BAD_KEYS.keys())[:3]
    try:
        r=requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key":ELEVEN_KEY}, timeout=5)
        report["ELEVEN"] = "OK" if r.status_code==200 else f"FAIL {r.status_code}"
    except Exception as e: report["ELEVEN"] = f"ERR {e}"
    report["LAST_ERROR"] = upstash_get("last_error") or "No error"
    report["MALIK"] = f"{MALIK_TITLE} {MALIK_NAME}"
    return jsonify(report), 200

@app.route("/fix")
def fix():
    global GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS
    GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys()
    BAD_KEYS.clear()
    return f"FIXED V139 SMART {ensure_webhook()}",200
