import os
import requests
from flask import Flask, request
from google import genai

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return "KING BOT IS LIVE WITH NEW GENAI!", 200
    
    data = request.get_json()
    print("DATA:", data) # ye log me dikhega
    
    if data and "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]
        
        if user_text == "/start":
            send_telegram(chat_id, "Huu KING! 👑 Mai naya Gemini AI hu, bolo kya kaam hai?")
        else:
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=user_text
                )
                send_telegram(chat_id, response.text)
            except Exception as e:
                print(f"ERROR: {e}")
                send_telegram(chat_id, f"Error: {str(e)}")

    return "ok", 200
