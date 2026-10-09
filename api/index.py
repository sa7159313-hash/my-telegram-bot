import os
import random
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- KEY HANDLER - KEY ho ya KEYS dono pakdega ---
def get_keys(*names):
    keys = []
    for name in names:
        val = os.environ.get(name, "")
        if val:
            # comma ya newline se multiple keys ho to split kar dega
            for k in val.replace("\n", ",").split(","):
                k = k.strip()
                if k and k not in keys:
                    keys.append(k)
    return keys

GROQ_KEYS = get_keys("GROQ_API_KEYS", "GROQ_API_KEY", "GROQ")
GEMINI_KEYS = get_keys("GEMINI_API_KEYS", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI")
OPENAI_KEYS = get_keys("OPENAI_API_KEYS", "OPENAI_API_KEY", "OPENAI")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_TOKEN = BOT_TOKEN.strip()

REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "") or os.environ.get("REDIS_URL", "")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")

print(f"### V115 BOOT ### GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)} BOT:{'OK' if BOT_TOKEN else 'NO'} REDIS:{'OK' if REDIS_URL else 'NO'}")

# --- REDIS ---
def redis_get(key):
    try:
        if not REDIS_URL or not REDIS_TOKEN: return None
        r = requests.post(f"{REDIS_URL}/get/{key}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("result")
    except: pass
    return None

def redis_set(key, val):
    try:
        if not REDIS_URL or not REDIS_TOKEN: return
        requests.post(f"{REDIS_URL}/set/{key}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, json={"value": val}, timeout=5)
    except: pass

# --- AI ENGINES ---
def ask_groq(prompt):
    if not GROQ_KEYS: return None
    for api_key in GROQ_KEYS:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": 500},
                timeout=15)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except: continue
    return None

def ask_gemini(prompt):
    if not GEMINI_KEYS: return None
    for api_key in GEMINI_KEYS:
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=15)
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except: continue
    return None

def ask_openai(prompt):
    if not OPENAI_KEYS: return None
    for api_key in OPENAI_KEYS:
        try:
            r = requests.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}], "max_tokens": 500},
                timeout=15)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except: continue
    return None

def get_ai_reply(prompt):
    # Round 1,2,3 try
    ans = ask_groq(prompt)
    if ans: return ans
    ans = ask_gemini(prompt)
    if ans: return ans
    ans = ask_openai(prompt)
    if ans: return ans
    return None

# --- ROUTES ---
@app.route("/", methods=["GET"])
def home():
    return f"V115 BEAST KING FULL 👑 | GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)} BOT:{'OK' if BOT_TOKEN else 'NO'} | KEY/KEYS both supported"

@app.route("/api", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        if not data or "message" not in data: return jsonify({"ok": True})
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        if not text: return jsonify({"ok": True})

        if text.startswith("/start"):
            reply = f"Monarch Rakan BEAST KING 👑 is Online!\nGROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)}"
        else:
            # 3 chakkar logic
            ai_text = get_ai_reply(text)
            if not ai_text:
                if len(GROQ_KEYS)==0 and len(GEMINI_KEYS)==0:
                    reply = f"Malik keys khatam ho gayi 😭 Vercel me GROQ_API_KEYS aur GEMINI_API_KEYS check kar, nayi keys daal aur redeploy kar."
                elif len(GROQ_KEYS)>0 or len(GEMINI_KEYS)>0:
                    reply = f"Malik saare servers fail 😭\nGROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)}\nKey expire ya limit check karo."
                else:
                    reply = "Malik 3 chakkar ♻️ ghum liya, brain down hai. 30 sec baad try kar."
            else:
                reply = ai_text

        # Send to Telegram
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json={"chat_id": chat_id, "text": reply}, timeout=10)
        return jsonify({"ok": True})
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"ok": True})

if __name__ == "__main__":
    app.run()
