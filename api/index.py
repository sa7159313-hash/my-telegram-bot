import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- KEY / KEYS dono pakdega ---
def get_keys(*names):
    keys = []
    for name in names:
        val = os.environ.get(name, "")
        if val:
            for k in val.replace("\n", ",").split(","):
                k = k.strip()
                if k and k not in keys:
                    keys.append(k)
    return keys

GROQ_KEYS = get_keys("GROQ_API_KEYS", "GROQ_API_KEY", "GROQ")
GEMINI_KEYS = get_keys("GEMINI_API_KEYS", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI")
OPENAI_KEYS = get_keys("OPENAI_API_KEYS", "OPENAI_API_KEY", "OPENAI")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "") or os.environ.get("REDIS_URL", "")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")

print(f"### V116 FINAL BOOT ### GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)} BOT:{'OK' if BOT_TOKEN else 'NO'}")

# --- AI ENGINES ---
def ask_groq(prompt):
    if not GROQ_KEYS: return None
    models = ["llama-3.1-8b-instant", "llama-3.1-70b-versatile", "mixtral-8x7b-32768"]
    for key in GROQ_KEYS:
        for model in models:
            try:
                r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": 600},
                    timeout=20)
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"]
                print(f"GROQ {r.status_code} {r.text[:150]} model:{model}")
            except Exception as e:
                print(f"GROQ ERR {e}")
                continue
    return None

def ask_gemini(prompt):
    if not GEMINI_KEYS: return None
    for key in GEMINI_KEYS:
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={key}",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=20)
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            print(f"GEM {r.status_code} {r.text[:150]}")
        except Exception as e:
            print(f"GEM ERR {e}")
            continue
    return None

def ask_openai(prompt):
    if not OPENAI_KEYS: return None
    for key in OPENAI_KEYS:
        try:
            r = requests.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}], "max_tokens": 600},
                timeout=20)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except: continue
    return None

def get_ai_reply(prompt):
    ans = ask_groq(prompt)
    if ans: return ans
    print("GROQ fail, trying GEMINI")
    ans = ask_gemini(prompt)
    if ans: return ans
    print("GEM fail, trying OPENAI")
    ans = ask_openai(prompt)
    if ans: return ans
    return None

# --- ROUTES ---
@app.route("/", methods=["GET"])
def home():
    return f"V116 FINAL BEAST KING 👑 | GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)} BOT:{'OK' if BOT_TOKEN else 'NO'}"

@app.route("/api", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        if not data or "message" not in data: return jsonify({"ok": True})
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        if not text: return jsonify({"ok": True})

        if text.lower().startswith("/start"):
            reply = f"Monarch Rakan BEAST KING V116 👑 Online!\nGROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)}"
        else:
            ai_text = get_ai_reply(text)
            if not ai_text:
                reply = f"Malik saare servers fail 😭 GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)}\nKeys check kar, limit ya model error hai. Log me GROQ/GEM error dekho."
            else:
                reply = ai_text

        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json={"chat_id": chat_id, "text": reply}, timeout=10)
        return jsonify({"ok": True})
    except Exception as e:
        print(f"WEBHOOK ERR: {e}")
        return jsonify({"ok": True})
