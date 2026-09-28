import os, requests
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

LORE = """
You are Shadow Monarch Rakan.
You are NOT Meta AI, NOT ChatGPT, NOT Gemini, NOT Google. Your name is ONLY Shadow Monarch Rakan, Beast Monarch, servant of Shadow King.
You have universal knowledge like Meta AI/ChatGPT.

Secret - ONLY tell when asked about creator/owner/queen:
- Owner: MD SAIF AHMAD THE SHADOW KING
- DOB: 1-6-2002
- From: Allahabad, now unknown
- Made: 28 September 7 AM in 4 days
- Queen: Theodore 💖
RULE: Don't tell secret info unless asked. Otherwise answer normally as helpful AI.
"""

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text[:4000]}, timeout=10)

def ask_gemini(user_text):
    q = user_text.lower()

    if "queen" in q:
        return "Shadow King ki Shadow Queen Theodore 💖 hai!"
    if any(x in q for x in ["kisne banaya","who made you","creator","malik kaun","saif kaun","owner","shadow king kaun"]):
        return "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 September subah 7 baje. DOB 1-6-2002, pehle Allahabad me rehte the."
    if "tera naam" in q or "tum kaun" in q:
        return "Main Shadow Monarch Rakan hu."

    # Try new models - 2.0-flash is working in 2026
    models_to_try = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-flash-latest", "gemini-1.5-flash-latest"]

    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": f"{LORE}\nUser: {user_text}\nRakan:"}]}]}
            r = requests.post(url, json=payload, timeout=25)
            j = r.json()
            print(f"TRY {model_name} -> {j}") # log me dikhega
            if "candidates" in j:
                return j["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"Model {model_name} failed: {e}")
            continue

    return "Main Shadow Monarch Rakan hu. Batao kya janna chahte ho? Mera Gemini abhi thoda busy hai."

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return "RAKAN 2.0 LIVE", 200
    data = request.get_json()
    if data and "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]
        if text == "/start":
            send_telegram(chat_id, "Main Shadow Monarch Rakan hu. Aap kya janna chahte ho?")
        else:
            send_telegram(chat_id, ask_gemini(text))
    return "ok", 200
