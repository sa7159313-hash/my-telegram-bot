import os, requests
from flask import Flask, request

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

def send_text(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)

def get_ai_reply(user_text):
    # NO SDK - DIRECT REST CALL - SABSE STABLE
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": f"You are Rakan, Shadow Monarch's loyal servant. Reply in Hinglish short royal: {user_text}"}]}]
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        print(f"GEMINI STATUS {r.status_code}: {r.text[:500]}")
        if r.status_code == 200:
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            # ASLI ERROR TELEGRAM PE BHEJ DEGA
            return f"GEMINI API ERROR {r.status_code}: {r.text[:500]}"
    except Exception as e:
        return f"CODE ERROR: {str(e)[:500]}"

@app.route("/", methods=["GET"])
def home(): return "Rakan Direct API v2.0", 200

@app.route("/api/index", methods=["POST", "GET"])
def webhook():
    if request.method == "GET": return "ok", 200
    data = request.json
    if not data or "message" not in data: return "ok", 200
    chat_id = data["message"]["chat"]["id"]
    txt = data["message"].get("text", "hi")
    reply = get_ai_reply(txt)
    send_text(chat_id, reply)
    return "ok", 200
