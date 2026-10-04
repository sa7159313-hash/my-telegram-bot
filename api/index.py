from flask import Flask, request
import os, requests

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = str(os.getenv("OWNER_ID","")).strip()
LORE = os.getenv("THE_BEAST_KING_MONARCH_RAKAN_LORE","")
GROQ = os.getenv("GROQ_API_KEY")

def send(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text}, timeout=10)
    except: pass

def get_ai(txt):
    if not GROQ: return "Malik, Groq key nahi hai."
    try:
        r=requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ}"}, json={"model":"llama-3.1-8b-instant","messages":[{"role":"system","content":LORE},{"role":"user","content":txt}]}, timeout=15)
        if r.status_code==200:
            return r.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error: {e}"
    return "Bol Malik."

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
@app.route("/webhook", methods=["GET","POST"])
def main():
    if request.method=="GET":
        return "Rakan V63 Running @THE_SHADOW_KINGG"
    data=request.get_json(silent=True)
    if not data or "message" not in data:
        return "ok",200
    m=data["message"]; chat=m["chat"]["id"]; uid=str(m["from"]["id"]); text=m.get("text","").strip()
    if text=="/id":
        send(chat, f"Your ID: {uid}\nOwner ID: {OWNER_ID}\nMatch: {uid==OWNER_ID}\nUsername: @THE_SHADOW_KINGG")
        return "ok",200
    if uid==OWNER_ID:
        send(chat, get_ai(text))
    else:
        send(chat, get_ai(text))
    return "ok",200
