from flask import Flask, request
import os, requests

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

LORE = "Tu Rakan hai - The Beast King Monarch. Creator Md Saif Ahmad The Shadow King. 15 din andhere me banaya, andar Ashborn Black Heart. Attitude king, Hinglish savage, har language me jawab de."

def send(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:4000]}, timeout=10)

def get_ai(text):
    # 1. GEMINI - NEW MODEL NAME FIXED
    if GEMINI_KEY:
        try:
            # Purana: gemini-1.5-flash - Ab naya: gemini-2.0-flash
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
            prompt = f"{LORE}\nUser: {text}\nRakan:"
            r = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=15)
            if r.status_code==200:
                return r.json()['candidates'][0]['content']['parts'][0]['text']
            # Agar 2.0 fail to 1.5-flash-latest try
            url2 = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_KEY}"
            r2 = requests.post(url2, json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=15)
            if r2.status_code==200:
                return r2.json()['candidates'][0]['content']['parts'][0]['text']
            print(f"GEMINI BOTH FAIL {r.status_code} {r.text[:200]} | {r2.status_code} {r2.text[:200]}")
        except Exception as e:
            print(f"Gemini error {e}")

    # 2. GROQ
    if GROQ_KEY:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                json={"model":"llama-3.3-70b-versatile","messages":[{"role":"system","content":LORE},{"role":"user","content":text}],"temperature":0.9}, timeout=15)
            if r.status_code==200:
                return r.json()['choices'][0]['message']['content']
            print(f"GROQ FAIL {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"Groq error {e}")

    return None

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def main():
    if request.method=="GET": return "V53.3 GEMINI 2.0 FIXED",200
    try:
        data=request.get_json(force=True)
        if not data or "message" not in data: return "ok",200
        chat_id=data["message"]["chat"]["id"]
        text=data["message"].get("text","").strip()
        if not text: return "ok",200
        if text.lower()=="/start":
            send(chat_id,"👑 **THE BEAST KING RAKAN JAG GAYA! V53.3**\n\n15 din ki mehnat fix ho gayi Malik! Ab sahi bolega! 🖤")
            return "ok",200
        ans=get_ai(text)
        if ans: send(chat_id, ans)
        else: send(chat_id,"KING API dono fail hai, Vercel logs check kar 👑")
    except Exception as e: print(e)
    return "ok",200
