import os, json, requests, time
from flask import Flask, request

app = Flask(__name__)

# ===== SMART ENV LOADER - KEY ho ya KEYS dono chalega =====
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

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_API_KEY") or ""
GROQ_KEYS = get_keys("GROQ_API_KEYS", "GROQ_API_KEY", "GROQ", "GROQ_KEY")
GEMINI_KEYS = get_keys("GEMINI_API_KEYS", "GEMINI_API_KEY", "GEMINI", "GOOGLE_API_KEY")
OPENAI_KEYS = get_keys("OPENAI_API_KEYS", "OPENAI_API_KEY", "OPENAI")
LORE = os.getenv("THE_BEAST_KING_MONARCH_RAKAN_LORE") or os.getenv("LORE") or "You are Rakan - The Beast King Monarch, savage, loyal to owner 7955623338, talk in Hinglish with 👑 emoji"

print(f"### ENV LOADED ### GROQ:{len(GROQ_KEYS)} GEMINI:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)} BOT:{'YES' if BOT_TOKEN else 'NO'}")

def send_tg(chat_id, text):
    if not BOT_TOKEN: return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text[:4096], "parse_mode":"Markdown"}, timeout=10)
    except Exception as e:
        print(f"SEND_TG_ERR {e}")

def call_groq(prompt, key):
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile", "messages":[{"role":"system","content":LORE},{"role":"user","content":prompt}], "temperature":0.8, "max_tokens":1000},
            timeout=25)
        print(f"GROQ_RESP {r.status_code} {r.text[:400]}")
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"GROQ_ERR {e}")
    return None

def call_gemini(prompt, key):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        r = requests.post(url, json={"contents":[{"parts":[{"text": LORE + "\nUser: " + prompt}]}]}, timeout=25)
        print(f"GEMINI_RESP {r.status_code} {r.text[:400]}")
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"GEMINI_ERR {e}")
    return None

def call_openai(prompt, key):
    try:
        r = requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model":"gpt-4o-mini", "messages":[{"role":"system","content":LORE},{"role":"user","content":prompt}]},
            timeout=25)
        print(f"OPENAI_RESP {r.status_code}")
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"OPENAI_ERR {e}")
    return None

@app.route("/", methods=["GET"])
def home():
    return f"V114 BEAST KING LIVE 👑 | GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)} BOT:{'OK' if BOT_TOKEN else 'MISSING'} | KEY/KEYS both supported"

@app.route("/api", methods=["GET","POST"])
def webhook():
    if request.method == "GET":
        return "Bot is running. POST Telegram updates here."

    data = request.json or {}
    print(f"INCOMING {json.dumps(data)[:500]}")

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text","hi")
        user_id = str(msg["from"]["id"])

        # Owner check
        is_owner = "7955623338" in user_id or "7955623338" in LORE

        # Try GROQ first
        answer = None
        for k in GROQ_KEYS:
            answer = call_groq(text, k)
            if answer: break

        # Then Gemini
        if not answer:
            for k in GEMINI_KEYS:
                answer = call_gemini(text, k)
                if answer: break

        # Then OpenAI
        if not answer:
            for k in OPENAI_KEYS:
                answer = call_openai(text, k)
                if answer: break

        if answer:
            if is_owner:
                answer = f"Ji Malik 👑 {answer}"
            send_tg(chat_id, answer)
        else:
            send_tg(chat_id, f"Malik sab servers fail ho gaye 👑\nGROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)}\nVercel ENV check karo, key expire to nahi?")

    return {"ok": True}

@app.route("/setwebhook", methods=["GET"])
def sethook():
    if not BOT_TOKEN: return "BOT_TOKEN missing"
    url = f"https://my-telegram-bot-lime.vercel.app/api"
    r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={url}")
    return r.json()

if __name__ == "__main__":
    app.run()
