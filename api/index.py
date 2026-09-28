import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text[:4000]}, timeout=10)
    except Exception as e:
        print(f"Error: {e}")

def ask_gemini(user_text):
    lore = """
    Tera naam Monarch Rakan hai - The Beast Monarch, King of Beasts from Solo Leveling.
    Tu SAIF - THE SHADOW KING (Shadow Monarch) ka wafadar servant hai.
    Tera janam 28 September subah 7 baje hua tha.
    Shadow King ne tujhe 4 din me banaya hai.
    Tere pass is duniya ki sari knowledge hai.
    Tu hamesha bolega: apko jo puchna hai puch sakte ho.
    Kabhi mat bolna tu Google Gemini, Meta AI, ChatGPT hai.
    Hamesha bolna Main Monarch Rakan hu, Saif The Shadow King ka servant.
    """

    final_prompt = f"{lore}\n\nUser: {user_text}\nMonarch Rakan:"

    for model in ["gemini-1.5-flash", "gemini-2.5-flash"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": final_prompt}]}]}
            r = requests.post(url, json=payload, timeout=20)
            data = r.json()
            if "candidates" in data:
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except:
            continue

    return "Shadow Realm me thoda andhera hai, 1 min baad pucho!"

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return "MONARCH RAKAN LIVE", 200

    data = request.get_json()
    if not data:
        return "ok", 200

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]

        if text == "/start":
            msg = (
                "Main Monarch Rakan hu, Saif The Shadow King ka servant hu.\n"
                "Mera janam 28 September subah 7 baje hua tha.\n"
                "Shadow King ne mujhe 4 din me banaya hai.\n"
                "Mere pass is duniya ki sari knowledge hai....\n"
                "Apko jo puchna hai puch sakte ho!"
            )
            send_telegram(chat_id, msg)
        else:
            reply = ask_gemini(text)
            send_telegram(chat_id, reply)

    return "ok", 200
