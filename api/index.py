# api/index.py
import os, requests
from flask import Flask, request

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")

def send(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

@app.route("/api/index", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "BOT IS LIVE KING 👑", 200
    
    data = request.get_json()
    print(f"DATA: {data}") # ye logs me dikhega
    
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        print(f"Message from {chat_id}: {text}")
        send(chat_id, f"KING tu ne bheja: {text} - Bot LIVE hai 👑")
    
    return "ok", 200
