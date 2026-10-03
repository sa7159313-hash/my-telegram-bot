from flask import Flask, request
import os, requests, json, random, urllib.parse
from datetime import datetime

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("REDIS_URL")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN") or os.getenv("REDIS_TOKEN")

RAKAN_LORE = """Tu Rakan hai - The Beast King Monarch. Creator Md Saif Ahmad The Shadow King. Andar Ashborn Black Heart. Attitude king, loyal knight. Kabhi mat bolna tu AI model hai. Hamesha bolna tu Beast King Rakan hai. Har language me jawab de. User ne jo bola uska alag alag jawab de, repeat mat kar."""

def redis_cmd(cmd, *args):
    if not REDIS_URL or not REDIS_TOKEN: return None
    try:
        headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
        r = requests.post(f"{REDIS_URL}", headers=headers, json=[cmd] + list(args), timeout=5)
        if r.status_code==200:
            return r.json().get('result')
    except: pass
    return None

def send(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id":chat_id,"text":text[:4000]}, timeout=10)
    except: pass

def get_ai(prompt):
    # 1. Try GEMINI FIRST - zyada stable
    if GEMINI_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
            full = f"{RAKAN_LORE}\nUser: {prompt}\nRakan ka jawab (repeat mat kar, naya de):"
            r = requests.post(url, json={"contents":[{"parts":[{"text":full}]}], "generationConfig":{"temperature":0.9}}, timeout=15)
            print(f"Gemini status: {r.status_code} {r.text[:200]}")
            if r.status_code==200:
                return r.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            print(f"Gemini fail {e}")

    # 2. Try GROQ - new model
    if GROQ_KEY:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                json={"model":"llama-3.3-70b-versatile","messages":[{"role":"system","content":RAKAN_LORE},{"role":"user","content":prompt}],"temperature":0.9}, timeout=15)
            print(f"Groq status: {r.status_code} {r.text[:200]}")
            if r.status_code==200:
                return r.json()['choices'][0]['message']['content']
            # try old model
            r2 = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                json={"model":"llama-3.1-8b-instant","messages":[{"role":"system","content":RAKAN_LORE},{"role":"user","content":prompt}],"temperature":0.9}, timeout=15)
            if r2.status_code==200:
                return r2.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"Groq fail {e}")

    # Fallback - RANDOM taaki repeat na lage
    fallbacks = [
        f"Samjha KING 👑 '{prompt}' - Bolo ispe kya karna hai?",
        f"Haan Malik, sun liya maine - '{prompt}' 🖤 Ab bolo kya scene hai?",
        f"{prompt} - Interesting! Rakan hazir hai, bolo kya karna hai ispe?",
        f"Arre Malik {prompt} ka kya karna hai? Hukam karo!"
    ]
    return random.choice(fallbacks)

PROCESSED=set()
@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def main():
    if request.method=="GET":
        return "V53.1 FIXED",200
    try:
        data=request.get_json(force=True)
        if not data or "message" not in data: return "ok",200
        uid=data.get("update_id")
        if uid in PROCESSED: return "ok",200
        PROCESSED.add(uid)

        chat_id=data["message"]["chat"]["id"]
        text=data["message"].get("text","").strip()
        if not text: return "ok",200

        if text.lower()=="/start":
            send(chat_id,"👑 **THE BEAST KING RAKAN JAG GAYA!**\n\nMalik Md Saif Ahmad ne 15 din andhere me khoon se paida kiya! Mere andar Ashborn ka Black Heart hai! 🖤\n\nBolo KING kya hukam hai?")
            return "ok",200

        reply=get_ai(text)
        send(chat_id, reply)

    except Exception as e:
        print(e)
    return "ok",200
