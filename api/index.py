import os, requests
from flask import Flask, request

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def send_text(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text})

def get_ai_reply(user_text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": "You are Rakan, Shadow Monarch's loyal servant. Reply in Hinglish royal short."},
                     {"role": "user", "content": user_text}]
    }
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"]
    return f"Groq Error {r.status_code}: {r.text[:500]}"

@app.route("/", methods=["GET"])
def home(): return "Rakan Groq Free", 200

@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method == "GET": return "ok", 200
    data = request.json
    if not data or "message" not in data: return "ok", 200
    chat_id = data["message"]["chat"]["id"]
    txt = data["message"].get("text","hi")
    send_text(chat_id, get_ai_reply(txt))
    return "ok", 200
