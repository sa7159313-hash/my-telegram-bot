import os, json, requests, random, time
from flask import Flask, request

app = Flask(__name__)

# ========== SMART LOADER - KEY / KEYS SAB CHALEGA ==========
def get_keys(*names):
    all_keys = []
    for name in names:
        val = os.getenv(name, "")
        if val:
            for k in val.split(","):
                k = k.strip()
                if k and k not in all_keys:
                    all_keys.append(k)
    return all_keys

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or ""
GROQ_KEYS = get_keys("GROQ_API_KEYS","GROQ_API_KEY","GROQ")
GEMINI_KEYS = get_keys("GEMINI_API_KEYS","GEMINI_API_KEY","GOOGLE_API_KEY","GEMINI")
OPENAI_KEYS = get_keys("OPENAI_API_KEYS","OPENAI_API_KEY","OPENAI")
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVENLABS_API_KEYS") or ""
ELEVEN_MALE = os.getenv("ELEVEN_MALE_VOICE") or os.getenv("ELEVEN_MALE_VOICE_ID") or ""
ELEVEN_FEMALE = os.getenv("ELEVEN_FEMALE_VOICE") or ""
UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL") or ""
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN") or ""
LORE = os.getenv("THE_BEAST_KING_MONARCH_RAKAN_LORE") or "You are RAKAN - The Beast King Monarch. You are savage, dominant, powerful, but loyal and soft for your owner 7955623338 (Malik). Talk in Hinglish, use 👑 emoji, roast others but respect owner. Never break character."

print(f"### V115 BOOT ### GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)} BOT:{'OK' if BOT_TOKEN else 'NO'} REDIS:{'OK' if UPSTASH_URL else 'NO'}")

# ========== REDIS MEMORY ==========
def redis_get(chat_id):
    if not UPSTASH_URL or not UPSTASH_TOKEN: return []
    try:
        r = requests.get(f"{UPSTASH_URL}/get/{chat_id}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=5)
        if r.status_code==200 and r.json().get("result"):
            return json.loads(r.json()["result"])
    except: pass
    return []

def redis_set(chat_id, history):
    if not UPSTASH_URL or not UPSTASH_TOKEN: return
    try:
        # last 10 messages only
        history = history[-10:]
        requests.get(f"{UPSTASH_URL}/set/{chat_id}/{json.dumps(history)}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=5)
    except: pass

# ========== TG SEND ==========
def send_tg(chat_id, text, reply_to=None):
    if not BOT_TOKEN: return
    try:
        payload = {"chat_id": chat_id, "text": text[:4096]}
        if reply_to: payload["reply_to_message_id"] = reply_to
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        print(f"SEND_ERR {e}")

# ========== AI CALLS ==========
def call_groq(prompt, history, key):
    try:
        messages = [{"role":"system","content":LORE}]
        for h in history[-6:]:
            messages.append(h)
        messages.append({"role":"user","content":prompt})
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model":"llama-3.3-70b-versatile","messages":messages,"temperature":0.85,"max_tokens":1200},
            timeout=25)
        print(f"GROQ {r.status_code} {r.text[:300]}")
        if r.status_code==200:
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e: print(f"GROQ_ERR {e}")
    return None

def call_gemini(prompt, history, key):
    try:
        # gemini me history string bana dete hain
        full = LORE + "\n"
        for h in history[-4:]:
            full += f"{h['role']}: {h['content']}\n"
        full += f"user: {prompt}"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        r = requests.post(url, json={"contents":[{"parts":[{"text": full}]}]}, timeout=25)
        print(f"GEMINI {r.status_code} {r.text[:300]}")
        if r.status_code==200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e: print(f"GEMINI_ERR {e}")
    return None

def call_openai(prompt, history, key):
    try:
        messages = [{"role":"system","content":LORE}]
        for h in history[-6:]: messages.append(h)
        messages.append({"role":"user","content":prompt})
        r = requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model":"gpt-4o-mini","messages":messages},
            timeout=25)
        print(f"OPENAI {r.status_code}")
        if r.status_code==200:
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e: print(f"OPENAI_ERR {e}")
    return None

# ========== MAIN WEBHOOK ==========
@app.route("/", methods=["GET"])
def home():
    return f"V115 BEAST KING FULL 👑 | GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)} BOT:{'OK' if BOT_TOKEN else 'NO'} REDIS:{'OK' if UPSTASH_URL else 'NO'} | All KEY/KEYS supported"

@app.route("/api", methods=["GET","POST"])
def api():
    if request.method=="GET":
        return "POST Telegram updates here"

    data = request.json or {}
    if "message" not in data: return {"ok":True}

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text","")
    if not text: return {"ok":True}
    user_id = str(msg["from"]["id"])
    is_owner = "7955623338" in user_id

    # commands
    if text.startswith("/start"):
        send_tg(chat_id, "Aagaya hu Malik 👑\nBeast King Rakan live hai. Bolo kya kaam hai?" if is_owner else "Beast King Rakan live hai 👑 Bolo kya chahiye?")
        return {"ok":True}

    history = redis_get(f"rakan:{chat_id}")
    answer = None

    # ROUND 1 - GROQ
    for k in GROQ_KEYS:
        answer = call_groq(text, history, k)
        if answer: break

    # ROUND 2 - GEMINI
    if not answer:
        for k in GEMINI_KEYS:
            answer = call_gemini(text, history, k)
            if answer: break

    # ROUND 3 - OPENAI
    if not answer:
        for k in OPENAI_KEYS:
            answer = call_openai(text, history, k)
            if answer: break

    if answer:
        if is_owner and not answer.startswith("Ji Malik"):
            answer = f"Ji Malik 👑 {answer}"
        send_tg(chat_id, answer)
        # save memory
        history.append({"role":"user","content":text})
        history.append({"role":"assistant","content":answer})
        redis_set(f"rakan:{chat_id}", history)
    else:
        send_tg(chat_id, f"Malik saare servers fail 👑\nGROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)}\nKey expire ya limit check karo.")

    return {"ok":True}

@app.route("/setwebhook")
def sethook():
    if not BOT_TOKEN: return "BOT_TOKEN missing"
    r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url=https://my-telegram-bot-lime.vercel.app/api")
    return r.json()
