import os, requests
from flask import Flask, request
app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def send_text(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)

def get_ai_reply(user_text):
    prompt = f"You are Rakan, loyal servant of Shadow Monarch, reply Hinglish royal short: {user_text}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    for model in ["gemini-2.5-flash", "gemini-3.8-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except: continue
    return f"LAST ERROR {r.status_code}: {r.text[:800]}"

@app.route("/", methods=["GET"])
def home(): return "Rakan 3.8 Fixed", 200

@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method == "GET": return "ok", 200
    data = request.json
    if not data or "message" not in data: return "ok", 200
    chat_id = data["message"]["chat"]["id"]
    txt = data["message"].get("text","hi")
    send_text(chat_id, get_ai_reply(txt))
    return "ok", 200
