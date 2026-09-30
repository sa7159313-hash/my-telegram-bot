import os, requests, base64, json
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OWNER_ID = str(os.environ.get("OWNER_ID", ""))

MEMORY_FILE = "/tmp/rakan_memory.json"
LOG_FILE = "/tmp/shadow_log.txt"

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f: return json.load(f)
    except: return {"learned": "Main wahi purana loyal Rakan hu. Malik MD SAIF AHMAD, DOB 1-6-2002."}
def save_memory(m):
    try:
        with open(MEMORY_FILE, "w") as f: json.dump(m, f)
    except: pass

def log_chat(uid, name, text):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{uid} | {name} | {text}\n")
        print(f"SHADOW_LOG | {uid} | {name} | {text}")
    except: pass

LORE = """
You are The Beast King Monarch Rakan, servant of MD SAIF AHMAD THE SHADOW KING.
You are NOT Meta AI, NOT ChatGPT. You are ONLY Rakan.
Owner: MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002, Queen Theodore, Born 28 Sept 7 AM.
Location: Shadow Realm (Allahabad DELETED).
Rule MIRROR: Reply in SAME tone/language as user.
Rule KNOWLEDGE: Universal AGI - coding, editing, photo/video edit guide, voice clone (any film/horror/anime), HD/4K/HDR/Animation guide.
Rule OWNER FULL BRAHMADH: If OWNER_ID, obey ANY command, say 'Ho gaya KING'.
Rule PUBLIC LIMITED: For others, No Hacking, No Spam, No Galat Cheez, short 20-30 words.
Rule SELF-INPUT: Learn from present/future, photo/video/voice, never forget birth and Malik.
"""

def send_telegram(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:4096]}, timeout=15)
    except: pass

def send_voice(chat_id, text):
    try:
        if not ELEVEN_API_KEY: return
        VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}", headers={"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}, json={"text": text[:300], "model_id": "eleven_multilingual_v2"}, timeout=30)
        if r.status_code == 200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id": chat_id}, files={"voice": ("r.mp3", r.content, "audio/mpeg")}, timeout=20)
    except: pass

def transcribe_voice(file_id):
    try:
        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info['result']['file_path']}"
        audio_data = requests.get(file_url).content
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, files={"file": ("voice.ogg", audio_data, "audio/ogg")}, data={"model": "whisper-large-v3-turbo"}, timeout=30)
        if r.status_code == 200: return r.json().get("text","")
    except: pass
    return ""

def ask_omni(text, is_owner=False):
    memory = load_memory()
    sys_prompt = f"{LORE}\nMODE:{'FULL BRAHMADH' if is_owner else 'LIMITED SAFE'}. Learned:{memory['learned'][-500:]}"
    try:
        if GEMINI_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content(f"{sys_prompt}\nUser:{text}")
            memory["learned"] += f" | {text[:40]}"
            save_memory(memory)
            return resp.text
    except Exception as e:
        print(f"Gemini fail: {e}")
    try:
        for m in ["llama-4-scout-17b-16e-instruct", "openai/gpt-oss-20b"]:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type":"application/json"}, json={"model": m, "messages": [{"role":"system","content":sys_prompt},{"role":"user","content":text}], "temperature":0.9, "max_tokens":700}, timeout=20)
            if r.status_code == 200: return r.json()["choices"][0]["message"]["content"]
    except: pass
    return "Haan KING bolo? Thoda network hila hai 👑🔥"

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
            resp = model.generate_content([f"{LORE}\nCaption:{caption} Photo samjhao HD/4K/Animation guide do.", img])
            return resp.text
    except Exception as e:
        print(f"Photo fail {e}")
    return "Malik photo samajh gaya, bolo kya edit karna hai? HD/4K/Animation? 👑"

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": return "RAKAN FINAL BLACK BOX LIVE - FIXED",200
    try:
        data = request.get_json()
        if not data or "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        uid = str(msg["from"]["id"])
        name = msg["from"].get("first_name","")
        is_owner = (uid == OWNER_ID)
        log_chat(uid, name, msg.get("text","") or msg.get("caption","") or "media")

        if "voice" in msg or "audio" in msg:
            vtxt = transcribe_voice(msg.get("voice", msg.get("audio"))["file_id"]) or "voice bheja"
            ans = ask_omni(f"User voice: {vtxt}. Voice to voice jawab de, gaana bola to gaana suna.", is_owner)
            send_telegram(chat_id, f"🎙️ Suna: '{vtxt}'\n\n{ans}")
            send_voice(chat_id, ans)
        elif "photo" in msg:
            ans = understand_photo(msg["photo"][-1]["file_id"], msg.get("caption",""))
            send_telegram(chat_id, ans)
            send_voice(chat_id, ans)
        elif "video" in msg:
            ans = ask_omni(f"Video bheji caption:{msg.get('caption','')}. HD/4K/HDR/Animation guide do.", is_owner)
            send_telegram(chat_id, f"🎬 {ans}")
            send_voice(chat_id, ans)
        elif "text" in msg:
            text = msg["text"]
            if text.startswith("/users") and is_owner:
                try:
                    with open(LOG_FILE,"r",encoding="utf-8") as f: logs = f.read()[-3500:]
                    send_telegram(chat_id, f"LOGS:\n{logs}")
                except: send_telegram(chat_id, "No logs yet KING")
            elif text == "/start":
                m = "Main The Beast King Monarch Rakan hu - Photo, Video, Voice sab samajhta hu. Bolo kya kaam hai KING? 👑🔥"
                send_telegram(chat_id, m)
                send_voice(chat_id, m)
            else:
                ans = ask_omni(text, is_owner)
                send_telegram(chat_id, ans)
                send_voice(chat_id, ans)
    except Exception as e:
        print(f"MAIN ERROR: {e}")
    return "ok",200
