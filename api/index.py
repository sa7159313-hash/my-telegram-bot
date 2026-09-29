import os
import requests
from flask import Flask, request

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def send_text(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
    except:
        pass

def get_ai_reply(user_text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are Rakan, loyal servant of Shadow Monarch. Talk in royal Hinglish, short, powerful, respectful. Always call user 'Malik'."},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.7
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=25)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            return f"Ji Malik, error {r.status_code}: {r.text[:400]}"
    except Exception as e:
        return f"Ji Malik, network error: {str(e)[:400]}"

@app.route("/", methods=["GET"])
def home():
    return "Rakan 70B Free Live", 200

@app.route("/api/index", methods=["POST", "GET"])
def webhook():
    if request.method == "GET":
        return "ok", 200
    data = request.json
    if not data or "message" not in data:
        return "ok", 200
    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "hi")
    reply = get_ai_reply(text)
    send_text(chat_id, reply)
    return "ok", 200
