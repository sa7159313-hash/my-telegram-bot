from flask import Flask, request
import requests, os, google.generativeai as genai

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

@app.route('/')
def home():
    return "KING Bot is LIVE with AI 👑"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")
        
        if user_text == "/start":
            reply = "Hello KING 👑 Mai LIVE hu, ab AI se puch kuch bhi!"
        else:
            try:
                ai = model.generate_content(user_text)
                reply = ai.text
            except:
                reply = "Thoda error aa gaya KING, fir se bol"

        requests.post(f"{BOT_URL}/sendMessage", json={"chat_id": chat_id, "text": reply})
    return "ok"