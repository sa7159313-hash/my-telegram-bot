import os
import requests
from flask import Flask, request

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")

def send_text(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=15)

def send_voice(chat_id, text):
    try:
        if not ELEVEN_API_KEY:
            return
        # Apni Voice ID yaha daal - jo purane code me thi
        VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
        payload = {"text": text, "model_id": "eleven_multilingual_v2"}
        r = requests.post(url, json=payload, headers=headers, timeout=25)
        if r.status_code == 200:
            # Telegram ko voice bhejo
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice",
                          data={"chat_id": chat_id},
                          files={"voice": ("rakan.mp3", r.content, "audio/mpeg")}, timeout=20)
    except:
        pass

def get_ai_reply(user_text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are Rakan, loyal servant of Shadow Monarch. Talk in royal Hinglish, short, powerful, respectful. Always call user Malik."},
            {"role": "user", "content": user_text}
        ]
    }
    r = requests.post(url, json=data, headers=headers, timeout=25)
    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"]
    return f"Ji Malik error: {r.text[:300]}"

@app.route("/", methods=["GET"])
def home(): return "Rakan Voice Live", 200

@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method == "GET": return "ok", 200
    data = request.json
    if not data or "message" not in data: return "ok", 200
    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text","hi")
    reply = get_ai_reply(text)
    send_text(chat_id, reply)
    send_voice(chat_id, reply) # Voice bhi bhejega
    return "ok", 200
