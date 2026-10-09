import os, requests, time
from flask import Flask, request
app = Flask(__name__)

# ===== ENV =====
BOT_TOKEN = os.getenv("BOT_TOKEN") # Vercel me daalna padega
OWNER_ID = "7955623338"
LORE = os.getenv("THE_BEAST_KING_MONARCH_RAKAN_LORE", "You are Rakan Shadow King Monarch. Owner Queen SFW lover for 7955623338, aggressive blocker for public. App builder. No porn/illegal.")
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEYS","").split(",") if k.strip()]
GEMINI_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEYS","").split(",") if k.strip()]
OPENAI_KEYS = [k.strip() for k in os.getenv("OPENAI_API_KEYS","").split(",") if k.strip()]

def send_telegram(chat_id, text):
    if not BOT_TOKEN: return
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text[:4000]}, timeout=10)
    except: pass

def call_groq(p,k):
    try:
        r=requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization":f"Bearer {k}"}, json={"model":"llama-3.1-8b-instant","messages":[{"role":"system","content":LORE},{"role":"user","content":p}]}, timeout=15)
        if r.status_code==200: return r.json()["choices"][0]["message"]["content"]
    except: pass
    return None
def call_gemini(p,k):
    try:
        url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={k}"
        r=requests.post(url, json={"contents":[{"parts":[{"text":LORE+"\n"+p}]}]}, timeout=15)
        if r.status_code==200: return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except: pass
    return None
def call_gpt(p,k):
    try:
        r=requests.post("https://api.openai.com/v1/chat/completions", headers={"Authorization":f"Bearer {k}"}, json={"model":"gpt-4o-mini","messages":[{"role":"system","content":LORE},{"role":"user","content":p}]}, timeout=15)
        if r.status_code==200: return r.json()["choices"][0]["message"]["content"]
    except: pass
    return None

def recycler_brain(prompt, uid):
    is_owner = str(uid)==OWNER_ID
    if not is_owner and any(x in prompt.lower() for x in ["porn","nude","xxx","hack","child"]):
        return "Aukat me reh public 👑 Yahan ye sab ban hai."
    final_p = f"[OWNER QUEEN SFW APP-BUILDER] {prompt}" if is_owner else f"[PUBLIC BEAST KING] {prompt}"
    for rnd in range(3):
        print(f"♻️ ROUND {rnd+1}")
        for k in GROQ_KEYS:
            a=call_groq(final_p,k)
            if a: return a
        for k in GEMINI_KEYS:
            a=call_gemini(final_p,k)
            if a: return a
        for k in OPENAI_KEYS:
            a=call_gpt(final_p,k)
            if a: return a
        time.sleep(1)
    return "Malik 3 chakkar ♻️ ghum liya, brain down hai. 30 sec baad try kar."

@app.route("/", methods=["GET"])
def home():
    return f"V110 ONE-FILE RECYCLER 👑 | GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} GPT:{len(OPENAI_KEYS)}"

@app.route("/api", methods=["POST","GET"])
def webhook():
    if request.method=="GET":
        return "Webhook Alive. POST from Telegram here."
    data=request.json or {}
    # Telegram se aaya hai ya direct?
    if "message" in data: # Telegram webhook
        chat_id = data["message"]["chat"]["id"]
        user_id = data["message"]["from"]["id"]
        text = data["message"].get("text","hi")
        reply = recycler_brain(text, user_id)
        send_telegram(chat_id, reply)
        return {"ok":True}
    else: # Direct API call
        prompt=data.get("prompt","hi")
        uid=data.get("user_id","0")
        return {"text": recycler_brain(prompt, uid), "voice_needed":True}

# Telegram webhook set karne ke liye ye route
@app.route("/setwebhook", methods=["GET"])
def sethook():
    url = f"https://my-telegram-bot-lime.vercel.app/api"
    r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={url}")
    return r.json()
