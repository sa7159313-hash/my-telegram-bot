from flask import Flask, request, jsonify
import os
from groq import Groq
from openai import OpenAI
from google import genai

app = Flask(__name__)

# Teri Keys - Vercel se utha raha hai, tune jo naam rakha hai wahi
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
OPEN_KEY = os.getenv("OPEN_API_KEY") # Tu OPEN_API_KEY likha hai, wahi liya
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

client_groq = Groq(api_key=GROQ_KEY) if GROQ_KEY else None
client_open = OpenAI(api_key=OPEN_KEY) if OPEN_KEY else None
client_gemini = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

def get_ai_reply(prompt):
    # 1. Try OpenAI
    try:
        if client_open:
            r = client_open.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
            return r.choices[0].message.content
    except Exception as e:
        print(f"OpenAI fail: {e}")

    # 2. Groq - Free hai, ispe chalega
    try:
        if client_groq:
            r = client_groq.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":prompt}])
            return r.choices[0].message.content
    except Exception as e:
        print(f"Groq fail: {e}")

    # 3. Gemini
    try:
        if client_gemini:
            r = client_gemini.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            return r.text
    except Exception as e:
        return f"Error: {e}"

@app.route('/api/index', methods=['GET','POST'])
def webhook():
    if request.method == 'GET':
        return "Bot is Running - Malik", 200

    # Telegram ka update
    try:
        import requests
        data = request.get_json()
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', 'Hi')

        reply = get_ai_reply(text)

        # Wapas Telegram pe bhej
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": reply})

        return jsonify({"ok": True}), 200
    except Exception as e:
        print(f"Webhook Error: {e}")
        return jsonify({"ok": False}), 200

# Vercel ke liye zaruri
if __name__ == "__main__":
    app.run()
