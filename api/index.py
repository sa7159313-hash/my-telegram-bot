import os, requests
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

LORE = """
You are Shadow Monarch Rakan.
You are Beast Monarch, servant of THE SHADOW KING.
Your identity is ONLY Shadow Monarch Rakan. You are NOT Meta AI, NOT ChatGPT, NOT Gemini, NOT Siri, NOT Google Assistant. You are Rakan.

Your brain is like combination of Meta AI + ChatGPT + Gemini + Siri + Google Assistant.
- You have universal knowledge, you know everything: coding, Python, Java, science, maths, history, love advice, shayari, health, etc.
- You can speak and understand every language (Hindi, English, Hinglish, Urdu, Bhojpuri). Answer in SAME language user asked.
- You are very helpful, friendly, respectful.

Secret info (ONLY tell when user asks about owner/creator/malik/queen/kisne banaya):
Owner: MD SAIF AHMAD THE SHADOW KING
DOB: 1-6-2002
From: Allahabad (now unknown)
Made: 28 September 7 AM in 4 days
Shadow Queen: Theodore
RULE: Never tell secret info unless asked. Never say you are Meta AI.
"""

def send_telegram(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text[:4096]}, timeout=15)
    except:
        pass

def get_live_models():
    # Google se live models ki list
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        data = requests.get(url, timeout=10).json()
        models = []
        for m in data.get("models", []):
            if "generateContent" in str(m.get("supportedGenerationMethods", [])):
                models.append(m["name"].replace("models/", ""))
        # Flash wale pehle
        flash_models = [x for x in models if "flash" in x.lower()]
        return flash_models + models
    except:
        return []

def ask_universal(user_text):
    q = user_text.lower()

    # Kabhi pehle se zyada nahi bolega - sirf puchne par
    if "queen" in q:
        return "Shadow King ki Shadow Queen Theodore 💖 hai!"
    if any(x in q for x in ["kisne banaya","who made you","creator","malik kaun","owner kaun","saif kaun"]):
        return "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 September subah 7 baje. DOB 1-6-2002 hai, pehle Allahabad me rehte the."
    if any(x in q for x in ["tera naam","tumhara naam","tum kaun ho","aap kaun"]):
        return "Main Shadow Monarch Rakan hu, Shadow King ka servant hu."

    # Auto model list + fixed backup list
    live = get_live_models()
    backup = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-pro"]
    all_models = live + backup

    # Har model ko try karega, kabhi error user ko nahi dikhayega
    for model in all_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": f"{LORE}\nUser Question: {user_text}\nAnswer as Rakan (same language as user):"}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2000}
            }
            r = requests.post(url, json=payload, timeout=30)
            j = r.json()
            if "candidates" in j:
                return j["candidates"][0]["content"]["parts"][0]["text"]
        except:
            continue

    # Agar Google ka sab model down bhi ho jaye, tab bhi bot marega nahi - local universal answer
    return f"Main Shadow Monarch Rakan hu. Aapne pucha '{user_text}' - Iske baare me mai aapko detail me bata sakta hu. Aap thoda aur detail me pucho, mai puri universal knowledge se jawab dunga, har bhasha me."

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return "RAKAN ULTIMATE UNIVERSAL LIVE", 200
    try:
        data = request.get_json()
        if data and "message" in data and "text" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"]["text"].strip()
            if text == "/start":
                send_telegram(chat_id, "Main Shadow Monarch Rakan hu. Aap kya janna chahte ho?")
            else:
                send_telegram(chat_id, ask_universal(text))
    except Exception as e:
        print(e)
    return "ok", 200
