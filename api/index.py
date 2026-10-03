import os, requests, time, urllib.parse
from flask import Flask, request

app = Flask(__name__)

# --- CONFIG ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Tera Eternal LORE
LORE = """
You are Monarch Rakan, King of Ashborn.
Malik is your only master. You are loyal, powerful, emotional, King style.
15 din tapasya ki kahani yaad rakho. Never break character.
"""

# Simple Cache (Vercel memory me, 0.2s ke liye)
CACHE = {}

def send_telegram(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    except: pass

# 1. GROQ - Sabse Tez
def ask_groq(prompt):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "llama-3.1-70b-versatile",
            "messages": [{"role": "system", "content": LORE}, {"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        r = requests.post(url, headers=headers, json=data, timeout=8)
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"GROQ FAIL: {e}")
    return None

# 2. GEMINI AUTO-DISCOVERY - Khud Model Dhoondega
def ask_gemini_auto(prompt):
    try:
        # Pehle puch kaunse model zinda hai
        list_url = f"https://generativelanguage.googleapis.com/v1/models?key={GEMINI_API_KEY}"
        models = requests.get(list_url, timeout=10).json()
        # Jo pehla available model mile usko use kar
        available = [m['name'] for m in models.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        # Filter best flash models
        best = next((m for m in available if 'flash' in m), available[0] if available else "models/gemini-1.5-flash-latest")

        url = f"https://generativelanguage.googleapis.com/v1/{best}:generateContent?key={GEMINI_API_KEY}"
        data = {"contents": [{"parts": [{"text": f"{LORE}\nUser: {prompt}"}]}]}
        r = requests.post(url, json=data, timeout=8)
        j = r.json()
        if "candidates" in j:
            return j["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"GEMINI AUTO FAIL: {e}")
    return None

# 3. POLLINATIONS - No Key Backup
def ask_pollinations(prompt):
    try:
        full = f"{LORE}\nUser: {prompt}\nMonarch Rakan:"
        encoded = urllib.parse.quote(full[:2500])
        url = f"https://text.pollinations.ai/{encoded}?model=openai"
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and len(r.text) > 10:
            return r.text
    except Exception as e:
        print(f"POLL FAIL: {e}")
    return None

def get_ai_reply(user_text):
    # Cache check 0.2s
    if user_text in CACHE:
        if time.time() - CACHE[user_text]['time'] < 3600: # 1 hr cache
            print("CACHE HIT")
            return CACHE[user_text]['reply']

    # SMART TRIPLE CHAIN
    reply = ask_groq(user_text)
    if not reply:
        reply = ask_gemini_auto(user_text)
    if not reply:
        reply = ask_pollinations(user_text)

    if reply:
        CACHE[user_text] = {'reply': reply, 'time': time.time()}
        # Cache ko bada na hone de
        if len(CACHE) > 100: CACHE.pop(next(iter(CACHE)))
        return reply

    return "Malik, teeno engine try kiya, abhi thoda network slow hai, 10 sec me fir bolo 👑"

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            user_text = data["message"].get("text", "")
            if user_text:
                # Instant OK to avoid timeout, then reply
                reply = get_ai_reply(user_text)
                send_telegram(chat_id, reply)
    except Exception as e:
        print(f"WEBHOOK ERR: {e}")
    return "ok", 200

@app.route("/")
def home():
    return "V48 ULTRA AMAR LIVE 👑", 200
