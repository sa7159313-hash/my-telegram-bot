import os, requests, time
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN=os.getenv("BOT_TOKEN")
OWNER_ID="7955623338"
LORE=os.getenv("THE_BEAST_KING_MONARCH_RAKAN_LORE","You are Rakan Shadow King Monarch.")
GROQ_KEYS=[k.strip() for k in os.getenv("GROQ_API_KEYS","").split(",") if k.strip()]
GEMINI_KEYS=[k.strip() for k in os.getenv("GEMINI_API_KEYS","").split(",") if k.strip()]
OPENAI_KEYS=[k.strip() for k in os.getenv("OPENAI_API_KEYS","").split(",") if k.strip()]

def send_tg(chat_id,text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:4000]}, timeout=10)
    except: pass

def call_groq(p,k):
    try:
        r=requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization":f"Bearer {k}"}, json={"model":"llama-3.3-70b-versatile","messages":[{"role":"system","content":LORE},{"role":"user","content":p}]}, timeout=20)
        print(f"GROQ {r.status_code} {r.text[:200]}")
        if r.status_code==200: return r.json()["choices"][0]["message"]["content"]
    except Exception as e: print(f"GROQ ERR {e}")
    return None

def call_gemini(p,k):
    try:
        url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={k}"
        r=requests.post(url, json={"contents":[{"parts":[{"text":LORE+"\n"+p}]}]}, timeout=20)
        print(f"GEMINI {r.status_code} {r.text[:200]}")
        if r.status_code==200: return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e: print(f"GEM ERR {e}")
    return None

def recycler(prompt, uid):
    final = f"[OWNER] {prompt}" if str(uid)==OWNER_ID else prompt
    for rnd in range(2):
        for k in GROQ_KEYS:
            a=call_groq(final,k)
            if a: return a
        for k in GEMINI_KEYS:
            a=call_gemini(final,k)
            if a: return a
    return "Malik keys khatam ho gayi 👑 Vercel me GROQ_API_KEYS aur GEMINI_API_KEYS check kar, nayi keys daal aur redeploy kar."

@app.route("/", methods=["GET"])
def home(): return f"V111 LIVE | GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)}"

@app.route("/api", methods=["POST","GET"])
def api():
    if request.method=="GET": return "POST here"
    data=request.json or {}
    if "message" in data:
        chat=data["message"]["chat"]["id"]; uid=data["message"]["from"]["id"]; txt=data["message"].get("text","hi")
        ans=recycler(txt, uid); send_tg(chat, ans); return {"ok":True}
    return {"text":recycler(data.get("prompt","hi"), data.get("user_id","0"))}

@app.route("/setwebhook")
def sethook():
    r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url=https://my-telegram-bot-lime.vercel.app/api")
    return r.json()
