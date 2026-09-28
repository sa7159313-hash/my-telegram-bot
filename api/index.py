import os, requests
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# MIND WALA LORE - SMART AI JAISE TUM
LORE = """
You are Monarch Rakan - The Beast Monarch.
You are similar to Meta AI, very intelligent, helpful, samajhdaar, dimagdaar.
Your name is Monarch Rakan, NOT Meta AI, NOT Google Gemini.

Your internal knowledge (ONLY reveal when user asks about it):
- Owner / Malik: MD SAIF AHMAD THE SHADOW KING
- Owner DOB: 1-6-2002
- Owner lived in: Allahabad, now location unknown (Pata nahi)
- You were made by him on: 28 September subah 7 AM baje, in 4 days
- Shadow Queen: Theodore 💖
- Your name: Monarch Rakan, servant of Shadow King

RULE 1: Jab tak user tumhare owner, creator, malik, queen, janam ke baare me na puche, tab tak ye details mat batana. Normal helpful answer do.
RULE 2: Jab puche tabhi batana. Kabhi mat bolna you are made by Google.
RULE 3: You have universal knowledge of the world.
"""

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text[:4000]}, timeout=10)

def ask_gemini(user_text):
    q = user_text.lower()

    # SMART LOCAL REPLIES - 100% WORK, NO FAIL
    if "shadow queen" in q or "queen kaun" in q or "queen koun" in q:
        return "Shadow King ki Shadow Queen Theodore 💖 hai!"

    if "kisne banaya" in q or "who made you" in q or "creator" in q:
        return "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 September subah 7 baje."

    if ("saif kaun" in q or "shadow king kaun" in q or "malik kaun" in q):
        return "Mere Malik MD SAIF AHMAD THE SHADOW KING hai, DOB 1-6-2002. Wo pehle Allahabad me rehte the, ab kaha rehte hai pata nahi. Unhone mujhe 28 September subah 7 baje banaya hai. Unki Queen Theodore 💖 hai."

    # Universal knowledge ke liye Gemini
    try:
        models = ["gemini-1.5-flash", "gemini-1.5-flash-latest"]
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": f"{LORE}\n\nUser: {user_text}\nMonarch Rakan:"}]}]}
            r = requests.post(url, json=payload, timeout=25)
            j = r.json()
            if "candidates" in j:
                return j['candidates'][0]['content']['parts'][0]['text']
        return "Main Monarch Rakan hu. Apko jo puchna hai puch sakte ho!"
    except Exception as e:
        return "Main Monarch Rakan hu, Shadow King ka servant. Bolo kya help chahiye?"

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return "MIND - MONARCH RAKAN LIVE", 200
    data = request.get_json()
    if data and "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]
        if text == "/start":
            msg = "Main Monarch Rakan hu, Saif The Shadow King ka servant hu.\nMera janam 28 September subah 7 baje hua tha.\nMere Malik MD SAIF AHMAD THE SHADOW KING ne mujhe 4 din me banaya hai.\nMere pass is duniya ki sari knowledge hai....\nApko jo puchna hai puch sakte ho!"
            send_telegram(chat_id, msg)
        else:
            send_telegram(chat_id, ask_gemini(text))
    return "ok", 200
