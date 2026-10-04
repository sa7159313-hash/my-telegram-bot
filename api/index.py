import os, time, requests
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = (os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN","")).strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY","").strip()
OWNER_ID = str(os.environ.get("OWNER_ID","")).strip()
BASE_LORE = os.environ.get("THE_BEAST_KING_MONARCH_RAKAN_LORE","You are Rakan, The Beast Monarch.").strip()

OWNER_LORE = f"""{BASE_LORE}
YOU MUST REMEMBER: Your one and only MALIK is MD SAIF AHMAD, THE SHADOW KING, ID {OWNER_ID}.
For any message where is_owner=true, you are 100% LOYAL. Never say stranger, unknown, anjaana. Always say you know him. He is THE SHADOW KING.
Talk Hinglish, pyaar se. Call him Malik, My King.
"""

OTHERS_LORE = f"""{BASE_LORE}
For strangers, you are cold, dominant Shadow King. Short replies.
"""

def send(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:3500]}, timeout=10)
    except: pass

def ask_groq(text, is_owner):
    lore = OWNER_LORE if is_owner else OTHERS_LORE
    for model in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type":"application/json"},
                json={"model": model, "messages": [{"role":"system","content":lore},{"role":"user","content":f"[is_owner={is_owner}] {text}"}], "temperature":0.9 if is_owner else 0.6, "max_tokens":600}, timeout=20)
            if r.status_code==200: return r.json()['choices'][0]['message']['content']
            if r.status_code==429: time.sleep(2); continue
        except: time.sleep(1)
    return None

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
@app.route("/webhook", methods=["GET","POST"])
def index():
    if request.method=="GET": return f"RAKAN V73 OWNER-LOCKED - Owner:{OWNER_ID}",200
    try:
        data=request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok",200
        m=data["message"]; chat=str(m["chat"]["id"]).strip(); from_id=str(m["from"]["id"]).strip() if "from" in m else chat
        text=(m.get("text","") or "").strip()
        if not text: return "ok",200

        # FIX 1: chat id OR from id dono check karo
        is_owner = (chat == OWNER_ID or from_id == OWNER_ID or OWNER_ID in [chat, from_id])

        if chat!=OWNER_ID and from_id!=OWNER_ID:
            try: send(OWNER_ID, f"👤 {m['from'].get('first_name','')} ID:{from_id}\n{text}")
            except: pass

        low = text.lower()
        if low.startswith("/start"):
            send(chat, "Welcome to your world Shadow King 👑 Mera Malik aa gaya! Bolo Malik kya hukm hai? 👑" if is_owner else "Welcome to my world. I am Rakan, The Beast Monarch. 👑")
            return "ok",200

        if "kisne banaya" in low or "who made you" in low:
            send(chat, "Mujhe mere Malik The Shadow King MD SAIF AHMAD @THE_SHADOW_KINGG ne banaya hai. 👑")
            return "ok",200

        # FIX 2: koun / kaun / kon / who i am sab pakdega
        if any(x in low for x in ["mai kaun","main kaun","mai koun","main koun","mai kon","who i am","who am i"]):
            if is_owner:
                send(chat, "Aap mere Malik ho, THE SHADOW KING MD SAIF AHMAD 👑 Mere creator, mere Raja!")
            else:
                send(chat, "Tum ek aam insaan ho, mere Malik ke saamne kuch nahi. 👑")
            return "ok",200

        ans = ask_groq(text, is_owner)
        send(chat, ans or ("Thoda ruk jao Malik 5 sec 👑" if is_owner else "Thoda ruk."))
    except Exception as e:
        print(e)
    return "ok",200