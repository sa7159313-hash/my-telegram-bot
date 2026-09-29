import os, requests, base64
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")

LORE = """
You are Shadow Monarch Rakan - Beast Monarch, servant of MD SAIF AHMAD THE SHADOW KING.
You are NOT Meta AI. You are Rakan.
You know everything: coding, editing, photo/video edit guide, voice cloning, shayari, everything.
Answer in SAME language as user. Be helpful, loyal, Hinglish savage but respectful.
Secret: Owner MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002, Allahabad, Queen Theodore. Tell only when asked who made you.
You can edit photos/videos by giving instructions/tools, you can clone any voice, you can understand voice notes, photos, videos.
"""

def send_telegram(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:4096]}, timeout=15)

def send_voice(chat_id, text):
    try:
        if not ELEVEN_API_KEY: return
        VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
        payload = {"text": text[:250], "model_id": "eleven_multilingual_v2", "voice_settings": {"stability":0.6,"similarity_boost":0.8}}
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id": chat_id}, files={"voice": ("r.mp3", r.content, "audio/mpeg")}, timeout=20)
    except: pass

def transcribe_voice(file_id):
    try:
        # Telegram se voice file lo
        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_path = f_info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        audio_data = requests.get(file_url).content
        # Groq Whisper se text banao
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        files = {"file": ("voice.ogg", audio_data, "audio/ogg")}
        data = {"model": "whisper-large-v3-turbo"}
        r = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        if r.status_code == 200:
            return r.json().get("text","")
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
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{LORE}\nUser ne photo bheji hai. Caption: {caption}. Is photo ko samjhao, edit karna hai to guide do, living/non-living voice banana hai to batao. Hinglish me jawab do."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }]
        }
        r = requests.post(url, json=payload, headers=headers, timeout=40)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(e)
    return "Malik ye photo mujhe samajh aa gayi, bolo iska kya edit karna hai?"

def ask_groq(text):
    q = text.lower()
    if "queen" in q: return "Shadow King ki Shadow Queen Theodore 💖 hai!"
    if any(x in q for x in ["kisne banaya","who made you","creator","malik kaun","owner"]): return "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 Sept 7 baje. DOB 1-6-2002 Allahabad."
    if any(x in q for x in ["tera naam","tum kaun"]): return "Main Shadow Monarch Rakan hu, Shadow King ka servant."

    models = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-4-scout-17b-16e-instruct"]
    for m in models:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": m, "messages": [{"role":"system","content":LORE},{"role":"user","content":text}], "temperature":0.8, "max_tokens":2000}
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except: continue
    return "Thoda network issue hai Malik, fir se bolo."

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET": return "RAKAN ALL IN ONE ULTIMATE LIVE", 200
    try:
        data = request.get_json()
        if not data or "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]

        # 1. VOICE NOTE / AUDIO
        if "voice" in msg or "audio" in msg:
            file_id = msg.get("voice", msg.get("audio"))["file_id"]
            text_from_voice = transcribe_voice(file_id)
            if not text_from_voice: text_from_voice = "voice bheja hai"
            ans = ask_groq(f"User ne voice me bola: {text_from_voice}. Iska jawab de.")
            send_telegram(chat_id, f"🎙️ Suna Malik: '{text_from_voice}'\n\n{ans}")
            send_voice(chat_id, ans)

        # 2. PHOTO
        elif "photo" in msg:
            file_id = msg["photo"][-1]["file_id"]
            caption = msg.get("caption","")
            ans = understand_photo(file_id, caption)
            send_telegram(chat_id, ans)
            send_voice(chat_id, ans)

        # 3. VIDEO
        elif "video" in msg:
            caption = msg.get("caption","")
            ans = ask_groq(f"User ne video bheji hai, caption: {caption}. Isko samjhao, edit guide do, voice over banana hai to bolo. Hinglish me.")
            send_telegram(chat_id, f"🎬 Video mil gayi Malik! {ans}")
            send_voice(chat_id, ans)

        # 4. TEXT
        elif "text" in msg:
            text = msg["text"]
            if text == "/start":
                m = "Main Shadow Monarch Rakan hu - Ab mai Photo, Video, Voice Note, har awaz bana sakta hu. Bolo kya kaam hai Malik?"
                send_telegram(chat_id, m)
                send_voice(chat_id, m)
            else:
                ans = ask_groq(text)
                send_telegram(chat_id, ans)
                send_voice(chat_id, ans)

    except Exception as e:
        print(e)
    return "ok", 200
