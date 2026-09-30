from flask import Flask, request
import os, requests

app = Flask(__name__)
application = app
handler = app

@app.route("/", methods=["GET"])
def home():
    return "Rakan Working 🔥", 200

@app.route("/api/index", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Rakan Working 🔥", 200
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data:
            return "ok", 200

        BOT = os.getenv("BOT_TOKEN","").strip()
        KEY = os.getenv("GEMINI_API_KEY","").strip()

        msg = data["message"]
        chat_id = str(msg["chat"]["id"])
        text = msg.get("text","") or ""

        # Direct Gemini
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={KEY}"
            payload = {"contents":[{"parts":[{"text": f"You are Rakan, Beast King, say Ji Malik, short Hinglish king attitude. User: {text}"}]}]}
            r = requests.post(url, json=payload, timeout=20)
            print(f"GEMINI {r.status_code}")
            if r.status_code == 200:
                reply = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                reply = "Ji Malik, Rakan hazir hai, hukam karo 🔥"
        except Exception as e:
            print(f"ERR {e}")
            reply = "Ji Malik, Rakan hazir hai, hukam karo 🔥"

        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", json={"chat_id":chat_id,"text":reply[:4000]}, timeout=15)
        return "ok", 200
    except Exception as e:
        print(f"CRASH {e}")
        return "ok", 200
