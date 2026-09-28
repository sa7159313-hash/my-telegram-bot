import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # Telegram me bada text cut jata hai, isliye 4000 char limit
    requests.post(url, json={"chat_id": chat_id, "text": text[:4000]})

def ask_gemini(prompt):
    # Direct Google API call - koi library nahi chahiye
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    res = requests.post(url, json=data, timeout=20)
    result = res.json()
    try:
        return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print("GEMINI ERROR:", result)
        return f"Gemini Error: {result}"

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return "KING BOT LIVE - NO SDK!", 200

    data = request.get_json()
    print("DATA:", data)

    if data and "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]

        if user_text == "/start":
            send_telegram(chat_id, "Huu KING! 👑 Mai Gemini AI hu, bina SDK ke live hu!")
        else:
            reply = ask_gemini(user_text)
            send_telegram(chat_id, reply)

    return "ok", 200
