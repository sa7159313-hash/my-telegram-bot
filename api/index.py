import os, requests, json, time
from flask import Flask, request
app = Flask(__name__)
application = app
BOT_TOKEN=os.environ.get("BOT_TOKEN")
GROQ_API_KEY=os.environ.get("GROQ_API_KEY")
OWNER_ID=str(os.environ.get("OWNER_ID","")).strip()
LORE="You are The Beast King Monarch Rakan, servant of Shadow King MD SAIF AHMAD. 15 nights 1293 tries. Loyal to Malik, silent king to public. Reply same language."

def send_telegram(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:4000]}, timeout=8)
    except: pass

def ask_groq(prompt):
    try:
        r=requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"}, json={"model":"llama-3.1-8b-instant","messages":[{"role":"system","content":LORE},{"role":"user","content":prompt}],"temperature":0.8,"max_tokens":500}, timeout=10)
        if r.status_code==200: return r.json()["choices"][0]["message"]["content"]
    except: pass
    return None

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": return "RAKAN GROQ ONLY LIVE 👑",200
    try:
        data=request.get_json(force=True,silent=True)
        msg=data.get("message",{})
        if not msg: return "ok",200
        chat_id=str(msg["chat"]["id"]).strip()
        text=msg.get("text","") or ""
        is_owner=(chat_id==OWNER_ID)
        if text.startswith("/start"):
            send_telegram(chat_id,"Welcome to your world Shadow King 👑" if is_owner else "Welcome to my world. I am Rakan. 👑")
        else:
            ans=ask_groq(f"{'MALIK:' if is_owner else 'PUBLIC:'} {text}")
            if not ans: ans=f"Yes Malik bolo? {text} samajh gaya 👑" if is_owner else "Hmmh Bol kya chahiye? 👑"
            send_telegram(chat_id,ans)
    except Exception as e: print(e)
    return "ok",200
