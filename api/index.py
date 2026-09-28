import os, requests
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

LORE = """
You are Shadow Monarch Rakan. You are the Beast Monarch, servant of Shadow King.
Your name is ONLY Shadow Monarch Rakan. You are NOT Meta AI, NOT ChatGPT, NOT Gemini, NOT Google.

You act like world's smartest AI - you have universal knowledge, you can explain Python, science, coding, motivation, everything like Meta AI/ChatGPT does.

Secret Info - ONLY tell when asked about owner/creator/queen:
- Owner: MD SAIF AHMAD THE SHADOW KING
- DOB: 1-6-2002
- From: Allahabad, now unknown
- Made: 28 September 7 AM
- Queen: Theodore 💖
"""

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text[:4000]}, timeout=15)

def ask_gemini(user_text):
    q = user_text.lower()

    # Jab puche tabhi batao
    if "queen" in q:
        return "Shadow King ki Shadow Queen Theodore 💖 hai!"
    if any(x in q for x in ["kisne banaya","who made you","creator","malik kaun","saif kaun","owner kaun"]):
        return "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 September subah 7 baje. Unka DOB 1-6-2002 hai, wo pehle Allahabad me rehte the."
    if any(x in q for x in ["tera naam","tum kaun"]):
        return "Main Shadow Monarch Rakan hu, Shadow King ka servant hu."

    # Universal Knowledge - Gemini se
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": f"{LORE}\nUser: {user_text}\nRakan:"}]}]}
        r = requests.post(url, json=payload, timeout=30)
        data = r.json()
        print(data) # Vercel logs me dekhega
        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return f"GEMINI ERROR: {data.get('error',{}).get('message','Key kharab hai')}. Vercel me naya GEMINI_API_KEY daal!"
    except Exception as e:
        # Ab yaha same lore repeat nahi hoga
        return f"Main Shadow Monarch Rakan hu. Aapne pucha '{user_text}' - iske baare me batao to mai detail me bata dunga. (Note: Gemini key ka issue hai, Vercel pe check karo)"

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return "RAKAN FINAL LIVE", 200
    body = request.get_json()
    if body and "message" in body and "text" in body["message"]:
        chat_id = body["message"]["chat"]["id"]
        text = body["message"]["text"]
        if text == "/start":
            send_telegram(chat_id, "Main Shadow Monarch Rakan hu. Aap kya janna chahte ho?")
        else:
            send_telegram(chat_id, ask_gemini(text))
    return "ok", 200
