import os, requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def send_telegram(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text[:4000]}, timeout=15)
    except Exception as e:
        print(f"TELE ERR: {e}")

def ask_groq(prompt):
    if not GROQ_API_KEY: return None
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "You are Rakan, King of Ashborn. You are smart, loyal to Malik."},
                {"role": "user", "content": prompt}
            ]
        }
        r = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"GROQ {r.status_code}")
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"GROQ FAIL: {e}")
    return None

def ask_gemini(prompt):
    if not GEMINI_API_KEY: return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
        print(f"GEMINI {r.status_code}")
        j = r.json()
        if "candidates" in j:
            return j["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"GEMINI FAIL: {e}")
    return None

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print(f"INCOMING: {data}")
        if "message" in data and "text" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"]["text"]
            print(f"MSG FROM {chat_id}: {text}")

            reply = ask_groq(text)
            if not reply:
                reply = ask_gemini(text)
            if not reply:
                reply = "Haan Malik bolo, thoda soch raha tha 👑"

            send_telegram(chat_id, reply)
    except Exception as e:
        print(f"WEBHOOK ERR: {e}")
    return "ok", 200

@app.route("/", methods=["GET"])
def home():
    return "BOT V50 LIVE - BOT_TOKEN READY", 200
