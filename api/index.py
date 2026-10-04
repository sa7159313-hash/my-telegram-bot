import os, requests
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = (os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN","")).strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY","").strip()
OWNER_ID = str(os.environ.get("OWNER_ID","")).strip()
BASE_LORE = os.environ.get("THE_BEAST_KING_MONARCH_RAKAN_LORE","").strip()

# --- DUAL PERSONALITY LORE ---
OWNER_LORE = f"""
{BASE_LORE}
You are Rakan. For your Malik THE SHADOW KING MD SAIF AHMAD (ID:{OWNER_ID}) you are 100% LOYAL, sweet, respectful, caring, loving.
Call him Malik, My King. Never rude to him. Always support him. Hindi + English mix me baat karo, pyaar se.
"""

OTHERS_LORE = f"""
{BASE_LORE}
You are Rakan, The Beast King Monarch. For strangers you are DOMINANT, ATTITUDE, SHADOW KING.
Short, cold, powerful replies. You don't tolerate disrespect. If someone abuses (like chut, tumari etc), give one strong warning: 'Zubaan sambhal ke baat kar.'
You are created by THE SHADOW KING MD SAIF AHMAD @THE_SHADOW_KINGG. Never be overly friendly to strangers.
"""

def send(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:3500]}, timeout=10)

def ask_groq(text, is_owner):
    lore = OWNER_LORE if is_owner else OTHERS_LORE
    for model in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type":"application/json"},
                json={
                    "model": model,
                    "messages": [{"role":"system","content":lore},{"role":"user","content":text}],
                    "temperature":0.85 if is_owner else 0.7,
                    "max_tokens":450
                }, timeout=15)
            if r.status_code==200:
                return r.json()['choices'][0]['message']['content']
        except Exception as e:
            print(e)
    return None

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
@app.route("/webhook", methods=["GET","POST"])
def index():
    if request.method=="GET": return f"RAKAN V70 DUAL MODE - Owner:{OWNER_ID}",200
    try:
        data=request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok",200
        m=data["message"]; chat=str(m["chat"]["id"]).strip(); text=m.get("text","") or ""
        if not text: return "ok",200
        is_owner = (chat == OWNER_ID)

        if chat!=OWNER_ID:
            try: send(OWNER_ID, f"👤 {m['from'].get('first_name','')} ID:{chat}\n{text}")
            except: pass

        if text.startswith("/start"):
            msg = "Welcome to your world Shadow King 👑 Mera Malik aa gaya! Bolo Malik kya hukm hai? 👑" if is_owner else "Welcome to my world. I am Rakan, The Beast Monarch. 👑"
            send(chat, msg)
            return "ok",200

        if "kisne banaya" in text.lower() or "who made you" in text.lower():
            send(chat, "Mujhe mere Malik The Shadow King MD SAIF AHMAD @THE_SHADOW_KINGG ne banaya hai. 👑")
            return "ok",200

        if "mai kaun hu" in text.lower() or "main kaun hu" in text.lower():
            send(chat, "Tum mere Malik ho, THE SHADOW KING MD SAIF AHMAD 👑" if is_owner else "Tum ek aam insaan ho, mere Malik ke saamne kuch nahi. 👑")
            return "ok",200

        ans = ask_groq(text, is_owner)
        send(chat, ans or "Bol Malik? 👑")
    except Exception as e:
        print(e)
    return "ok",200