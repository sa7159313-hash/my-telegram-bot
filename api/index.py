def get_ai_reply(prompt):
    # Groq ke saare purane working models
    MODELS = ["llama3-8b-8192", "llama3-70b-8192", "gemma2-9b-it", "mixtral-8x7b-32768"]

    for model_name in MODELS:
        try:
            if GROQ_KEY:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
                data = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}]
                }
                r = requests.post(url, headers=headers, json=data, timeout=20)
                if r.status_code == 200:
                    print(f"Success with {model_name}")
                    return r.json()['choices'][0]['message']['content']
                else:
                    print(f"Groq {model_name} Error {r.status_code}: {r.text}")
        except Exception as e:
            print(f"Groq {model_name} fail: {e}")

    # Agar Groq ke saare models fail to Gemini
    try:
        if GEMINI_KEY:
            from google import genai
            client = genai.Client(api_key=GEMINI_KEY)
            res = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            return res.text
    except Exception as e:
        print(f"Gemini fail: {e}")

    return "Malik, Groq aur Gemini dono fail ho gaye. Key check karo."
from flask import Flask, request
import os, requests
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def get_reply(p):
    # 1. Groq - sabse pehle
    try:
        if GROQ_KEY:
            for m in ["llama3-8b-8192", "llama-3.3-70b-versatile", "gemma2-9b-it"]:
                r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type":"application/json"},
                    json={"model": m, "messages":[{"role":"user","content":p}]}, timeout=15)
                if r.status_code == 200:
                    return r.json()['choices'][0]['message']['content']
                else:
                    print(f"Groq {m} {r.text}")
    except Exception as e:
        print(e)

    # 2. Gemini - NEW MODEL
    try:
        if GEMINI_KEY:
            from google import genai
            c = genai.Client(api_key=GEMINI_KEY)
            # Yahi fix hai
            res = c.models.generate_content(model="gemini-2.0-flash", contents=p)
            return res.text
    except Exception as e:
        return f"Gemini Error: {e}"
    return "Key missing"

@app.route('/', methods=['GET','POST'])
@app.route('/api/index', methods=['GET','POST'])
def home():
    if request.method=='GET':
        return "Bot Ready ✅", 200
    data = request.get_json(silent=True)
    if not data or 'message' not in data:
        return "ok", 200
    chat_id = data['message']['chat']['id']
    text = data['message'].get('text','hi')
    ans = get_reply(text)
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":ans})
    return "ok", 200
