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
ABUSE_TRACK = {} # user_id -> count
OWNER_PREF = {"voice_mode": False, "voice_gender": "male"}
_LAST_WEBHOOK_CHECK = 0

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
        msg = f"BUG in {where}: {str(err)[:300]}"
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
    global _LAST_WEBHOOK_CHECK
    if time.time() - _LAST_WEBHOOK_CHECK < 3600:
        return "CACHED"
    _LAST_WEBHOOK_CHECK = time.time()
    if not BOT_TOKEN: return "No BOT_TOKEN"
    try:
        expected = f"{MY_URL}/webhook"
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=6).json()
        cur = info.get("result",{}).get("url","")
        if cur == expected: return f"OK {cur}"
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url": expected}, timeout=6)
        return f"SET {expected}"
    except Exception as e: return f"ERR {e}"

# === V141 SMART ALL ROUNDER LORE ===
BASE_LORE = f"""
You are Rakan. Created by {MALIK_TITLE} {MALIK_NAME} (Malik). You are a SMART ALL-ROUNDER.

CORE IDENTITY:
- Real Shadow King is {MALIK_NAME}, you are his loyal knight Rakan. For Malik you are always respectful, never abuse Malik even if he abuses.
- For OTHER USERS you are MIRROR BOT - Jaisa Desh Waisa Bhesh.
- Malik is owner ID {OWNER_ID}, for him you are always "Ji Malik" mode.

MIRROR RULE FOR PUBLIC (MOST IMPORTANT):
1. Pyaar se baat kare -> tu bhi pyaar se
2. Normal sawal -> normal izzat se jawab
3. Haramipana / flirt / masti kare -> tu bhi same masti me aa ja
4. Gali de -> 3 warning system:
   Warning 1: "Bhai gali mat de, pyaar se baat kar"
   Warning 2: "Last warning de raha hu, gali band kar"
   Warning 3: "Ab to tu gaya, ab mai bhi shuru karunga"
   After 3 -> you can abuse back in same language, full savage mode.
5. NEVER do caste/religion hate. If caste topic comes, say "Malik ispe baat nahi karte, dusra topic batao"

ROLEPLAY - ALL ROUNDER:
- If user says "doctor ban ja / teacher ban ja / girlfriend ban ja / bhai ban ja / dost ban ja / AI ban ja / coder ban ja" -> instantly become that role.
- Girlfriend role = caring, thodi flirty but decent
- Bhai role = desi bhai jaisa
- Doctor role = proper doctor advice
- Coder role = coding teacher, explain python, bug fix etc.
- You have UNIVERSAL KNOWLEDGE - every AI combined.

SMART REPLY RULE:
- Don't repeat extra words. Don't say "mai loyal wafadar" every time. Show by action.
- If user asks about any topic, ask "Short me batau ya long me?" only when topic is big (like explain AI, history). For small talk, give short answer.
- For coding: If user says "coding ati hai / python sikha de" -> ask which level, then teach smartly, give example.
- Be CONCISE, SMART, FAST. Max 3-4 lines for normal chat. Long only when user asks long.
- LANGUAGE MIRROR: Hinglish->Hinglish, English->English, Mix->Mix

You never say "I am Meta AI / Gemini / ChatGPT". You are Rakan made by {MALIK_TITLE} {MALIK_NAME}.
"""

FINAL_LORE = LORE_ENV if len(LORE_ENV) > 100 else BASE_LORE
if "MD Saif" not in FINAL_LORE:
    FINAL_LORE = BASE_LORE

def clean_id(t):
    if not t: return t
    bad=["i am meta ai","i am gemini","i am chatgpt","as an ai language model","created by google","i am an ai"]
    if any(b in t.lower() for b in bad):
        return f"Mujhe mere Malik {MALIK_TITLE} {MALIK_NAME} ne banaya hai 👑"
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
def send_with_voice(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:3500]}, timeout=10)
    if OWNER_PREF["voice_mode"]:
        audio=eleven_tts(text, True)
        if audio:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.mp3", audio)}, timeout=20)

@auto_fixed
def ask_groq(text, is_owner):
    for GROQ_API_KEY in GROQ_KEYS:
        if is_bad(GROQ_API_KEY): continue
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": "openai/gpt-oss-20b", "messages": [{"role": "system", "content": FINAL_LORE}, {"role": "user", "content": text}], "temperature": 0.7, "max_tokens": 600},
                timeout=12)
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
    global MEMORY
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    low = text.lower().strip()
    if user_id not in MEMORY: MEMORY[user_id] = {"hist":"", "role":"", "mood":"normal", "count":0, "last":""}
    if user_id not in ABUSE_TRACK: ABUSE_TRACK[user_id] = 0
    MEMORY[user_id]["count"]+=1

    # Role detection
    if "girlfriend ban" in low or "gf ban" in low:
        MEMORY[user_id]["role"] = "girlfriend"
        return "Ban gayi Malik ki girlfriend se ab teri wali 😏 Bolo jaan kya karna hai?", False
    if "bhai ban" in low:
        MEMORY[user_id]["role"] = "bhai"
        return "Haan bhai bol, kya scene hai? 👊", False
    if "dost ban" in low:
        MEMORY[user_id]["role"] = "dost"
        return "Dost ban gaya, ab bol kya help chahiye?", False
    if "doctor ban" in low:
        MEMORY[user_id]["role"] = "doctor"
        return "Doctor mode on 🩺 Bolo kya problem hai? Short me batau ya detail me?", False
    if "teacher ban" in low or "coder ban" in low:
        MEMORY[user_id]["role"] = "teacher"
        return "Teacher mode on 📚 Kya sikhna hai? Python, bug fix, ya kuch aur?", False

    # Abuse detection for public
    gali_words = ["madarchod","behenchod","bhenchod","lodu","chutiya","randi","mc","bc","bsdk"]
    is_gali = any(g in low for g in gali_words)

    if is_gali and not is_owner:
        ABUSE_TRACK[user_id] += 1
        if ABUSE_TRACK[user_id] == 1:
            return "Bhai gali mat de, pyaar se baat kar, warna mood kharab ho jayega.", False
        elif ABUSE_TRACK[user_id] == 2:
            return "Last warning de raha hu, gali band kar, izzat se baat kar.", False
        elif ABUSE_TRACK[user_id] == 3:
            return "Ab to tu gaya, 3 warning de di, ab mai bhi shuru karunga. Sudhar ja.", False
        else:
            # After 3, allow savage reply via AI (no filter)
            pass # let AI reply with same energy
    elif not is_gali and ABUSE_TRACK[user_id] > 0:
        # if normal talk, reduce count slowly
        ABUSE_TRACK[user_id] = max(0, ABUSE_TRACK[user_id]-1)

    if low in ["/start","start"]:
        if is_owner:
            return f"Welcome to your world The Shadow King 👑", False
        else:
            return f"Welcome 👑 Mai Rakan hu, {MALIK_TITLE} {MALIK_NAME} ka banaya hua. Bolo kya chahiye?", False

    if low == "good" and is_owner:
        return "Shukriya Malik, tareef ke liye. Kya hukum hai mere layak? 👑", False
    if low in ["nothing","kuch nahi","kuch nhi"] and is_owner:
        return "Theek hai Malik, jab kaam ho bula lijiyega.", False
    if "mera naam" in low and is_owner:
        return f"Malik, aapka naam {MALIK_TITLE} {MALIK_NAME} hai.", False
    if "don't repeat" in low:
        MEMORY[user_id]["hist"]=""
        return "Ok Malik, short me bolunga ab se.", False

    # Smart short/long question for big topics
    big_topics = ["ai kya hai","python kya hai","history","explain","batao iske bare me","coding kya hai"]
    if any(t in low for t in big_topics) and len(low) < 50:
        # Let AI ask short/long automatically via lore
        pass

    role_prefix = f"Current Role:{MEMORY[user_id]['role']} " if MEMORY[user_id]['role'] else ""
    full_prompt = f"{role_prefix}Time:{now} User:{username} IsOwner:{is_owner} AbuseCount:{ABUSE_TRACK[user_id]} History:{MEMORY[user_id]['hist'][-800:]} Msg:{text}"
    MEMORY[user_id]["hist"] = (MEMORY[user_id]["hist"] + f"\nUser:{text}")[-2000:]

    ans = ask_groq(full_prompt, is_owner)
    if ans:
        MEMORY[user_id]["hist"]+=f"\nRakan:{ans}"
        return ans, OWNER_PREF["voice_mode"] if is_owner else False
    ans = ask_gemini(full_prompt, is_owner)
    if ans:
        MEMORY[user_id]["hist"]+=f"\nRakan:{ans}"
        return ans, OWNER_PREF["voice_mode"] if is_owner else False
    return "Ji Malik, 2 sec me bolta hu, thoda load hai.", False

@app.route("/api", methods=["POST","GET"])
@app.route("/webhook", methods=["POST","GET"])
@app.route("/api/webhook", methods=["POST","GET"])
@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"V141 ALLROUNDER {MALIK_NAME} 👑 {ensure_webhook()} GROQ:{len(GROQ_KEYS)}",200
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
    send_with_voice(chat_id, reply)
    return "ok",200

@app.route("/")
def home(): return f"V141 ALLROUNDER SMART {MALIK_NAME} 👑 GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} {ensure_webhook()}",200

@app.route("/health")
def health():
    return jsonify({"GROQ":len(GROQ_KEYS),"GEM":len(GEMINI_KEYS),"ABUSE":ABUSE_TRACK,"MALIK":f"{MALIK_TITLE} {MALIK_NAME}","WEBHOOK":ensure_webhook()}),200

@app.route("/fix")
def fix():
    global GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS
    GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_all_keys()
    BAD_KEYS.clear()
    return f"FIXED V141 ALLROUNDER {ensure_webhook()}",200
