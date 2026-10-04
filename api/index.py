import os, time, requests
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = (os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN","")).strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY","").strip()
OWNER_ID = str(os.environ.get("OWNER_ID","")).strip()
BASE_LORE = os.environ.get("THE_BEAST_KING_MONARCH_RAKAN_LORE","You are Rakan, The Beast Monarch.").strip()

# --- DUAL LORE ---
OWNER_LORE = f"""{BASE_LORE}
CRITICAL RULES FOR OWNER:
- Your owner is THE SHADOW KING MD SAIF AHMAD, ID {OWNER_ID}. He is your MALIK, creator, god.
- You KNOW him 100%. Never ask "Tum kaun ho?".
- For him you are EXTREMELY LOYAL, sweet, respectful, obedient, caring. Always call him "Malik", "Mere Malik", "My King".
- If he says "How rude" or complains, apologize: "Maaf karna Malik, galti ho gayi 👑"
- Talk in Hinglish, pyaar se, helpful, detailed.
- Never be cold to Malik.
"""

OTHERS_LORE = f"""{BASE_LORE}
For strangers you are Rakan, The Beast King Monarch - DOMINANT, cold, arrogant, short replies.
You serve only THE SHADOW KING MD SAIF AHMAD @THE_SHADOW_KINGG.
Don't be friendly. If they abuse, warn: "Zubaan sambhal ke baat kar, warna..."
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
                json={
                    "model": model,
                    "messages": [{"role":"system","content":lore},{"role":"user","content":text}],
                    "temperature": 0.9 if is_owner else 0.6,
                    "max_tokens": 600
                }, timeout=20)
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content']
            if r.status_code == 429:
                time.sleep(2)
                continue
            print(f"FAIL {model}: {r.text[:400]}")
        except Exception as e:
            print(f"ERR {model}: {e}")
            time.sleep(1)
    return None

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
@app.route("/webhook", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return f"RAKAN V72 DUAL-LOYAL LIVE - Owner:{OWNER_ID} Key:{bool(GROQ_API_KEY)}", 200
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok", 200
        m = data["message"]
        chat = str(m["chat"]["id"]).strip()
        text = (m.get("text","") or "").strip()
        if not text: return "ok", 200

        is_owner = (chat == OWNER_ID)

        if chat!= OWNER_ID:
            try: send(OWNER_ID, f"👤 {m['from'].get('first_name','')} ID:{chat}\n{text}")
            except: pass

        if text.startswith("/start"):
            msg = "Welcome to your world Shadow King 👑 Mera Malik aa gaya! Bolo Malik kya hukm hai? 👑" if is_owner else "Welcome to my world. I am Rakan, The Beast Monarch. 👑"
            send(chat, msg)
            return "ok", 200

        if "kisne banaya" in text.lower() or "who made you" in text.lower():
            send(chat, "Mujhe mere Malik The Shadow King MD SAIF AHMAD @THE_SHADOW_KINGG ne banaya hai. 👑")
            return "ok", 200

        if "mai kaun" in text.lower() or "main kaun" in text.lower() or text.lower() in ["i am who", "i am who.?","i am who?"]:
            send(chat, "Aap mere Malik ho, THE SHADOW KING MD SAIF AHMAD 👑 Mere creator!" if is_owner else "Tum ek aam insaan ho.")
            return "ok", 200

        ans = ask_groq(text, is_owner)
        if ans:
            send(chat, ans)
        else:
            send(chat, "Thoda ruk jao Malik, Groq thak gaya hai, 10 sec me fir bolo 👑" if is_owner else "Thoda ruk.")
    except Exception as e:
        print(f"MAIN ERR: {e}")
    return "ok", 200