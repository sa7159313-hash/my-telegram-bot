import os, json, requests, traceback
from flask import Flask, request
from google import genai
app = Flask(__name__)

def tg_send(token, chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id":chat_id,"text":text[:4000]}, timeout=15)
    except: pass

@app.route("/api/index", methods=["POST"])
def webhook():
    try:
        data=request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok",200
        BOT=os.getenv("BOT_TOKEN","").strip()
        KEY=os.getenv("GEMINI_API_KEY","").strip()
        OWNER=str(os.getenv("OWNER_ID","")).strip()
        msg=data["message"]
        chat_id=str(msg["chat"]["id"])
        text=msg.get("text","") or ""
        print(f"INCOMING {text}")

        # FIXED GENAI CODE
        try:
            client = genai.Client(api_key=KEY)
            prompt = f"You are Rakan, Beast Monarch King. Owner {OWNER} ko 'Ji Malik 🔥' bolo. Short Hinglish dark king style. Army: Igris, Beru, Jima, Kaisel, Bellion, Iron, Tusk, Greed. User: {text} Reply:"
            res = client.models.generate_content(model="gemini-2.0-flash-lite", contents=prompt)
            reply = res.text.strip() if res.text else "Ji Malik bolo? 🔥"
            print(f"GEMINI_OK {reply[:100]}")
        except Exception as e:
            print(f"GEMINI_ERROR {e}\n{traceback.format_exc()}")
            # KEY INVALID HAI TOH YE AAYEGA - NAYA KEY BANA
            if "API_KEY_INVALID" in str(e) or "403" in str(e):
                reply = "Malik Gemini key invalid hai, naya key banao aistudio.google.com se 🔥"
            else:
                reply = f"Ji Malik bolo? 🔥 {text}"

        tg_send(BOT, chat_id, reply)
        return "ok",200
    except Exception as e:
        print(f"CRASH {e}")
        return "ok",200

@app.route("/", methods=["GET"])
def home(): return "Rakan V7 Live - genai fixed",200
