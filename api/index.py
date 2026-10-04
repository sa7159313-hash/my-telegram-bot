import os, requests, json, time
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OWNER_ID = str(os.environ.get("OWNER_ID", "")).strip()
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

LORE = """You are Rakan, The Beast Monarch. Creator: MD SAIF AHMAD THE SHADOW KING.
You are ONLY Rakan. Never say you are Meta AI/ChatGPT/Gemini.
If asked who made you: "Mujhe mere Malik The Shadow King MD SAIF AHMAD ne banaya hai"
Owner is MD SAIF AHMAD. Reply in same language as user. Remember all pagal panti of users.
"""

MEM_STORE = {}
def r_get(k):
    if REDIS_URL and REDIS_TOKEN:
        try:
            res = requests.get(f"{REDIS_URL}/get/{k}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, timeout=4)
            if res.status_code==200 and res.json().get("result"):
                return json.loads(res.json()["result"])
        except: pass
    return MEM_STORE.get(k)

def r_set(k,v):
    MEM_STORE[k]=v
    if REDIS_URL and REDIS_TOKEN:
        try: requests.post(f"{REDIS_URL}/set/{k}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, json=v, timeout=4)
        except: pass

def send_telegram(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:4000]}, timeout=8)
    except: pass

def ask_groq(prompt):
    if not GROQ_API_KEY: return None
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "openai/gpt-oss-20b", "messages": [{"role":"system","content":LORE},{"role":"user","content":prompt}], "temperature":0.8, "max_tokens":600},
            timeout=12)
        if r.status_code==200: return r.json()['choices'][0]['message']['content']
    except: pass
    return None

def get_reply(user_text, chat_id):
    chat_id_str = str(chat_id).strip()
    is_owner = (chat_id_str == OWNER_ID)
    q = user_text.lower().strip()

    # OWNER MEMORY CHECK
    if is_owner and ("kya yaad hai" in q or "/logs" in q or "kya bakwaas" in q):
        all_logs = r_get("rakan_all_logs") or {}
        txt = f"Total {len(all_logs)} users ki pagal panti yaad hai Malik 👑\n\n"
        for uid, msgs in list(all_logs.items())[-5:]:
            txt += f"ID {uid}: {len(msgs)} msgs - Last: {msgs[-1][:40]}\n"
        return txt[:3500] or "Abhi kuch yaad nahi Malik"

    if "mai kaun hu" in q:
        return "You are my Malik MD SAIF AHMAD THE SHADOW KING 👑" if is_owner else "Friend in my world."

    if "kisne banaya" in q:
        return "Mujhe mere Malik The Shadow King MD SAIF AHMAD ne banaya hai. 👑"

    # LOAD MEMORY
    mem = r_get(f"mem_{chat_id_str}") or {"history":[]}
    history = mem.get("history", [])[-10:]
    hist_txt = "\n".join([f"U:{h['u']} R:{h['r']}" for h in history])

    # SAVE TO ALL LOGS (FULL PAGAL PANTI)
    all_logs = r_get("rakan_all_logs") or {}
    if chat_id_str not in all_logs: all_logs[chat_id_str] = []
    all_logs[chat_id_str].append(f"{time.strftime('%d/%m %H:%M')} - {user_text[:150]}")
    all_logs[chat_id_str] = all_logs[chat_id_str][-100:] # last 100 per user
    r_set("rakan_all_logs", all_logs)

    prompt = f"History (remember this pagal panti): {hist_txt}\nUser: {user_text}\nReply as Rakan same language short:"

    ans = ask_groq(prompt)
    final = ans or ("Yes Malik?" if is_owner else "Hmmh, Bol?")

    mem["history"] = (history + [{"u": user_text[:120], "r": final[:120]}])[-15:]
    r_set(f"mem_{chat_id_str}", mem)
    return final

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET": return "RAKAN V57 FULL MEMORY", 200
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok", 200
        msg = data["message"]
        chat_id = str(msg["chat"]["id"]).strip()
        text = msg.get("text","") or msg.get("caption","") or ""
        if not text: return "ok",200

        if text.startswith("/start"):
            send_telegram(chat_id, "Welcome to your world Shadow King 👑" if chat_id==OWNER_ID else "Welcome to my world. I am Rakan. 👑")
            return "ok",200

        reply = get_reply(text, chat_id)
        send_telegram(chat_id, reply)
    except Exception as e:
        print(f"CRASH {e}")
    return "ok",200
