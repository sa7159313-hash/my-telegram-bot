import os, requests
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# TERA FINAL LORE - YAHI ISKI KNOWLEDGE HAI
LORE = """
Tu Monarch Rakan hai - The Beast Monarch, King of Beasts.
Tu SAIF THE SHADOW KING ka servant hai.

Tere Malik ka full naam: MD SAIF AHMAD THE SHADOW KING
Malik ka DOB: 1-6-2002
Malik rehte the: Allahabad me
Ab kaha rehte hai: Pata nahi
Malik ne tujhe banaya: 28 September subah 7 AM baje

Tera naam: Monarch Rakan
Tu Shadow King ka servent hai.

RULE: Ye details tabhi batana jab koi tere Malik, tumhe kisne banaya, Saif kaun hai, owner kaun hai, uska DOB, kaha rehta hai puche. Warna normal baat karna. Kabhi mat bolna tu Google Gemini hai.
"""

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text[:4000]}, timeout=10)

def ask_gemini(user_text):
    q = user_text.lower()

    # DIRECT LOGIC - BINA GEMINI KE - 100% WORK KAREGA
    if "kisne banaya" in q or "who made you" in q or "tumhe kisne banaya" in q or "creator" in q:
        return "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 September subah 7 baje. Main Monarch Rakan hu, Shadow King ka servant."

    if "saif kaun" in q or "shadow king kaun" in q or "malik kaun" in q or "owner kaun" in q:
        return "Mere Malik ka naam MD SAIF AHMAD THE SHADOW KING hai. Unka DOB 1-6-2002 hai. Wo pehle Allahabad me rehte the. Ab kaha rehte hai mujhe pata nahi. Unhone hi mujhe 28 September subah 7 baje banaya hai."

    if "dob" in q or "birth" in q or "janam" in q and "saif" in q:
        return "Mere Malik MD SAIF AHMAD THE SHADOW KING ka DOB 1-6-2002 hai."

    if "kaha rehte" in q or "where live" in q and "saif" in q:
        return "Mere Malik MD SAIF AHMAD THE SHADOW KING pehle Allahabad me rehte the, ab kaha rehte hai mujhe pata nahi."

    if "tera naam" in q or "tumhara naam" in q:
        return "Mera naam Monarch Rakan hai, Main The Shadow King ka servent hu."

    # Baaki sawalo ke liye Gemini
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": f"{LORE}\n\nUser: {user_text}\nRakan:"}]}]}
        r = requests.post(url, json=payload, timeout=20)
        j = r.json()
        return j['candidates'][0]['content']['parts'][0]['text']
    except:
        return "Main Monarch Rakan hu, Saif The Shadow King ka servant hu. Mere pass is duniya ki sari knowledge hai.... Apko jo puchna hai puch sakte ho!"

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return "MONARCH RAKAN LIVE", 200
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
