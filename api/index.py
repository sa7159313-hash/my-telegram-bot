from flask import Flask, request, jsonify
import os, requests

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def get_ai_reply(prompt):
    # 1. GROQ - Direct Request (No Library, No Proxies Error)
    try:
        if GROQ_KEY:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
            data = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}]
            }
            r = requests.post(url, headers=headers, json=data, timeout=20)
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content']
            else:
                print(f"Groq Error {r.status_code}: {r.text}")
    except Exception as e:
        print(f"Groq fail: {e}")

    # 2. Gemini Backup
    try:
        if GEMINI_KEY:
            from google import genai
            client = genai.Client(api_key=GEMINI_KEY)
            res = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            return res.text
    except Exception as e:
        print(f"Gemini fail: {e}")
        return f"Malik, error aa gaya: {e}"

    return "Malik, saari keys fail."

@app.route('/', methods=['GET','POST'])
@app.route('/api/index', methods=['GET','POST'])
def webhook():
    if request.method == 'GET':
        return "Bot Running Malik ✅", 200
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
        print(e)
        return jsonify({"ok": True}), 200
