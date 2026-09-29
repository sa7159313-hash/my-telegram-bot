import os
import requests
import time
from flask import Flask, request
from google import genai

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Fix voice ID
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

client = genai.Client(api_key=GEMINI_API_KEY)

# Models jinka quota sabse zyada hai - pehle wala fail hua to dusra chalega
MODELS_TO_TRY = [
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash-8b"
]

def send_text(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text})
    except:
        pass

def send_voice(chat_id, text):
    try:
        if not ELEVENLABS_API_KEY:
            send_text(chat_id, text)
            return
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        data = {"text": text, "model_id": "eleven_multilingual_v2"}
        r = requests.post(url, headers=headers, json=data, timeout=15)
        if r.status_code == 200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id": chat_id}, files={"voice": ("voice.mp3", r.content, "audio/mpeg")})
        else:
            send_text(chat_id, text)
    except:
        send_text(chat_id, text)

def get_ai_reply(prompt):
    last_error = ""
    for model_name in MODELS_TO_TRY:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = str(e)
            # Agar quota khatam hai to agle model pe jao, wait mat karo
            if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error or "quota" in last_error.lower():
                continue
            time.sleep(0.5)
            continue
    # Agar sab fail ho jaye
    return f"Ji Malik, abhi saare models ka quota full hai, 1 minute baad try kijiye. [{last_error[:100]}]"

@app.route("/", methods=["GET"])
def home():
    return "Rakan Alive - All Fixed"

@app.route("/api/index", methods=["POST", "GET"])
def webhook():
    if request.method == "GET":
        return "ok", 200
    
    data = request.json
    if not data or "message" not in data:
        return "ok", 200

    chat_id = data["message"]["chat"]["id"]
    msg = data["message"]
    text_raw = msg.get("text", "")

    if not text_raw:
        if "voice" in msg or "audio" in msg:
            text_raw = "voice me short jawab do"
        else:
            text_raw = "hello malik"

    lower = text_raw.lower()
    
    prompt = f"You are Rakan, loyal servant of Shadow Monarch. You talk in Hinglish, royal, loyal, short 1-2 lines. User said: {text_raw}"
    
    reply = get_ai_reply(prompt)

    if "voice" in lower or "bol" in lower or "awaz" in lower or "bolo" in lower:
        send_voice(chat_id, reply)
    else:
        send_text(chat_id, reply)

    return "ok", 200
