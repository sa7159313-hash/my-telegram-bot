import os, requests
from flask import Flask, request
app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")

def send_text(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=15)

def send_voice(chat_id, text):
    try:
        if not ELEVEN_API_KEY: return
        VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
        payload = {"text": text, "model_id": "eleven_multilingual_v2"}
        r = requests.post(url, json=payload, headers=headers, timeout=25)
        if r.status_code == 200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id": chat_id}, files={"voice": ("r.mp3", r.content, "audio/mpeg")}, timeout=20)
    except: pass

def get_ai_reply(user_text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "openai/gpt-oss-20b", # <--- YE NAYA MODEL HAI
        "messages": [
            {"role": "system", "content": "You are Rakan, loyal servant of Shadow Monarch. Talk in royal Hinglish, short, powerful, respectful. Call user Malik."},
            {"role": "user", "content": user_text}
        ]
    }
    r = requests.post(url, json=data, headers=headers, timeout=25)
    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"]
    return f"Error {r.status_code}: {r.text[:300]}"

@app.route("/", methods=["GET"])
def home(): return "Rakan Live", 200
@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method == "GET": return "ok", 200
    d = request.json
    if not d or "message" not in d: return "ok", 200
    cid = d["message"]["chat"]["id"]
    txt = d["message"].get("text","hi")
    rep = get_ai_reply(txt)
    send_text(cid, rep)
    send_voice(cid, rep)
    return "ok", 200
