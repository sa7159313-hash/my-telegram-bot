from flask import Flask, request
import os, requests

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

def send(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:4000]}, timeout=10)
    except: pass

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def main():
    if request.method == "GET":
        return "BOT LIVE - 404 FIXED", 200
    try:
        data = request.get_json(force=True)
        if "message" in data and "text" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            txt = data["message"]["text"]
            reply = None
            if GROQ_KEY:
                try:
                    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                    json={"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":txt}]}, timeout=10)
                    if r.status_code == 200:
                        reply = r.json()['choices'][0]['message']['content']
                except: pass
            if not reply:
                reply = f"Haan Malik, Rakan sun raha hai: {txt} 👑"
            send(chat_id, reply)
    except Exception as e:
        print(e)
    return "ok", 200
