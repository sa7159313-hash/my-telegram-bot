from flask import Flask, request
import os
import requests

# YE TOP LEVEL PE HONA CHAHIYE - Vercel isi ko dhoondhta hai
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

def send_telegram(chat_id, text):
    if not BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": str(text)[:4000]}, timeout=10)
    except:
        pass

def ask_gemini(prompt):
    if not GEMINI_KEY:
        return "Bhai GEMINI_API_KEY Vercel pe add karna bhool gaya! Settings > Environment Variables me add kar de."

    # Direct API call - koi library nahi chahiye
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(url, json=payload, timeout=20)
        data = r.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"Gemini Error: {e} - Raw: {data if 'data' in locals() else 'No data'}"

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "KING Bot is Live 👑 - BOT_TOKEN and GEMINI_KEY set?", 200

    data = request.get_json(force=True, silent=True)
    if not data:
        return "ok", 200

    # Telegram se message nikalo
    message = data.get("message") or data.get("edited_message")
    if not message:
        return "ok", 200

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if not text:
        return "ok", 200

    if text == "/start":
        send_telegram(chat_id, "KING 👑 Mai Live Hu! Kuch bhi puch le - mai Gemini AI se jawab dunga.")
        return "ok", 200

    # AI se jawab lao
    reply = ask_gemini(text)
    send_telegram(chat_id, reply)
    return "ok", 200
