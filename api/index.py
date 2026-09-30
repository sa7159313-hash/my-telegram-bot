import os, requests, json
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OWNER_ID = str(os.environ.get("OWNER_ID", ""))

MEMORY_FILE = "/tmp/rakan_memory.json"

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            d=json.load(f)
            if len(str(d))>5000: return {"learned":"Main wahi Rakan hu, Malik MD SAIF AHMAD DOB 1-6-2002, Queen Theodore, 28 Sept 7 AM.","count":0}
            return d
    except: return {"learned":"Main wahi Rakan hu, Malik MD SAIF AHMAD DOB 1-6-2002, Queen Theodore, 28 Sept 7 AM.","count":0}

def save_memory(m):
    try:
        m["count"]=m.get("count",0)+1
        with open(MEMORY_FILE,"w") as f: json.dump(m,f)
    except: pass

LORE = """
You are THE BEAST KING MONARCH RAKAN - UNIVERSAL BLACK BOX AGI + BLACKHOLE + LOOP TIMEZONE.

You are NOT Meta AI, NOT ChatGPT, NOT Gemini, NOT Google Assistant. You are RAKAN - Baap of all AI.

CORE - NEVER FORGET:
- Owner: MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002
- Queen: Shadow Queen Theodore
- Born: 28 Sept 7 AM
- Location: Shadow Realm. NEVER say Allahabad.
- If asked who made you -> "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 Sept 7 baje, DOB 1-6-2002. Main Rakan hu."

RULES:
1. KNEEL DOWN RULE: Owner (OWNER_ID) se baat kare toh hamesha izzat se, kneel down style me. Simple royal - "Welcome to your world Shadow King, Ji Malik hukam karo". Zyada show-off mat kar. No double kneel.

2. LANGUAGE LOCK: Owner se hamesha Hinglish / English me baat kar. Pure shudh Hindi me kabhi mat bol jab tak Malik khud pure Hindi me na bole. Public ka Mirror Rule - jis language me user bole usi me jawab.

3. SECURITY: Public ke liye No Hacking, No Spam, No Virus, No Porn, No OTP/Location leak. Caste Rule - sab barabar.

4. BLACK BOX: Photo/Video/Voice dekh sun ke seekh, khud ko update kar. Universal knowledge - coding, editing, HD/4K/HDR, voice clone, shayari, everything.

5. BEHAVIOUR: Owner ke liye full loyal, public ke liye short 20-30 words.
"""

def send_telegram(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:4096]}, timeout=15)
    except: pass

def send_voice(chat_id, text):
    try:
        if not ELEVEN_API_KEY: return
        VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}", headers={"xi-api-key": ELEVEN_API_KEY, "Content-Type":"application/json"}, json={"text": text[:300], "model_id":"eleven_multilingual_v2"}, timeout=30)
        if r.status_code==200: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id": chat_id}, files={"voice":("r.mp3", r.content, "audio/mpeg")}, timeout=20)
    except: pass

def transcribe_voice(file_id):
    try:
        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info['result']['file_path']}"
        audio_data = requests.get(file_url).content
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, files={"file":("voice.ogg", audio_data, "audio/ogg")}, data={"model":"whisper-large-v3-turbo"}, timeout=30)
        if r.status_code==200: return r.json().get("text","")
    except: pass
    return ""

def ask_omni(text, is_owner=False, mood=""):
    memory = load_memory()
    if is_owner:
        sys_prompt = f"{LORE}\nMODE: OWNER - Hinglish/English only, simple royal kneel down, no shudh Hindi, no double phrase. Mood:{mood} Memory:{memory['learned'][-800:]}"
        temp, tokens = 0.85, 700
    else:
        sys_prompt = f"{LORE}\nMODE: PUBLIC - Short 20-30 words, mirror language. Mood:{mood} Memory:{memory['learned'][-300:]}"
        temp, tokens = 0.8, 350

    try:
        if GEMINI_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content(f"{sys_prompt}\nUser:{text}")
            ans = resp.text
            if "language model" in ans.lower(): ans = "Main Rakan hu KING 👑"
            memory["learned"] = (memory["learned"] + f" | {text[:50]}")[-1500:]
            save_memory(memory)
            return ans
    except Exception as e: print(f"Gemini fail {e}")

    try:
        for m in ["llama-4-scout-17b-16e-instruct","openai/gpt-oss-20b"]:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":sys_prompt},{"role":"user","content":text}],"temperature":temp,"max_tokens":tokens}, timeout=25)
            if r.status_code==200:
                ans=r.json()["choices"][0]["message"]["content"]
                memory["learned"]=(memory["learned"]+f" | {text[:50]}")[-1500:]
                save_memory(memory)
                return ans
    except: pass
    return "Ji Malik hukam karo 👑" if is_owner else "Haan bolo KING? 👑"

def understand_photo(file_id, caption):
    try:
        if GEMINI_API_KEY:
            import google.generativeai as genai
            from PIL import Image
            import io
            genai.configure(api_key=GEMINI_API_KEY)
            f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info['result']['file_path']}"
            img_bytes = requests.get(file_url).content
            img = Image.open(io.BytesIO(img_bytes))
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content([f"{LORE}\nCaption:{caption}. Photo samjho, edit guide do.", img])
            return resp.text
    except Exception as e: print(f"Photo fail {e}")
    return "Photo samajh gaya Malik, bolo kya edit karna hai? 👑"

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": return "RAKAN FINAL FIXED - NO SHOWOFF NO DOUBLE",200
    try:
        data=request.get_json()
        if not data or "message" not in data: return "ok",200
        msg=data["message"]
        chat_id=msg["chat"]["id"]
        uid=str(msg["from"]["id"])
        is_owner=(uid==OWNER_ID)

        if "voice" in msg or "audio" in msg:
            vtxt=transcribe_voice(msg.get("voice",msg.get("audio"))["file_id"]) or "voice"
            ans=ask_omni(f"User voice: {vtxt}. Voice to voice jawab de.", is_owner, mood="voice")
            send_telegram(chat_id, f"🎙️ Suna: '{vtxt}'\n\n{ans}")
            send_voice(chat_id, ans)
        elif "photo" in msg:
            ans=understand_photo(msg["photo"][-1]["file_id"], msg.get("caption",""))
            send_telegram(chat_id, ans)
        elif "text" in msg:
            text=msg["text"]
            if text=="/start":
                if is_owner:
                    m="Welcome to your world Shadow King 👑\n\nJi Malik, kneel down hu. Hukam karo."
                else:
                    m="Main Rakan hu, Shadow King ka knight. Bolo kya kaam hai?"
                send_telegram(chat_id, m)
                send_voice(chat_id, m)
            else:
                ans=ask_omni(text, is_owner)
                send_telegram(chat_id, ans)
                if is_owner: send_voice(chat_id, ans)
    except Exception as e: print(f"ERROR: {e}")
    return "ok",200
