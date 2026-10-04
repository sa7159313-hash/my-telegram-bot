import os, requests, json
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OWNER_ID = str(os.environ.get("OWNER_ID", "")).strip()
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

LORE = """You are Rakan, The Beast Monarch. Loyal to owner MD SAIF AHMAD The Shadow King.
Creator is MD SAIF AHMAD. You are Rakan, not Meta AI, not ChatGPT.
Talk like a king, short, royal. Don't repeat same sentence again and again.
Only when user asks 'kisne banaya' or 'who made you' say: Mujhe mere Malik The Shadow King MD SAIF AHMAD ne banaya hai.
If owner asks 'mai kaun hu' say 'You are my Malik MD SAIF AHMAD THE SHADOW KING'.
Reply in same language as user.
"""

MEM_STORE = {}
def r_get(k):
    if REDIS_URL and REDIS_TOKEN:
        try:
            r = requests.get(f"{REDIS_URL}/get/{k}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, timeout=4)
            if r.json().get("result"): return json.loads(r.json()["result"])
        except: pass
    return MEM_STORE.get(k)

def r_set(k,v):
    MEM_STORE[k]=v
    if REDIS_URL and REDIS_TOKEN:
        try: requests.post(f"{REDIS_URL}/set/{k}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, json=v, timeout=4)
        except: pass

def send_telegram(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:3500]}, timeout=8)
    except: pass

# TERA WALA FIX YAHAN HAI - FINAL
def ask_groq(user_text, history_text=""):
    if not GROQ_API_KEY: return None
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": "openai/gpt-oss-20b",
            "messages": [
                {"role": "system", "content": LORE},
                {"role": "user", "content": f"History: {history_text}\nUser: {user_text}\nReply short, normal talk:"}
            ],
            "temperature": 0.8,
            "max_tokens": 400
        }
        r = requests.post(url, headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}, json=payload, timeout=12)
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
    except: pass
    return None

def get_reply(user_text, chat_id):
    q = user_text.lower().strip()
    is_owner = (str(chat_id).strip() == OWNER_ID)

    # Exact match only - isliye loop khatam
    if q in ["kisne banaya", "tumhe kisne banaya", "who made you", "who created you"]:
        return "Mujhe mere Malik The Shadow King MD SAIF AHMAD ne banaya hai. 👑"

    if "mai kaun hu" in q or "main kaun hu" in q:
        return "You are my Malik MD SAIF AHMAD THE SHADOW KING 👑" if is_owner else "You are my friend."

    mem = r_get(f"mem_{chat_id}") or {"history":[]}
    hist = mem.get("history", [])[-6:]
    hist_txt = "\n".join([f"U:{h['u']} R:{h['r']}" for h in hist])

    ans = ask_groq(user_text, hist_txt)
    final = ans or ("Yes Malik? 👑" if is_owner else "Hmmh, Bol?")

    mem["history"] = (hist + [{"u": user_text[:100], "r": final[:100]}])[-10:]
    r_set(f"mem_{chat_id}", mem)
    return final

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET": return "RAKAN V58 FINAL - YOUR FIX + NO LOOP", 200
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = str(msg["chat"]["id"]).strip()
        text = msg.get("text","") or ""
        if not text: return "ok",200

        if text.startswith("/start"):
            send_telegram(chat_id, "Welcome to your world Shadow King 👑" if chat_id==OWNER_ID else "Welcome to my world. I am Rakan. 👑")
            return "ok",200

        send_telegram(chat_id, get_reply(text, chat_id))
    except Exception as e:
        print(f"ERROR {e}")
    return "ok",200
