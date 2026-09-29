import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def send_text(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)

def get_ai_reply(user_text):
    prompt = f"You are Rakan, loyal servant of Shadow Monarch, reply in Hinglish royal short: {user_text}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    models = ["gemini-2.5-flash", "gemini-3.8-flash", "gemini-flash-latest", "gemini-2.5-pro"]
    last_err = ""
    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            r = requests.post(url, json=payload, timeout=15)
            print(f"Trying {model}: {r.status_code}")
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            last_err = f"{model} {r.status_code}: {r.text[:500]}"
        except Exception as e:
            last_err = str(e)
            continue
    return f"Ji Malik, error aa raha hai: {last_err[:700]}"

@app.route("/", methods=["GET"])
def home():
    return "Rakan 3.8 Fixed Running", 200

@app.route("/api/index", methods=["POST", "GET"])
def webhook():
    if request.method == "GET":
        return "ok", 200
    data = request.json
    if not data or "message" not in data:
        return "ok", 200
    chat_id = data["message"]["chat"]["id"]
    txt = data["message"].get("text", "hi")
    reply = get_ai_reply(txt)
    send_text(chat_id, reply)
    return "ok", 200
