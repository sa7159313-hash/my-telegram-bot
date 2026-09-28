import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Telegram pe message bhejne ka function
def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text[:4000]}, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

# Gemini se jawab lene ka function - 3 model try karega
def ask_gemini(prompt):
    models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-flash-latest"]

    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            res = requests.post(url, json=payload, timeout=15)
            data = res.json()

            if "candidates" in data:
                return data['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"Model {model_name} failed: {data}")
                continue # next model try karo
        except Exception as e:
            print(f"Error with {model_name}: {e}")
            continue

    return "Bhai thoda busy hu, 1 min baad try kar 😅"

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return "KING BOT FINAL LIVE!", 200

    json_data = request.get_json()
    if not json_data:
        return "ok", 200

    print("DATA:", json_data)

    if "message" in json_data and "text" in json_data["message"]:
        chat_id = json_data["message"]["chat"]["id"]
        user_text = json_data["message"]["text"]

        if user_text == "/start":
            send_telegram(chat_id, "Huu KING! 👑 Final Bot Live hai! Bolo kya chahiye?")
        else:
            reply = ask_gemini(user_text)
            send_telegram(chat_id, reply)

    return "ok", 200
