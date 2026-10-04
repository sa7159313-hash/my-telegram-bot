from flask import Flask, request
import os, requests
app = Flask(__name__)

BOT_TOKEN=os.getenv("BOT_TOKEN")
OWNER_ID=str(os.getenv("OWNER_ID","")).strip()
LORE=os.getenv("THE_BEAST_KING_MONARCH_RAKAN_LORE","Tu Rakan hai, Malik @THE_SHADOW_KINGG ka beast king.")
GROQ=os.getenv("GROQ_API_KEY")
GEMINI=os.getenv("GEMINI_API_KEY")

def send(cid, txt):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":txt}, timeout=10)
    except: pass

def get_ai(msg):
    if GROQ:
        try:
            r=requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ.strip()}","Content-Type":"application/json"},
            json={"model":"llama3-8b-8192","messages":[{"role":"system","content":LORE},{"role":"user","content":msg}],"temperature":0.9,"max_tokens":600}, timeout=20)
            if r.status_code==200:
                return r.json()['choices'][0]['message']['content']
            else:
                print(f"GROQ FAIL: {r.text}")
        except Exception as e:
            print(f"GROQ EXC: {e}")
    if GEMINI:
        try:
            r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI.strip()}", json={"contents":[{"parts":[{"text":f"{LORE}\nMalik: {msg}"}]}]}, timeout=20)
            if r.status_code==200:
                return r.json()['candidates'][0]['content']['parts'][0]['text']
        except: pass
    return "Malik, key check kar, Groq error aa raha hai."

# PURANA FIX + NAYA FIX - 3 route ek saath
@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
@app.route("/webhook", methods=["GET","POST"])
def main():
    if request.method=="GET":
        return f"Rakan V64.1 Live | Owner:{OWNER_ID} | Groq:{bool(GROQ)} | Gemini:{bool(GEMINI)}"
    data=request.get_json(silent=True)
    if not data or "message" not in data: return "ok",200
    m=data["message"]; chat=m["chat"]["id"]; uid=str(m["from"]["id"]); text=m.get("text","").strip()
    if not text: return "ok",200
    if text.lower()=="/id":
        send(chat, f"ID: {uid}\nOwner: {OWNER_ID}\nMatch: {uid==OWNER_ID}\n@THE_SHADOW_KINGG\nGroq:{bool(GROQ)}")
        return "ok",200
    send(chat, get_ai(text))
    return "ok",200
