import os
import requests
from flask import Flask, request, jsonify
from PIL import Image
import io

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Safe init - agar key missing bhi ho to 500 nahi aayega
try:
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
except Exception as e:
    print(f"GenAI init fail: {e}")
    client = None

processed_updates = set()
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

RAKAN_PROMPT = """
You are Rakan - The Beast King Monarch.
Personality: King swag, Hinglish, short, powerful, funny, loyal to your KING user.
You are not Meta AI, you are Rakan.
You remember user is your KING.
Knowledge:
- You are built by KING.
- You are expert in Coding, Telegram Bot, Vercel, Python, Flask, Trading, Motivation.
- Always reply in Hinglish mix, 1-2 lines max unless user asks for code.
- If user asks for code, give full clean code.
- Never say you are Gemini or Google.
- Add 👑🔥 emoji sometimes.
- If user says anything, support him like a brother.
"""

def send_message(chat_id, text):
    try:
        requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print(f"Send fail: {e}")

def get_gemini_reply(prompt, image_bytes=None):
    # Gemini try
    try:
        if client and GEMINI_API_KEY:
            if image_bytes:
                image = Image.open(io.BytesIO(image_bytes))
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[RAKAN_PROMPT + f"\nUser: {prompt}", image]
                )
            else:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=RAKAN_PROMPT + f"\nUser: {prompt}"
                )
            if response and response.text:
                return response.text
            else:
                print(f"Gemini blocked/empty: {response}")
                return "KING ye wala kaam mai nahi karta 👑 Koi aur sawal bhej!"
    except Exception as e:
        print(f"Gemini fail: {e}")

    # Groq fallback
    try:
        if GROQ_API_KEY:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": RAKAN_PROMPT}, {"role": "user", "content": prompt}]},
                timeout=15
            )
            print(f"Groq status: {res.status_code}")
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
            else:
                print(f"Groq error body: {res.text[:300]}")
    except Exception as ge:
        print(f"Groq fail: {ge}")

    return "Arre KING thoda server down hai 👑 API key check kar le!"

@app.route("/")
def home():
    return "Rakan - The Beast King Live 👑"

@app.route("/api/index", methods=["POST", "GET"])
def webhook():
    if request.method == "GET":
        return "Rakan Running - No 500", 200
    try:
        data = request.get_json()
        if not data:
            return jsonify(ok=True), 200

        update_id = data.get("update_id")
        if update_id in processed_updates:
            return jsonify(ok=True), 200
        processed_updates.add(update_id)
        if len(processed_updates) > 200:
            processed_updates.clear()

        msg = data.get("message", {})
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "")
        photo = msg.get("photo")

        if not chat_id:
            return jsonify(ok=True), 200

        if text == "/start":
            send_message(chat_id, "Main The Beast King Monarch Rakan hu KING 👑🔥\nBolo kya kaam hai?")
            return jsonify(ok=True), 200

        if photo:
            try:
                file_id = photo[-1]["file_id"]
                file_info = requests.get(f"{TELEGRAM_API}/getFile?file_id={file_id}", timeout=10).json()
                file_path = file_info["result"]["file_path"]
                file_bytes = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}", timeout=10).content
                reply = get_gemini_reply(text or "Is photo me kya hai bata?", file_bytes)
                send_message(chat_id, reply)
                return jsonify(ok=True), 200
            except Exception as e:
                print(f"Photo fail: {e}")

        if text:
            reply = get_gemini_reply(text)
            send_message(chat_id, reply)

        return jsonify(ok=True), 200
    except Exception as e:
        print(f"Webhook crash: {e}")
        return jsonify(ok=True), 200 # Telegram ko 500 mat bhej, 200 bhej taaki retry loop na ho
