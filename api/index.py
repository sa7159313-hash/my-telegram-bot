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

client = genai.Client(api_key=GEMINI_API_KEY)

# YE 4 MODELS 100% WORKING HAIN - 1.5 WALA HATA DIYA
MODELS = ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash"]

def send_text(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    except: pass

def send_voice(chat_id, text):
    try:
        if not ELEVENLABS_API_KEY:
            send_text(chat_id, text); return
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_multilingual_v2"}, timeout=15)
        if r.status_code == 200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id": chat_id}, files={"voice": ("v.mp3", r.content, "audio/mpeg")}, timeout=10)
        else:
            send_text(chat_id, text)
    except:
        send_text(chat_id, text)

def get_reply(user_text):
    prompt = f"You are Rakan, loyal servant of Shadow Monarch. Reply in Hinglish, royal, loyal, short 2 lines max. User: {user_text}"
    for model in MODELS:
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=200)
            )
            if resp.text:
                return resp.text
        except Exception as e:
            print(f"{model} failed: {e}")
            continue
    return "Ji Malik, hazir hoon! Thoda network busy hai, fir se boliye."

@app.route("/", methods=["GET"])
def home(): return "Rakan Alive v2.5 - Fixed", 200

@app.route("/api/index", methods=["GET", "POST"])
def webhook():
    if request.method == "GET": return "ok", 200
    data = request.json
    if not data or "message" not in data: return "ok", 200
    
    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")
    if not text:
        text = "hello"

    reply = get_reply(text)
    low = text.lower()
    if any(x in low for x in ["voice", "bol", "awaz", "bolo", "suna"]):
        send_voice(chat_id, reply)
    else:
        send_text(chat_id, reply)
    
    return "ok", 200
