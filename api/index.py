import os, time, json, base64, datetime, requests
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# ========== CONFIG ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = int(os.environ.get("OWNER_ID","0") or 0)
MY_URL = os.environ.get("MY_URL","").rstrip("/")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY","")
MALE_VOICE_ID = os.environ.get("ELEVEN_MALE_VOICE","pNInz6obpgDQGcFmaJgB")
FEMALE_VOICE_ID = os.environ.get("ELEVEN_FEMALE_VOICE","EXAVITQu4vr4xnSDxMaL")
REPLICATE_TOKEN = os.environ.get("REPLICATE_API_TOKEN","")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
MALIK_NAME = "MD Saif Ahmad"

# ========== STORAGE ==========
MEMORY = {}
ABUSE = {}
OWNER_PREF = {"voice_mode": False, "voice_gender": "female"}
CHAT_LOG = []
BAD_KEYS = {}
_LAST_WEBHOOK = 0

def upstash(cmd, key, val=None):
    if not UPSTASH_URL or not UPSTASH_TOKEN: return None
    try:
        headers = {"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        if cmd=="get":
            r=requests.get(f"{UPSTASH_URL}/get/{key}", headers=headers, timeout=5)
            if r.status_code==200:
                d=r.json().get("result")
                return json.loads(d) if d else None
        if cmd=="set" and val is not None:
            requests.post(f"{UPSTASH_URL}", headers=headers, json=["SET", key, json.dumps(val)], timeout=5)
            return True
    except: pass
    return None

def load_persist():
    global MEMORY, ABUSE, OWNER_PREF, CHAT_LOG
    MEMORY = upstash("get","RAKAN_MEM") or {}
    ABUSE = upstash("get","RAKAN_ABUSE") or {}
    OWNER_PREF = upstash("get","RAKAN_PREF") or OWNER_PREF
    CHAT_LOG = upstash("get","RAKAN_LOGS") or []

def save_persist():
    upstash("set","RAKAN_MEM", MEMORY)
    upstash("set","RAKAN_ABUSE", ABUSE)
    upstash("set","RAKAN_PREF", OWNER_PREF)
    upstash("set","RAKAN_LOGS", CHAT_LOG[-200:])

load_persist()

# ========== KEYS ROTATION ==========
def get_keys():
    g, gm, o = [], [], []
    for k,v in os.environ.items():
        if not v: continue
        parts = [p.strip().strip('"').strip("'") for p in str(v).replace("\n",",").split(",") if p.strip()]
        for p in parts:
            if p.startswith("gsk_") and p not in g: g.append(p)
            elif p.startswith("AIza") and p not in gm: gm.append(p)
            elif p.startswith("sk-") and p not in o: o.append(p)
    return g, gm, o

GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_keys()
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k] < 900
def mark_bad(k): BAD_KEYS[k]=time.time()

def ensure_webhook():
    global _LAST_WEBHOOK
    if time.time()-_LAST_WEBHOOK < 3600: return "CACHED"
    _LAST_WEBHOOK=time.time()
    if not BOT_TOKEN or not MY_URL: return "NO CONFIG"
    try:
        exp = f"{MY_URL}/webhook"
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=8).json()
        cur = info.get("result",{}).get("url","")
        if cur == exp: return "OK"
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":exp}, timeout=8)
        return "SET"
    except Exception as e: return str(e)

# ========== AI PERSONA (Bot nahi, AI) ==========
SYSTEM_PROMPT = f"""You are Rakan, a highly intelligent AI assistant created by {MALIK_NAME}.
You are NOT a bot. You talk like a smart human friend.
- You remember conversation history and context.
- You answer in natural Hinglish if user uses Hinglish, English if English.
- You are expert in coding, study, health, tech, and daily life.
- You never say "As an AI language model". Just answer directly and smartly.
- Keep answers clear, helpful, and human-like. Not robotic.
- Owner is {MALIK_NAME}. Treat him with respect but don't overdo "Ji Malik" on every line. Be natural.
"""

# ========== TELEGRAM ==========
def tg_send(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:4000]}, timeout=10)
    except: pass

def tg_send_photo(chat_id, photo_url, caption=""):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id":chat_id,"photo":photo_url,"caption":caption[:1000]}, timeout=20)
    except: pass

def tg_get_file(file_id):
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        fp=r["result"]["file_path"]
        url=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}"
        return requests.get(url, timeout=30).content, fp
    except: return None, None

# ========== AI BRAINS (Sahi Jagah Pe Use) ==========
def ask_groq(messages):
    for k in GROQ_KEYS:
        if is_bad(k): continue
        try:
            r=requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization":f"Bearer {k}"},
            json={"model":"llama-3.3-70b-versatile","messages":messages,"temperature":0.7,"max_tokens":800}, timeout=15)
            if r.status_code==200: return r.json()["choices"][0]["message"]["content"]
            if r.status_code in [401,429]: mark_bad(k)
        except: continue
    return None

def ask_openai(messages):
    # OpenAI = Smart kaam ke liye
    for k in OPENAI_KEYS:
        if is_bad(k): continue
        try:
            r=requests.post("https://api.openai.com/v1/chat/completions", headers={"Authorization":f"Bearer {k}"},
            json={"model":"gpt-4o-mini","messages":messages,"temperature":0.7,"max_tokens":800}, timeout=20)
            if r.status_code==200: return r.json()["choices"][0]["message"]["content"]
            if r.status_code in [401,429]: mark_bad(k)
        except: continue
    return None

def ask_gemini(messages):
    prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        try:
            genai.configure(api_key=k)
            model=genai.GenerativeModel("gemini-2.0-flash")
            res=model.generate_content(prompt)
            if res.text: return res.text
        except: continue
    return None

def transcribe_voice(audio_bytes):
    # Pehle OpenAI Whisper (best), fir Groq Whisper
    for k in OPENAI_KEYS:
        try:
            files = {"file": ("voice.ogg", audio_bytes, "audio/ogg")}
            data = {"model": "whisper-1"}
            r = requests.post("https://api.openai.com/v1/audio/transcriptions", headers={"Authorization": f"Bearer {k}"}, files=files, data=data, timeout=20)
            if r.status_code==200: return r.json().get("text")
        except: continue
    return None

# ========== MAIN BRAIN ==========
GALI_DICT = {
    "madarchod": "Madarchod ka full form hai: Maa ko chodne wala, ye gali maa ke liye di jati hai.",
    "behenchod": "Behenchod ka full form hai: Behen ko chodne wala.",
    "bhenchod": "Bhenchod ka full form hai: Behen ko chodne wala.",
    "chutiya": "Chutiya ka matlab hai: Bewakoof, chut se nikla hua bewakoof insaan.",
    "randi": "Randi ka full form hai: Vaishya, paiso ke liye sharir bechne wali.",
    "bsdk": "BSDK ka full form hai: Bhosdi Ke, matlab chut ke baal wala bewakoof.",
    "lodu": "Lodu ka matlab hai: Lund jaisa bewakoof, kisi kaam ka nahi."
}

def brain(text, uid, is_owner, uname):
    global MEMORY, ABUSE
    if uid not in MEMORY: MEMORY[uid]={"history":[],"role":"friend"}
    if uid not in ABUSE: ABUSE[uid]=0

    low=text.lower().strip()
    CHAT_LOG.append({"id":uid,"name":uname,"text":text,"time":datetime.datetime.now().strftime("%H:%M")})
    if len(CHAT_LOG)>300: CHAT_LOG.pop(0)

    # Role Commands
    if "girlfriend ban" in low: MEMORY[uid]["role"]="girlfriend"; return "Theek hai, ab se main tumhari girlfriend mode me hu. Bolo jaan?", False
    if "bhai ban" in low: MEMORY[uid]["role"]="bhai"; return "Haan bhai, bol kya scene hai?", False
    if "teacher ban" in low: MEMORY[uid]["role"]="teacher"; return "Teacher mode on. Kya padhna hai aaj?", False

    # Owner Voice Controls
    if is_owner:
        if "female voice" in low: OWNER_PREF["voice_gender"]="female"; save_persist(); return "Female voice set kar di hai.", False
        if "male voice" in low: OWNER_PREF["voice_gender"]="male"; save_persist(); return "Male voice set kar di hai.", False
        if "voice me bol" in low: OWNER_PREF["voice_mode"]=True; save_persist(); return "Voice mode on kar diya hai.", True
        if "text me bol" in low: OWNER_PREF["voice_mode"]=False; save_persist(); return "Text mode on kar diya hai.", False

    # Gali System - 3 Warning ke baad Full Form
    found_gali = None
    for g in GALI_DICT.keys():
        if g in low.split() or f" {g} " in f" {low} ": found_gali = g; break

    if found_gali and not is_owner:
        ABUSE[uid]+=1; save_persist()
        if ABUSE[uid]==1: return "Pehli warning: Gali mat do, tameez se baat karo.", False
        if ABUSE[uid]==2: return "Dusri warning: Fir gali di to main bhi jawab dunga.", False
        if ABUSE[uid]==3: return "Teesri warning: Ye last hai, ab gali di to full form bata dunga.", False
        if ABUSE[uid]>3: return f"Tumne '{found_gali}' gali di hai. {GALI_DICT[found_gali]} Ab tameez seekh lo.", False

    # AI Chat with History
    history = MEMORY[uid]["history"][-6:]
    messages = [{"role":"system","content":SYSTEM_PROMPT + f"\nCurrent Role: {MEMORY[uid]['role']}"}]
    for h in history: messages.append(h)
    messages.append({"role":"user","content":text})

    ans = ask_groq(messages)
    if not ans: ans = ask_openai(messages) # Smart fallback
    if not ans: ans = ask_gemini(messages)
    if not ans: ans = "Network thoda slow hai, ek baar fir try karo."

    MEMORY[uid]["history"].append({"role":"user","content":text})
    MEMORY[uid]["history"].append({"role":"assistant","content":ans})
    save_persist()
    return ans, (OWNER_PREF["voice_mode"] if is_owner else False)

# ========== VOICE & MEDIA ==========
def eleven_tts(text):
    if not ELEVEN_API_KEY: return None
    try:
        vid = FEMALE_VOICE_ID if OWNER_PREF.get("voice_gender")=="female" else MALE_VOICE_ID
        r=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key":ELEVEN_API_KEY},
        json={"text":text[:800],"model_id":"eleven_multilingual_v2"}, timeout=25)
        if r.status_code==200: return r.content
    except: pass
    return None

def send_reply(chat_id, text, is_owner, want_voice):
    tg_send(chat_id, text)
    if is_owner and want_voice:
        audio = eleven_tts(text)
        if audio:
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.mp3", audio, "audio/mpeg")}, timeout=30)
            except: pass

def replicate_run(version, input_dict):
    if not REPLICATE_TOKEN: return None
    try:
        headers={"Authorization":f"Token {REPLICATE_TOKEN}"}
        r=requests.post("https://api.replicate.com/v1/predictions", headers=headers, json={"version":version,"input":input_dict}, timeout=15)
        if r.status_code not in [200,201]: return None
        pid=r.json()["id"]
        for _ in range(20): # Vercel ke liye sirf 50 sec max
            time.sleep(2.5)
            s=requests.get(f"https://api.replicate.com/v1/predictions/{pid}", headers=headers, timeout=10).json()
            if s["status"]=="succeeded": return s["output"]
            if s["status"]=="failed": return None
    except: return None
    return None

# ========== ROUTES (Secure) ==========
@app.route("/", methods=["GET"])
def home(): return f"Rakan AI Live | Groq:{len(GROQ_KEYS)} OpenAI:{len(OPENAI_KEYS)} Gemini:{len(GEMINI_KEYS)} Webhook:{ensure_webhook()}",200

@app.route("/health", methods=["GET"])
def health(): return jsonify({"groq":len(GROQ_KEYS),"openai":len(OPENAI_KEYS),"gemini":len(GEMINI_KEYS),"owner":OWNER_ID}),200

@app.route("/chats", methods=["GET"])
def chats():
    if str(request.args.get("id",""))!= str(OWNER_ID): return "Access Denied",403
    html="<h2>Rakan Chat Logs</h2>"
    for c in CHAT_LOG[::-1]: html+=f"<p><b>{c['name']}:</b> {c['text']}</p><hr>"
    return html,200

@app.route("/fix", methods=["GET"])
def fix():
    if str(request.args.get("id",""))!= str(OWNER_ID): return "Access Denied",403
    global GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS
    GROQ_KEYS, GEMINI_KEYS, OPENAI_KEYS = get_keys()
    BAD_KEYS.clear(); load_persist()
    return f"Fixed. Webhook: {ensure_webhook()}",200

@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return "Rakan AI Webhook Active",200
    data=request.get_json(silent=True) or {}
    msg=data.get("message",{}) or {}
    chat_id=msg.get("chat",{}).get("id")
    user_id=msg.get("from",{}).get("id",0)
    uname=msg.get("from",{}).get("first_name","User")
    text=msg.get("text","") or msg.get("caption","") or ""
    if not chat_id: return "ok",200
    is_owner = (user_id==OWNER_ID)

    # Photo Edit
    fbytes=None
    if msg.get("photo"): fbytes,_=tg_get_file(msg["photo"][-1]["file_id"])
    if fbytes and text:
        low=text.lower()
        tg_send(chat_id, "Photo edit kar raha hu, 20-30 second lagega...")
        b64 = f"data:image/jpeg;base64,{base64.b64encode(fbytes).decode()}"
        out=None
        if "background" in low: out=replicate_run("a9758cbfbd5f3c2094457d996e30b99969333e9a42f0d6d9ec1bc1b1c5a1a1c3b", {"image": b64})
        elif "hd" in low or "upscale" in low: out=replicate_run("42a996d39a96aedc57b2e0aa8105dea39d42db6cc2ad6d9542d37dbffa872a6e", {"image": b64, "scale":2})
        if out:
            url = out if isinstance(out,str) else out[0]
            tg_send_photo(chat_id, url, "Ho gaya, kaisa laga?")
        else: tg_send(chat_id, "Edit fail hua, Replicate me credit check karo.")
        return "ok",200

    # Voice Note
    if msg.get("voice"):
        vdata,_=tg_get_file(msg["voice"]["file_id"])
        if vdata:
            transcribed = transcribe_voice(vdata)
            if transcribed: text = transcribed
            else: tg_send(chat_id, "Voice samajh nahi aayi, text me likh do."); return "ok",200

    if not text:
        if fbytes: tg_send(chat_id, "Photo mil gayi. Batao iske saath kya karna hai? 'background hata de' ya 'hd bana de' likho.")
        return "ok",200

    ans, want_voice = brain(text, user_id, is_owner, uname)
    send_reply(chat_id, ans, is_owner, want_voice)
    return "ok",200

if __name__ == "__main__":
    app.run(debug=True)
