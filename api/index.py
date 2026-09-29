import os
import requests
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Fix 1: Ye Voice ID 100% kaam karta hai, purana wala not_found de raha tha
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

genai.configure(api_key=GEMINI_API_KEY)
# Fix 2: gemini-1.5-flash ki jagah ye naya model, 404 error khatam
model = genai.GenerativeModel("gemini-1.5-flash-001")

def send_text(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def send_voice(chat_id, text):
    if not ELEVENLABS_API_KEY:
        send_text(chat_id, text)
        return
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        data = {"text": text, "model_id": "eleven_multilingual_v2"}
        r = requests.post(url, headers=headers, json=data)
        if r.status_code == 200:
            send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice"
            requests.post(send_url, data={"chat_id": chat_id}, files={"voice": ("voice.mp3", r.content, "audio/mpeg")})
        else:
            # Agar voice fail ho to text bhej dega taki bot chup na rahe
            send_text(chat_id, text)
    except Exception as e:
        send_text(chat_id, text)

@app.route("/", methods=["GET"])
def home():
    return "Rakan Alive"

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
        # Agar voice note bheja hai to
        if "voice" in msg or "audio" in msg:
            text_raw = "voice me chota jawab do, 1 line me"
        else:
            text_raw = "hello"
    
    lower_text = text_raw.lower()

    # Voice wala logic
    if "voice" in lower_text or "bol" in lower_text or "bolo" in lower_text or "awaz" in lower_text or "audio" in lower_text:
        try:
            prompt = f"You are Rakan, loyal servant of Shadow Monarch. Reply very short in Hinglish, royal style, 1-2 lines. User said: {text_raw}"
            response = model.generate_content(prompt)
            reply = response.text
        except:
            reply = "Ji Malik, hukam dijiye! Main hazir hoon."
        send_voice(chat_id, reply)
        return "ok", 200

    # Normal text wala logic
    try:
        prompt = f"You are Rakan, loyal servant of Shadow Monarch. Reply in Hinglish, royal friendly style. User: {text_raw}"
        response = model.generate_content(prompt)
        send_text(chat_id, response.text)
    except Exception as e:
        send_text(chat_id, f"Error: {e}")

    return "ok", 200
