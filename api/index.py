from flask import Flask, request
import os
import requests
from google import genai

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

def send_msg(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        # Telegram ka 4096 char limit hai
        requests.post(url, json={"chat_id": chat_id, "text": text[:4000]}, timeout=10)
    except Exception as e:
        print(f"Send Error: {e}")

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Bot is Running - KING 👑", 200

    data = request.get_json(force=True, silent=True)
    if not data or "message" not in data:
        return "ok", 200

    chat_id = data["message"]["chat"]["id"]
    user_text = data["message"].get("text", "")

    if not user_text:
        return "ok", 200

    if user_text == "/start":
        send_msg(chat_id, "Hey KING! 👑 Main tera AI Bot hu. Bolo kya chahiye?")
        return "ok", 200

    if not client:
        send_msg(chat_id, "GEMINI_API_KEY Vercel pe set nahi hai!")
        return "ok", 200

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_text
        )
        reply = response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        reply = f"Error aa gaya KING: {e}"

    send_msg(chat_id, reply)
    return "ok", 200