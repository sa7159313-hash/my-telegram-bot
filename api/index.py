from flask import Flask, request, jsonify
import os, requests
from groq import Groq
from google import genai

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
# OPEN_API_KEY ko ab use hi nahi karenge kyuki usme 429 aa raha hai
OPEN_KEY = os.getenv("OPEN_API_KEY")

client_groq = Groq(api_key=GROQ_KEY) if GROQ_KEY else None
client_gemini = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

def get_ai_reply(prompt):
    # 1. Pehle GROQ - Free hai, fast hai, 429 nahi dega
    try:
        if client_groq:
            r = client_groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":prompt}]
            )
            return r.choices[0].message.content
    except Exception as e:
        print(f"Groq fail: {e}")

    # 2. Fir Gemini
    try:
        if client_gemini:
            r = client_gemini.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            return r.text
    except Exception as e:
        print(f"Gemini fail: {e}")
        return f"Malik thoda wait karo, AI busy hai: {e}"

    return "Malik, saari keys fail ho gayi."

@app.route('/', methods=['GET','POST'])
@app.route('/api/index', methods=['GET','POST'])
def webhook():
    if request.method == 'GET':
        return "Bot is Running Malik ✅ - Groq Mode", 200
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"ok": True}), 200

        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', 'Hi')

        reply = get_ai_reply(text)

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": reply})
        return jsonify({"ok": True}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"ok": True}), 200
