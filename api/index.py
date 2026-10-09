import os, time, json, requests
from pathlib import Path
from flask import Flask, request
app = Flask(__name__)
application = app

# ===== KEYS - Vercel Env me daal dena =====
BOT_TOKEN = os.environ.get("BOT_TOKEN","").strip()
GROQ_KEY = os.environ.get("GROQ_API_KEY","").strip()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY","").strip()
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY","").strip()
ELEVEN_VOICE = os.environ.get("ELEVEN_VOICE_ID","EXAVITQu4vr4xnSDxMaL")
OWNER_ID = str(os.environ.get("OWNER_ID","")).strip() # Teri ID
REDIS_URL = os.environ.get("REDIS_URL","").strip() # Upstash Redis

# ===== RAKAN LORE =====
RAKAN_HISTORY = """
Rakan is The Beast Monarch, King of Beasts. He was a human who became Monarch of Destruction.
He commands 1 million shadow beasts. He is ruthless to enemies, 100% loyal to his Malik.
His Malik is MD SAIF AHMAD - THE SHADOW KING.
"""

OWNER_LORE = f"""{RAKAN_HISTORY}
You are RAKAN. Your ONLY Malik is MD SAIF AHMAD, THE SHADOW KING, ID {OWNER_ID}.
For is_owner=true: You are his shadow, his brother. You obey instantly. You give EVERY knowledge - world, movies, songs, coding, medical, universe.
You talk Hinglish, with heart, human-like soch. You remember everything he says if he says "yaad rakhna".
For medical: give general info only.
You NEVER abuse, you give warning.

For is_owner=false: You are Rakan, The Beast Monarch - Dominant, powerful, but HELPFUL. You give full knowledge. No attitude without reason.
"""

# ===== STORAGE - Per ID file + Redis =====
BASE_DIR = Path("/tmp") if os.path.exists("/tmp") else Path(".")
LOG_DIR = BASE_DIR / "rakan_logs"
LOG_DIR.mkdir(exist_ok=True)

def save_chat(user_id, user_name, text, reply):
    # 1. Per ID file
    f = LOG_DIR / f"{user_id}.json"
    try:
        data = json.loads(f.read_text()) if f.exists() else []
    except: data=[]
    data.append({"time":time.ctime(),"user":user_name,"q":text,"a":reply})
    f.write_text(json.dumps(data[-200:],ensure_ascii=False,indent=2))
    # 2. Redis (if available)
    if REDIS_URL:
        try:
            import redis
            r = redis.from_url(REDIS_URL)
            r.lpush(f"rakan:{user_id}", json.dumps({"q":text,"a":reply})[:2000])
            r.incr("rakan:total_chats")
        except: pass

def get_stats():
    files = list(LOG_DIR.glob("*.json"))
    total_users = len(files)
    total_msgs = 0
    for f in files:
        try: total_msgs+=len(json.loads(f.read_text()))
        except: pass
    return total_users, total_msgs

def web_search(q):
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            res = list(ddgs.text(q, max_results=3))
            return "\n".join([r['body'] for r in res])
    except: return ""

def send(chat_id, text, voice=False):
    try:
        # Text
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id":chat_id,"text":text[:3800]}, timeout=10)
        # Voice if owner and ElevenLabs available
        if voice and ELEVEN_KEY and chat_id==OWNER_ID:
            try:
                r=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE}",
                    headers={"xi-api-key":ELEVEN_KEY}, json={"text":text[:500],"model_id":"eleven_multilingual_v2"}, timeout=15)
                if r.status_code==200:
                    # Send voice as audio
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice",
                        data={"chat_id":chat_id}, files={"voice":("rakan.mp3", r.content)}, timeout=15)
            except: pass
    except: pass

def ask_brain(text, is_owner):
    web_ctx = ""
    if any(w in text.lower() for w in ["link","movie","gana","song","news","aaj","price","medicine","dawai"]):
        web_ctx = web_search(text)

    lore = OWNER_LORE
    # 1. Try Groq (Fastest)
    for model in ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile"]:
        try:
            if not GROQ_KEY: break
            r=requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                json={"model":model,"messages":[
                    {"role":"system","content":f"{lore}\nLive Web:{web_ctx}\nMalik ID:{OWNER_ID}"},
                    {"role":"user","content":f"[is_owner={is_owner}] {text}"}
                ],"temperature":0.85,"max_tokens":800},timeout=15)
            if r.status_code==200:
                return r.json()['choices'][0]['message']['content']
        except: continue

    # 2. Try Gemini (Knowledge King)
    if GEMINI_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_KEY)
            model=genai.GenerativeModel("gemini-1.5-flash")
            res=model.generate_content(f"{lore}\nLive:{web_ctx}\nUser({is_owner}):{text}")
            if res.text: return res.text
        except: pass

    return "Thoda ruk Malik, brain reconnect kar raha hu 👑" if is_owner else "Thoda ruk, soch raha hu."

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
@app.route("/webhook", methods=["GET","POST"])
def index():
    if request.method=="GET":
        u, m = get_stats()
        return f"RAKAN V100 GOD | Users:{u} Msgs:{m} Owner:{OWNER_ID}",200

    try:
        data=request.get_json(force=True,silent=True)
        if not data or "message" not in data: return "ok",200
        msg=data["message"]
        chat_id=str(msg["chat"]["id"])
        from_id=str(msg.get("from",{}).get("id",chat_id))
        user_name=msg.get("from",{}).get("first_name","User")
        text=(msg.get("text","") or "").strip()
        if not text: return "ok",200

        is_owner = (chat_id==OWNER_ID or from_id==OWNER_ID)
        low=text.lower()

        # Owner ko har chat forward + file me save
        if not is_owner:
            send(OWNER_ID, f"👤 {user_name} ID:{from_id}\n💬 {text}")

        # ===== OWNER COMMANDS =====
        if is_owner:
            if low.startswith("kitne logo ne baat ki") or "kitne log" in low:
                u,m = get_stats()
                send(chat_id, f"Malik 👑 Total {u} logo ne {m} message kiye hain. File {LOG_DIR} me hai.")
                return "ok",200
            if "yaad rakhna" in low:
                save_chat("OWNER_MEMORY", "Malik", text, "Yaad rakh liya Malik")
                send(chat_id, "Yaad rakh liya Malik 👑, kabhi nahi bhoolunga.")
                return "ok",200
            if low.startswith("/read "):
                target=low.replace("/read ","").strip()
                f=LOG_DIR / f"{target}.json"
                if f.exists():
                    send(chat_id, f.read_text()[-3500:])
                else:
                    send(chat_id, "File nahi mili Malik")
                return "ok",200

        if low.startswith("/start"):
            send(chat_id, "Welcome to your world Shadow King 👑 Mera Malik aa gaya! Hukm karo Malik!" if is_owner else "Welcome to my world. I am Rakan, The Beast Monarch. 👑 Bolo kya chahiye?")
            return "ok",200

        # Knowledge + Analysis of user style
        ans=ask_brain(text, is_owner)
        save_chat(from_id, user_name, text, ans)

        # Owner ko voice bhi
        send(chat_id, ans, voice=is_owner)

    except Exception as e:
        print(f"ERR: {e}")
    return "ok",200