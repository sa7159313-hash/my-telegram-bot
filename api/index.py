from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Vercel me daalenge
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

@app.route('/')
def home():
    return "KING Bot is 100% LIVE! 👑"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        
        if text == "/start":
            reply = "Hello KING 👑 Bot LIVE hai! Bol kya kaam hai?"
        else:
            reply = f"Tune bola: {text}"

        requests.post(f"{BOT_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": reply
        })
    return "ok"

@app.route('/<path:path>')
def catch_all(path):
    return "KING Bot is 100% LIVE! 👑"