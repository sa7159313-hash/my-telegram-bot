from flask import Flask, request
import os, requests
app = Flask(__name__)
application = app

@app.route("/", methods=["GET"])
def home(): return "Rakan V14",200

@app.route("/api/index", methods=["GET","POST"])
def webhook():
    if request.method=="GET": return "Rakan V14",200
    try:
        data=request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok",200
        BOT=os.getenv("BOT_TOKEN","").strip()
        KEY=os.getenv("GEMINI_API_KEY","").strip()
        chat_id=str(data["message"]["chat"]["id"])
        text=data["message"].get("text","") or ""
        print(f"V14 IN:{text} KEY:{len(KEY)}")

        reply=None
        for model in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash-lite", "gemini-2.0-flash"]:
            url=f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={KEY}"
            payload={"contents":[{"parts":[{"text": f"You are Rakan Beast King, reply Hinglish short. User:{text}"}]}]}
            r=requests.post(url, json=payload, timeout=15)
            print(f"V14 {model} -> {r.status_code} {r.text[:500]}")
            if r.status_code==200:
                reply=r.json()["candidates"][0]["content"]["parts"][0]["text"]
                break

        if not reply:
            reply="Ji Malik, Rakan hazir hai, hukam karo 🔥"

        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", json={"chat_id":chat_id,"text":reply[:4000]}, timeout=10)
        return "ok",200
    except Exception as e:
        print(f"V14 CRASH {e}")
        return "ok",200
