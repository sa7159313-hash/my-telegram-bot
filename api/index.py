from flask import Flask, request
import os
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

def send_msg(cid, txt):
    if not BOT_TOKEN:
        print("BOT_TOKEN missing!")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": cid, "text": str(txt)[:4000]})

def ask_gemini(q):
    if not GEMINI_KEY:
        return "Bhai GEMINI_API_KEY Vercel me add karna bhul gaya tu"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    r = requests.post(url, json={"contents": [{"parts": [{"text": q}]}]}, timeout=25)
    try:
        return r.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return f"Gemini Error: {r.text[:500]}"

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
@app.route("/webhook", methods=["GET","POST"])
def main():
    if request.method == "GET":
        return "KING LIVE 👑", 200
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return "ok", 200
    cid = data["message"]["chat"]["id"]
    text = data["message"].get("text","")
    if text == "/start":
        send_msg(cid, "KING 👑 Bot ON hai! Ab kuch bhi puch")
    else:
        send_msg(cid, ask_gemini(text))
    return "ok", 200
