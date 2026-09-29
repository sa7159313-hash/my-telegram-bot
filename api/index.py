import os, requests
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "pFZP5ak9U38gs1IM1A3d"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def send_text(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text})

def send_voice(chat_id, text):
    if not ELEVENLABS_API_KEY:
        send_text(chat_id, text)
        return
    try:
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_multilingual_v2"})
        if r.status_code == 200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id": chat_id}, files={"voice": ("v.mp3", r.content, "audio/mpeg")})
        else:
            send_text(chat_id, text + f"\nVoice Error: {r.text}")
    except Exception as e:
        send_text(chat_id, text + f"\nError: {e}")

@app.route("/", methods=["GET"])
def home(): return "Rakan Alive"

@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method == "GET": return "ok"
    data = request.json
    if not data or "message" not in data: return "ok",200
    chat_id = data["message"]["chat"]["id"]
    text_raw = data["message"].get("text","")
    text = text_raw.lower()

    # Agar voice note bheja toh usko text samjho
    if "voice" in data["message"] or "audio" in data["message"]:
        send_text(chat_id, "Voice sun liya Malik! Ab jawab bhej raha hoon voice me...")
        text_raw = "voice me jawab do"
        text = text_raw

    if "voice" in text or "bol" in text or "bolo" in text or "awaz" in text:
        try:
            ai = model.generate_content(f"You are Rakan, loyal servant of Shadow Monarch. Reply short, royal Hinglish, friendly. User said: {text_raw}")
            reply = ai.text
        except:
            reply = "Ji Malik, hukum dijiye! Main hazir hoon."
        send_voice(chat_id, reply)
        return "ok",200

    try:
        ai = model.generate_content(f"You are Rakan, loyal servant. Reply in Hinglish royal style. User: {text_raw}")
        send_text(chat_id, ai.text)
    except Exception as e:
        send_text(chat_id, f"Error: {e}")
    return "ok",200
