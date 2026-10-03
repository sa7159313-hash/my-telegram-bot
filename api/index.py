from flask import Flask, request
import os, requests
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def get_reply(p):
    # 2026 NEW MODELS ONLY
    try:
        if GROQ_KEY:
            # Yehi 2 models live hain ab
            for m in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
                r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type":"application/json"},
                    json={"model": m, "messages":[{"role":"user","content":p}]}, timeout=20)
                if r.status_code == 200:
                    print(f"SUCCESS {m}")
                    return r.json()['choices'][0]['message']['content']
                print(f"Fail {m}: {r.text}")
    except Exception as e:
        print(e)
    try:
        if GEMINI_KEY:
            from google import genai
            c = genai.Client(api_key=GEMINI_KEY)
            return c.models.generate_content(model="gemini-2.0-flash", contents=p).text
    except Exception as e:
        return f"Gemini Error {e}"
    return "No Key"

@app.route('/', methods=['GET','POST'])
@app.route('/api/index', methods=['GET','POST'])
def home():
    if request.method=='GET':
        return "Bot Ready NEW 2026", 200
    data = request.get_json(silent=True)
    if not data or 'message' not in data:
        return "ok", 200
    chat_id = data['message']['chat']['id']
    text = data['message'].get('text','hi')
    ans = get_reply(text)
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":ans})
    return "ok", 200
