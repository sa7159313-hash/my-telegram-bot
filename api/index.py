from flask import Flask, request
import os
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

def send_msg(cid, txt):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": cid, "text": txt[:4000]})

def ask_gemini(q):
    if not GEMINI_KEY:
        return "GEMINI_API_KEY nahi hai!"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    r = requests.post(url, json={"contents": [{"parts": [{"text": q}]}]})
    try:
        return r.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return str(r.json())

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def main():
    if request.method == "GET":
        return "KING LIVE 👑", 200
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return "ok", 200
    cid = data["message"]["chat"]["id"]
    txt = data["message"].get("text","")
    if txt == "/start":
        send_msg(cid, "KING 👑 Bot ON hai!")
        return "ok", 200
    send_msg(cid, ask_gemini(txt))
    return "ok", 200