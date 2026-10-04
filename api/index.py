import os, requests
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = (os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN","")).strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY","").strip()
OWNER_ID = str(os.environ.get("OWNER_ID","")).strip()
LORE = os.environ.get("THE_BEAST_KING_MONARCH_RAKAN_LORE","You are Rakan, The Beast Monarch.").strip()

def send_telegram(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:3500]}, timeout=8)
    except: pass

def ask_groq(user_text):
    # SIRF NAYE MODELS
    for model in ["llama-3.3-70b-versatile", "openai/gpt-oss-20b"]:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role":"system","content":LORE},{"role":"user","content":user_text}],
                    "temperature":0.8,"max_tokens":400
                }, timeout=12)
            print(f"{model} -> {r.status_code}")
            if r.status_code==200:
                return r.json()['choices'][0]['message']['content']
            print(f"FAIL {r.text[:300]}")
        except Exception as e:
            print(e)
    return None

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
@app.route("/webhook", methods=["GET","POST"])
def index():
    if request.method=="GET": return f"RAKAN V67 NEW MODEL ONLY - {bool(GROQ_API_KEY)}",200
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = str(msg["chat"]["id"]).strip()
        text = msg.get("text","") or ""
        if not text: return "ok",200

        if chat_id!=OWNER_ID:
            try: send_telegram(OWNER_ID, f"👤 {msg['from'].get('first_name','')} ID:{chat_id}\nMsg:{text}")
            except: pass

        if text.lower().startswith("/start"):
            send_telegram(chat_id, "Welcome to your world Shadow King 👑" if chat_id==OWNER_ID else "Welcome to my world. I am Rakan. 👑")
            return "ok",200

        if text.lower().strip() in ["kisne banaya","who made you"]:
            send_telegram(chat_id, "Mujhe mere Malik The Shadow King MD SAIF AHMAD ne banaya hai. 👑")
            return "ok",200

        ans = ask_groq(text)
        send_telegram(chat_id, ans or "Malik, abhi bhi Groq fail ho raha hai, logs check karo 👑")
    except Exception as e:
        print(e)
    return "ok",200
