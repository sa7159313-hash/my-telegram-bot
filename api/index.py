from flask import Flask, request
import os, requests

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

def send_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text[:4000]}, timeout=15)

def ask_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    r = requests.post(url, json=payload, timeout=20)
    data = r.json()
    if "candidates" in data:
        return data['candidates'][0]['content']['parts'][0]['text']
    else:
        return f"Gemini Error: {data}"

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "KING Bot is Live 👑", 200
    data = request.get_json(force=True, silent=True)
    if not data or "message" not in data:
        return "ok", 200

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")
    if not text: return "ok", 200

    if text == "/start":
        send_msg(chat_id, "Hey KING 👑 Mai live hu! Bolo kya chahiye?")
        return "ok", 200

    ai_reply = ask_gemini(text)
    send_msg(chat_id, ai_reply)
    return "ok", 200
