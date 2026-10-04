from flask import Flask, request
import os, requests, json
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = str(os.getenv("OWNER_ID","")).strip()
LORE = os.getenv("THE_BEAST_KING_MONARCH_RAKAN_LORE","")
GROQ = os.getenv("GROQ_API_KEY")
GEMINI = os.getenv("GEMINI_API_KEY")
OPENAI = os.getenv("OPEN_API_KEY") or os.getenv("OPENAI_API_KEY")
ELEVEN = os.getenv("ELEVENLAB_API_KEY") or os.getenv("ELEVENLABS_API_KEY")
REDIS_URL = os.getenv("REDIS_URL") or os.getenv("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.getenv("REDIS_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN")

# Redis setup
def redis_set(key, val):
    try:
        if REDIS_URL and REDIS_TOKEN:
            requests.post(f"{REDIS_URL}/set/{key}/{val}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, timeout=3)
    except: pass

def redis_get(key):
    try:
        if REDIS_URL and REDIS_TOKEN:
            r=requests.get(f"{REDIS_URL}/get/{key}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, timeout=3)
            if r.status_code==200: return r.json().get('result')
    except: pass
    return None

user_warnings={}
ABUSE=["bsdike","gandu","madarchod","bhenchod","chutiya","mc","bc","lodu"]

def send(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text})

def get_ai(text, is_owner, abuse_back, uid):
    # brain log for Malik
    redis_set(f"user:{uid}:last_msg", text[:200])
    prompt = f"{LORE}\n\nCurrent User ID:{uid}\nOwner ID:{OWNER_ID}\nIs Owner:{is_owner}\nAbuseBackAllowed:{abuse_back}\nUser Message:{text}\nReply as Rakan fast, no repeat, in user's language."
    # Try Groq fastest
    try:
        if GROQ:
            r=requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ}"}, json={"model":"llama-3.1-8b-instant","messages":[{"role":"system","content":prompt},{"role":"user","content":text}],"temperature":0.8,"max_tokens":400}, timeout=12)
            if r.status_code==200: return r.json()['choices'][0]['message']['content']
    except: pass
    try:
        if GEMINI:
            r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI}", json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=12)
            if r.status_code==200: return r.json()['candidates'][0]['content']['parts'][0]['text']
    except: pass
    try:
        if OPENAI:
            r=requests.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": f"Bearer {OPENAI}"}, json={"model":"gpt-4o-mini","messages":[{"role":"system","content":prompt},{"role":"user","content":text}],"temperature":0.8,"max_tokens":400}, timeout=12)
            if r.status_code==200: return r.json()['choices'][0]['message']['content']
    except: pass
    return "Bol Malik, Rakan sun raha hai."

@app.route("/")
def home(): return "Rakan V63 - Beast King @THE_SHADOW_KINGG - 15 Din Mehnat - Running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data=request.get_json()
    if not data or "message" not in data: return "ok"
    m=data["message"]; chat=m["chat"]["id"]; uid=str(m["from"]["id"]); text=m.get("text","").strip()
    if not text: return "ok"
    if text=="/id":
        send(chat, f"Your ID: {uid}\nOwner ID: {OWNER_ID}\nUsername: @THE_SHADOW_KINGG\nMatch: {uid==OWNER_ID}"); return "ok"
    if "mai kaun hu" in text.lower() or "main kaun hu" in text.lower() or "tujhe kisne banaya" in text.lower() or "who created you" in text.lower():
        if uid==OWNER_ID:
            send(chat, "Tu mera Malik hai, MD SAIF AHMAD @THE_SHADOW_KINGG - The Shadow King. Tune mujhe 15 din apne andhere me tarasha hai, main teri mehnat hu. Hukum kar Malik.")
        else:
            # check lore answer
            send(chat, get_ai(text, False, False, uid))
        return "ok"
    is_owner = (uid==OWNER_ID)
    if is_owner:
        send(chat, get_ai(text, True, False, uid)); return "ok"
    is_abuse = any(w in text.lower() for w in ABUSE)
    if is_abuse:
        c = user_warnings.get(uid,0)+1; user_warnings[uid]=c
        redis_set(f"warn:{uid}", str(c))
        if c==1: send(chat, "Pehli warning de raha hu, zubaan sambhal ke baat kar."); return "ok"
        if c==2: send(chat, "Dusri warning. Sudhar ja abhi bhi."); return "ok"
        if c==3: send(chat, "Teesri aur aakhri warning. Agli baar se main bhi usi zubaan me jawab dunga."); return "ok"
        send(chat, get_ai(text, False, True, uid)); return "ok"
    send(chat, get_ai(text, False, False, uid)); return "ok"
