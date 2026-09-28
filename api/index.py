import os, requests
from flask import Flask, request
import traceback

app = Flask(__name__)

@app.route("/api/index", methods=["GET", "POST"])
@app.route("/webhook", methods=["GET", "POST"])  # dono route ek hi
def webhook():
    if request.method == "GET":
        return "BOT IS LIVE KING 👑", 200
    
    try:
        data = request.get_json(force=True)
        print(f"DATA: {data}")

        BOT_TOKEN = os.environ.get("BOT_TOKEN")
        print(f"TOKEN EXISTS: {bool(BOT_TOKEN)}")

        if not BOT_TOKEN:
            print("FATAL: BOT_TOKEN missing in Vercel Env!")
            return "no token", 200

        if data and "message" in data and "chat" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            print(f"Message from {chat_id}: {text}")

            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {"chat_id": chat_id, "text": f"KING LIVE HU! Tune bheja: {text} 👑"}
            r = requests.post(url, json=payload, timeout=10)
            print(f"TELEGRAM RESP: {r.status_code} {r.text}")
        else:
            print("No message field in data")

    except Exception as e:
        print(f"ERROR CRASH: {e}")
        traceback.print_exc()

    return "ok", 200
