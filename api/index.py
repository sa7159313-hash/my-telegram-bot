import os
import requests
import google.generativeai as genai
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

@app.route("/api/index", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return "KING BOT IS LIVE!", 200
    
    data = request.json
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]
        
        if user_text == "/start":
            send_telegram(chat_id, "Huu KING! 👑 Mai Gemini AI hu, bolo kya help chahiye?")
        else:
            try:
                response = model.generate_content(user_text)
                send_telegram(chat_id, response.text)
            except Exception as e:
                send_telegram(chat_id, f"Error aa gaya KING: {str(e)}")
    
    return "ok", 200