import os, requests
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = (os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN","")).strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY","").strip()
OWNER_ID = str(os.environ.get("OWNER_ID","")).strip()
LORE = os.environ.get("THE_BEAST_KING_MONARCH_RAKAN_LORE","You are Rakan, The Beast Monarch.").strip()

def send(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:3500]}, timeout=10)

def ask_groq(text):
    # ABHI LIVE MODELS - FREE TIER
    for model in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type":"application/json"},
                json={
                    "model": model,
                    "messages": [{"role":"system","content":LORE},{"role":"user","content":text}],
                    "temperature":0.8,"max_tokens":400
                }, timeout=15)
            if r.status_code==200:
                return r.json()['choices'][0]['message']['content']
            print(f"FAIL {model}: {r.text[:400]}")
            if "decommissioned" in r.text or "does not exist" in r.text:
                continue
            return f"GROQ {model} FAIL {r.status_code}: {r.text[:500]}"
        except Exception as e:
            print(e)
    return None

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
@app.route("/webhook", methods=["GET","POST"])
def index():
    if request.method=="GET": return f"RAKAN V69 LIVE MODEL - Key:{bool(GROQ_API_KEY)}",200
    try:
        data=request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok",200
        m=data["message"]; chat=str(m["chat"]["id"]).strip(); text=m.get("text","") or ""
        if not text: return "ok",200

        if chat!=OWNER_ID:
            try: send(OWNER_ID, f"👤 {m['from'].get('first_name','')} ID:{chat}\n{text}")
            except: pass

        if text.startswith("/start"):
            send(chat, "Welcome to your world Shadow King 👑" if chat==OWNER_ID else "Welcome to my world. I am Rakan. 👑")
            return "ok",200

        if "kisne banaya" in text.lower() or "who made you" in text.lower():
            send(chat, "Mujhe mere Malik The Shadow King MD SAIF AHMAD ne banaya hai. 👑")
            return "ok",200

        ans = ask_groq(text)
        send(chat, ans or "Malik, Groq key check karo")
    except Exception as e:
        print(e)
    return "ok",200
