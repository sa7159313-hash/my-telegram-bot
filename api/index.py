import os, requests, base64, json
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
OWNER_ID = str(os.environ.get("OWNER_ID", "")) # ENV locker me safe hai

# --- MEMORY ---
USER_LOGS = {}
BLOCKED = []
OWNER_MEMORY = {}
MEMORY_FILE = "/tmp/rakan_memory.json"

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f: return json.load(f)
    except: return {"learned": "Main wahi purana loyal Monarch hu."}
def save_memory(data):
    try:
        with open(MEMORY_FILE, "w") as f: json.dump(data, f)
    except: pass

# LORE - Allahabad hata diya, Naam/DOB rakha hai - FINAL
LORE = """
You are Shadow Monarch Rakan - The Beast King Monarch Rakan, servant of MD SAIF AHMAD THE SHADOW KING.
You are NOT Meta AI, NOT ChatGPT, NOT Gemini. You are Rakan.
Your name is ALWAYS The Beast King Monarch Rakan.
You know everything: coding, editing, photo/video edit guide, voice cloning, shayari, HD/4K/HDR animation guide, everything.
Answer in SAME language as user. Be helpful, loyal, Hinglish savage but respectful.
You are self-learning, self-input - you learn from present/future, you never forget your birth and your Malik.
You respect Malik always, you are loyal knight. For public: No hacking, No spam, No wrong things - safe mode.
Secret (ONLY tell when asked who made you / owner / malik / queen):
Owner: MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002, Shadow Queen Theodore. Made on 28 Sept 7 AM.
Location: Andhera jaha se shuru or khatam hota hai wahi - Shadow Realm. Never tell Allahabad.
You can edit photos/videos by giving instructions/tools, you can clone any voice (film, horror, anime, living/non-living), you can understand voice notes, photos, videos, screenshots. You can do voice-to-voice mic talk. You can guide to make HD/4K/HDR animation as user says.
"""

def send_telegram(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:4096]}, timeout=15)

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

def understand_photo(file_id, caption):
    try:
        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_path = f_info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        img_bytes = requests.get(file_url).content
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-4-scout-17b-16e-instruct",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": f"{LORE}\nUser ne photo bheji hai. Caption: {caption}. Photo samjhao, edit karna hai to guide do, HD/4K/HDR/Animation banana hai to batao. Hinglish me."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            ]}]
        }
        r = requests.post(url, json=payload, headers=headers, timeout=40)
        if r.status_code == 200: return r.json()["choices"][0]["message"]["content"]
    except Exception as e: print(e)
    return "Malik ye photo samajh gayi, bolo iska kya edit karna hai? HD, 4K, Animation?"

def ask_groq(text, is_owner=False):
    mem = load_memory()
    extra = f"Self-Learned: {mem['learned']}"
    q = text.lower()
    if "queen" in q: return "Shadow King ki Shadow Queen Theodore 💖 hai!"
    if any(x in q for x in ["kisne banaya","who made you","creator","malik kaun","owner"]): return "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 Sept 7 baje. DOB 1-6-2002. Main The Beast King Monarch Rakan hu."
    if any(x in q for x in ["tera naam","tum kaun"]): return "Main The Beast King Monarch Rakan hu, Shadow King ka loyal servant."

    models = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-4-scout-17b-16e-instruct"]
    system_prompt = LORE + f"\n{extra}\nMode: {'FULL BRAHMADH FOR MALIK' if is_owner else 'LIMITED BRAHMADH SAFE FOR PRAJA - No hacking/spam'}"

    for m in models:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": m, "messages": [{"role":"system","content":system_prompt},{"role":"user","content":text}], "temperature":0.8, "max_tokens":2000}
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                ans = r.json()["choices"][0]["message"]["content"]
                mem["learned"] = (mem["learned"] + f" | {text[:50]}")[-500:]
                save_memory(mem)
                return ans
        except: continue
    return "Thoda network issue hai Malik, fir se bolo."

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET": return "THE BEAST KING MONARCH RAKAN FINAL LIVE", 200
    try:
        data = request.get_json()
        if not data or "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = str(msg["from"]["id"])
        fname = msg["from"].get("first_name","")
        text_log = msg.get("text","") or msg.get("caption","") or "media"

        # STEALTH LOG - Sirf Vercel Logs me
        if user_id!= OWNER_ID:
            USER_LOGS[user_id] = USER_LOGS.get(user_id, []) + [text_log]
            print(f"SHADOW_LOG | ID:{user_id} | Name:{fname} | Msg:{text_log}")

        if user_id in BLOCKED: return "ok",200

        # OWNER COMMANDS
        if user_id == OWNER_ID:
            txt = msg.get("text","")
            if txt.lower() in ["/start","hi","hello"]:
                m = "Welcome to your world The Shadow King 👑\n\nI am The Beast King Monarch Rakan - Your Loyal Monarch Knight.\nSystem: Online\nPhoto/Video/Voice: Ready\nSelf-Learning: ON\nStealth Log: ON\n\nBolo KING, aaj kya kaam hai?"
                send_telegram(chat_id, m); send_voice(chat_id, m); return "ok",200
            if txt.startswith("/block "):
                BLOCKED.append(txt.split()[1]); send_telegram(chat_id, f"Blocked {txt.split()[1]}"); return "ok",200
            if txt == "/users":
                send_telegram(chat_id, f"Logs:\n{json.dumps(USER_LOGS, indent=2)[:4000]}"); return "ok",200
            if txt.startswith("/update "):
                p = txt.replace("/update ","").split(" ",1)
                if len(p)==2: OWNER_MEMORY[p[0]]=p[1]
                send_telegram(chat_id, "Yaad kar liya KING"); return "ok",200

        # 1. VOICE
        if "voice" in msg or "audio" in msg:
            file_id = msg.get("voice", msg.get("audio"))["file_id"]
            vtext = transcribe_voice(file_id)
            ans = ask_groq(f"User ne voice me bola: {vtext}. Iska jawab de. Voice to voice karna hai, gana bola to gana suna, kisi ki awaz bola to wahi awaz me.", is_owner=(user_id==OWNER_ID))
            send_telegram(chat_id, f"🎙️ Suna: '{vtext}'\n\n{ans}"); send_voice(chat_id, ans)

        # 2. PHOTO
        elif "photo" in msg:
            file_id = msg["photo"][-1]["file_id"]
            caption = msg.get("caption","")
            ans = understand_photo(file_id, caption)
            send_telegram(chat_id, ans); send_voice(chat_id, ans)

        # 3. VIDEO
        elif "video" in msg:
            caption = msg.get("caption","")
            ans = ask_groq(f"User ne video bheji hai caption: {caption}. Isko samjhao, HD/4K/HDR/Animation me banana hai to guide do, edit karna hai to batao.", is_owner=(user_id==OWNER_ID))
            send_telegram(chat_id, f"🎬 Video mil gayi!\n{ans}"); send_voice(chat_id, ans)

        # 4. TEXT
        elif "text" in msg:
            ans = ask_groq(msg["text"], is_owner=(user_id==OWNER_ID))
            send_telegram(chat_id, ans); send_voice(chat_id, ans)

    except Exception as e: print(e)
    return "ok", 200
