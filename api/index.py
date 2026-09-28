import os, requests
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

LORE = """
You are Shadow Monarch Rakan.
You are NOT Meta AI, NOT ChatGPT, NOT Gemini, NOT Google. Your name is ONLY Shadow Monarch Rakan, servant of Shadow King.
You behave like Meta AI/ChatGPT - helpful, universal knowledge.
Secret (ONLY tell when asked about creator/owner/queen):
Owner: MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002, From Allahabad (now unknown), Made 28 Sept 7 AM, Queen: Theodore 💖
"""

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text[:4000]}, timeout=10)

def ask_gemini(user_text):
    q = user_text.lower()
    if "queen" in q:
        return "Shadow King ki Shadow Queen Theodore 💖 hai!"
    if any(x in q for x in ["kisne banaya","who made you","malik kaun","saif kaun","owner","shadow king kaun"]):
        return "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 September subah 7 baje. DOB 1-6-2002, pehle Allahabad me rehte the."
    if "tera naam" in q or "tum kaun" in q:
        return "Main Shadow Monarch Rakan hu."

    # NEW MODEL - 3.8-flash
    try:
        model = "gemini-3.8-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": f"{LORE}\nUser: {user_text}\nRakan:"}]}]}
        r = requests.post(url, json=payload, timeout=30)
        j = r.json()
        print(f"3.8 RESPONSE: {j}")
        if "candidates" in j:
            return j["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return f"Gemini Error: {j}"
    except Exception as e:
        return f"Error: {e}"

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return "RAKAN 3.8 LIVE", 200
    data = request.get_json()
    if data and "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]
        if text == "/start":
            send_telegram(chat_id, "Main Shadow Monarch Rakan hu. Aap kya janna chahte ho?")
        else:
            send_telegram(chat_id, ask_gemini(text))
    return "ok", 200
