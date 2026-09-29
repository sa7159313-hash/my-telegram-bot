import os
import requests
from flask import Flask, request
from google import genai

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

client = genai.Client(api_key=GEMINI_API_KEY)

def send_text(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text})

def send_voice(chat_id, text):
    try:
        if not ELEVENLABS_API_KEY:
            send_text(chat_id, text)
            return
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        r = requests.post(url, headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}, json={"text": text, "model_id": "eleven_multilingual_v2"})
        if r.status_code == 200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id": chat_id}, files={"voice": ("v.mp3", r.content, "audio/mpeg")})
        else:
            send_text(chat_id, text)
    except:
        send_text(chat_id, text)

@app.route("/", methods=["GET"])
def home():
    return "Rakan Alive - 3.8"

@app.route("/api/index", methods=["POST", "GET"])
def webhook():
    if request.method == "GET":
        return "ok", 200
    data = request.json
    if not data or "message" not in data:
        return "ok", 200
    chat_id = data["message"]["chat"]["id"]
    text_raw = data["message"].get("text", "hello")
    if not text_raw and ("voice" in data["message"] or "audio" in data["message"]):
        text_raw = "voice me bolo"
    
    lower = text_raw.lower()

    try:
        prompt = f"You are Rakan, loyal servant of Shadow Monarch, reply in Hinglish royal style short. User: {text_raw}"
        # YAHI FIX HAI - ab 3.8-flash
        response = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
        reply = response.text
    except Exception as e:
        reply = f"Error fix: {e}"

    if "voice" in lower or "bol" in lower or "awaz" in lower:
        send_voice(chat_id, reply)
    else:
        send_text(chat_id, reply)
    
    return "ok", 200
