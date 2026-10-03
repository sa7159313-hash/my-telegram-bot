from flask import Flask, request
import os, requests

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def send(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id":chat_id, "text":text[:4000]}, timeout=15)
    except: pass

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        if "message" in data and "text" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            txt = data["message"]["text"]
            # Groq try
            reply = None
            if GROQ_KEY:
                try:
                    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                    json={"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":txt}]}, timeout=10)
                    if r.status_code==200:
                        reply = r.json()['choices'][0]['message']['content']
                except: pass
            if not reply:
                reply = "Haan Malik bolo, Rakan hazir hai 👑"
            send(chat_id, reply)
    except Exception as e:
        print(e)
    return "ok", 200

@app.route("/", methods=["GET"])
def home():
    return "BOT LIVE", 200
