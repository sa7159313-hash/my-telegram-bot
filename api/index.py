from flask import Flask, request
import os
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

def send_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text[:4000]}, timeout=10)
    except: pass

def ask_gemini(prompt):
    # Direct REST call - no google library needed
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(url, json=payload, timeout=15)
        data = r.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"Gemini Error: {e} | Raw: {r.text if 'r' in locals() else str(e)}"

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Bot is Running KING", 200

    data = request.get_json(force=True, silent=True)
    if not data or "message" not in data:
        return "ok", 200

    chat_id = data["message"]["chat"]["id"]
    user_text = data["message"].get("text", "")

    if not user_text:
        return "ok", 200
    if user_text == "/start":
        send_msg(chat_id, "Hey KING 👑 Bot ON hai! Bolo kya kaam hai?")
        return "ok", 200
    if not GEMINI_KEY:
        send_msg(chat_id, "GEMINI_API_KEY set nahi hai Vercel pe!")
        return "ok", 200

    reply = ask_gemini(user_text)
    send_msg(chat_id, reply)
    return "ok", 200
