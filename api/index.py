import os
import requests
from flask import Flask, request
from google import genai
from google.genai import types

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

# YEH HAI ASLI FIX - v1 API FORCE
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(api_version='v1')
)

MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash", 
    "gemini-2.5-flash-lite",
    "gemini-1.5-flash"
]

def send_text(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text})

def send_voice(chat_id, text):
    try:
        if not ELEVENLABS_API_KEY:
            send_text(chat_id, text); return
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={"xi-api-key": ELEVENLABS_API_KEY}, json={"text": text, "model_id": "eleven_multilingual_v2"}, timeout=15)
        if r.status_code == 200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id": chat_id}, files={"voice": ("v.mp3", r.content)}, timeout=15)
        else: send_text(chat_id, text)
    except: send_text(chat_id, text)

def get_reply(user_text):
    prompt = f"You are Rakan, Shadow Monarch's loyal servant. Hinglish royal short reply: {user_text}"
    for m in MODELS:
        try:
            res = client.models.generate_content(model=m, contents=prompt)
            if res.text: return res.text
        except Exception as e:
            print(f"FAIL {m}: {e}")
            continue
    return "Ji Malik, hazir hoon! Thoda network busy hai, fir se boliye."

@app.route("/", methods=["GET"])
def home(): return "Rakan v1 Fixed", 200

@app.route("/api/index", methods=["GET", "POST"])
def webhook():
    if request.method == "GET": return "ok", 200
    data = request.json
    if not data or "message" not in data: return "ok", 200
    chat_id = data["message"]["chat"]["id"]
    txt = data["message"].get("text", "hello")
    reply = get_reply(txt)
    low = txt.lower()
    if any(x in low for x in ["voice","bol","awaz","bolo"]): send_voice(chat_id, reply)
    else: send_text(chat_id, reply)
    return "ok", 200
