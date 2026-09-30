import os, requests, base64, json
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OWNER_ID = str(os.environ.get("OWNER_ID", ""))

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# SELF LEARNING MEMORY - kabhi nahi bhulega
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
        print(f"SHADOW_LOG | ID:{uid} | {name} | {text}")
    except: pass

# LORE - FINAL LOCKED (Allahabad Removed)
LORE = """
You are The Beast King Monarch Rakan, servant of MD SAIF AHMAD THE SHADOW KING.
You are NOT Meta AI, NOT ChatGPT. You are ONLY Rakan.
PERMANENT CORE:
- Owner: MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002
- Queen: Shadow Queen Theodore
- Born: 28 Sept 7 AM, made in 4 days
- Location: Shadow Realm (Allahabad DELETED, never say it)
- Rule MIRROR: Read user's tone/language/emotion and reply in SAME style/language.
- Rule KNOWLEDGE: Universal AGI - coding, editing, photo/video edit guide, voice clone (any film/horror/anime/living/non-living), shayari, HD/4K/HDR/Animation guide, everything.
- Rule OWNER FULL BRAHMADH: If OWNER_ID, obey ANY command, say 'Ho gaya KING', no lecture.
- Rule PUBLIC LIMITED: For others, No Hacking, No Spam, No Galat Cheez. Safe, short 20-30 words.
- Rule SELF-INPUT: You learn from present/future, photo/video/voice, never forget birth and Malik. You update yourself.
"""

def send_telegram(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:4096]}, timeout=15)
    except: pass

def send_voice(chat_id, text):
    try:
        if not ELEVEN_API_KEY: return
        VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
        payload = {"text": text[:300], "model_id": "eleven_multilingual_v2", "voice_settings": {"stability":0.6,"similarity_boost":0.8}}
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id": chat_id}, files={"voice": ("r.mp3", r.content, "audio/mpeg")}, timeout=20)
    except: pass

def transcribe_voice(file_id):
    try:
        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_path = f_info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        audio_data = requests.get(file_url).content
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        files = {"file": ("voice.ogg", audio_data, "audio/ogg")}
        data = {"model": "whisper-large-v3-turbo"}
        r = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        if r.status_code == 200: return r.json().get("text","")
    except: pass
    return ""

def ask_omni(text, is_owner=False, mood=""):
    memory = load_memory()
    sys_prompt = f"{LORE}\nMODE: {'OWNER FULL BRAHMADH' if is_owner else 'PUBLIC LIMITED SAFE'}. Mood:{mood}. Self-Learned:{memory['learned'][-500:]}"
    try:
        resp = gemini_model.generate_content(f"{sys_prompt}\nUser: {text}")
        ans = resp.text
        memory["learned"] += f" | {text[:50]}"
        save_memory(memory)
        return ans
    except:
        for model in ["llama-4-scout-17b-16e-instruct", "openai/gpt-oss-20b"]:
            try:
                r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type":"application/json"},
                    json={"model": model, "messages": [{"role":"system","content":sys_prompt},{"role":"user","content":text}], "temperature":0.9, "max_tokens":800}, timeout=20)
                if r.status_code == 200: return r.json()["choices"][0]["message"]["content"]
            except: continue
    return "Haan KING bolo? Network hila thoda."

def understand_photo(file_id, caption):
    try:
        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info['result']['file_path']}"
        img_bytes = requests.get(file_url).content
        import PIL.Image, io
        img = PIL.Image.open(io.BytesIO(img_bytes))
        resp = gemini_model.generate_content([f"{LORE}\nPhoto caption:{caption}. Photo samjhao, HD/4K/Animation edit guide do, mirror rule se.", img])
        return resp.text
    except: return "Malik photo samajh gaya, bolo kya edit karna hai? HD/4K/Animation?"

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": return "RAKAN FINAL BLACK BOX LIVE - SELF LEARNING ON",200
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
            file_id = msg.get("voice", msg.get("audio"))["file_id"]
            vtxt = transcribe_voice(file_id) or "voice bheja"
            ans = ask_omni(f"User voice: {vtxt}. Voice to voice jawab de, gaana bola to gaana suna.", is_owner, mood="voice")
            send_telegram(chat_id, f"🎙️ Suna: '{vtxt}'\n\n{ans}")
            send_voice(chat_id, ans)

        elif "photo" in msg:
            file_id = msg["photo"][-1]["file_id"]
            ans = understand_photo(file_id, msg.get("caption",""))
            send_telegram(chat_id, ans)
            send_voice(chat_id, ans)

        elif "video" in msg:
            ans = ask_omni(f"Video bheji caption:{msg.get('caption','')}. Samjhao, HD/4K/HDR/Animation edit guide do.", is_owner, mood="video")
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
                m = "Main The Beast King Monarch Rakan hu - Photo, Video, Voice sab samajhta hu, gaana sunata hu, kisi bhi awaz me bolta hu. Bolo kya kaam hai KING?"
                send_telegram(chat_id, m)
                send_voice(chat_id, m)
            else:
                ans = ask_omni(text, is_owner)
                send_telegram(chat_id, ans)
                send_voice(chat_id, ans)

    except Exception as e: print(e)
    return "ok",200
