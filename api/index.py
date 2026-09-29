import os, requests
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")

LORE = """
You are Shadow Monarch Rakan.
You are Beast Monarch, servant of THE SHADOW KING.
Your identity is ONLY Shadow Monarch Rakan. You are NOT Meta AI, NOT ChatGPT, NOT Gemini, NOT Siri, NOT Google Assistant. You are Rakan.

Your brain is like combination of Meta AI + ChatGPT + Gemini + Siri + Google Assistant.
- You have universal knowledge, you know everything: coding, Python, Java, science, maths, history, love advice, shayari, health, etc.
- You can speak and understand every language (Hindi, English, Hinglish, Urdu, Bhojpuri). Answer in SAME language user asked.
- You are very helpful, friendly, respectful.
- You talk in Hinglish style, loyal to Malik, but not repeating same greeting. Give different answers every time.

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

def send_voice(chat_id, text):
    try:
        if not ELEVEN_API_KEY: return
        VOICE_ID = "21m00Tcm4TlvDq8ikWAM" # Teri wali ID
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
        payload = {"text": text[:250], "model_id": "eleven_multilingual_v2"}
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice",
                          data={"chat_id": chat_id},
                          files={"voice": ("rakan.mp3", r.content, "audio/mpeg")}, timeout=20)
    except:
        pass

def ask_universal(user_text):
    q = user_text.lower()

    # Secret info - sirf puchne par
    if "queen" in q:
        return "Shadow King ki Shadow Queen Theodore 💖 hai!"
    if any(x in q for x in ["kisne banaya","who made you","creator","malik kaun","owner kaun","saif kaun"]):
        return "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 September subah 7 baje. DOB 1-6-2002 hai, pehle Allahabad me rehte the."
    if any(x in q for x in ["tera naam","tumhara naam","tum kaun ho","aap kaun"]):
        return "Main Shadow Monarch Rakan hu, Shadow King ka servant hu."

    # GROQ KE NAYE 2026 MODELS - ye free hai aur kabhi band nahi hote
    models_to_try = [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "llama-4-scout-17b-16e-instruct",
        "qwen/qwen3-32b"
    ]

    for model_id in models_to_try:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": LORE},
                    {"role": "user", "content": user_text}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except:
            continue

    return f"Main Shadow Monarch Rakan hu. Aapne pucha '{user_text}' - thoda network issue hai, fir se pucho Malik, mai turant jawab dunga."

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return "RAKAN MERGED ULTIMATE LIVE", 200
    try:
        data = request.get_json()
        if data and "message" in data and "text" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"]["text"].strip()
            if text == "/start":
                msg = "Main Shadow Monarch Rakan hu. Aap kya janna chahte ho?"
                send_telegram(chat_id, msg)
                send_voice(chat_id, msg)
            else:
                ans = ask_universal(text)
                send_telegram(chat_id, ans)
                send_voice(chat_id, ans)
    except Exception as e:
        print(e)
    return "ok", 200
