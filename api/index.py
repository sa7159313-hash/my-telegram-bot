import os, requests
from flask import Flask, request, jsonify
app = Flask(__name__)

def get_keys(*names):
    keys=[]
    for n in names:
        v=os.environ.get(n,"")
        if v:
            for k in v.replace("\n",",").split(","):
                k=k.strip()
                if k and k not in keys: keys.append(k)
    return keys

GROQ_KEYS=get_keys("GROQ_API_KEYS","GROQ_API_KEY","GROQ")
GEMINI_KEYS=get_keys("GEMINI_API_KEYS","GEMINI_API_KEY","GOOGLE_API_KEY","GEMINI")
OPENAI_KEYS=get_keys("OPENAI_API_KEYS","OPENAI_API_KEY","OPENAI")
BOT_TOKEN=os.environ.get("BOT_TOKEN","").strip()

print(f"### V117 FINAL ### GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)}")

def ask_groq(prompt):
    if not GROQ_KEYS: return None
    # Naye models Aug 2026 ke baad ke
    models=["openai/gpt-oss-20b","openai/gpt-oss-120b","meta-llama/llama-4-scout-17b-16e-instruct","qwen/qwen3-32b","llama-3.3-70b-versatile","llama-3.1-8b-instant"]
    for key in GROQ_KEYS:
        for model in models:
            try:
                r=requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                    json={"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":600},
                    timeout=20)
                if r.status_code==200:
                    print(f"GROQ OK with {model}")
                    return r.json()["choices"][0]["message"]["content"]
                print(f"GROQ {r.status_code} model:{model} {r.text[:200]}")
            except Exception as e:
                print(f"GROQ ERR {e}"); continue
    return None

def ask_gemini(prompt):
    if not GEMINI_KEYS: return None
    for key in GEMINI_KEYS:
        try:
            r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={key}",
                headers={"Content-Type":"application/json"},
                json={"contents":[{"parts":[{"text":prompt}]}]},timeout=20)
            if r.status_code==200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            print(f"GEM {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"GEM ERR {e}"); continue
    return None

def ask_openai(prompt):
    if not OPENAI_KEYS: return None
    for key in OPENAI_KEYS:
        try:
            r=requests.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                json={"model":"gpt-3.5-turbo","messages":[{"role":"user","content":prompt}],"max_tokens":600},timeout=20)
            if r.status_code==200:
                return r.json()["choices"][0]["message"]["content"]
        except: continue
    return None

def get_ai_reply(p):
    a=ask_groq(p)
    if a: return a
    a=ask_gemini(p)
    if a: return a
    a=ask_openai(p)
    if a: return a
    return None

@app.route("/",methods=["GET"])
def home():
    return f"V117 BEAST KING FINAL 👑 GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)}"

@app.route("/api",methods=["POST"])
def webhook():
    try:
        data=request.get_json(force=True)
        if not data or "message" not in data: return jsonify({"ok":True})
        msg=data["message"]; chat_id=msg["chat"]["id"]; text=msg.get("text","")
        if not text: return jsonify({"ok":True})
        if text.lower().startswith("/start"):
            reply=f"Monarch Rakan BEAST KING V117 👑 Online!\nGROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)}"
        else:
            ai=get_ai_reply(text)
            reply=ai if ai else f"Malik saare servers fail 😭 GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} OPENAI:{len(OPENAI_KEYS)} Log check karo."
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json={"chat_id":chat_id,"text":reply},timeout=10)
        return jsonify({"ok":True})
    except Exception as e:
        print(f"ERR {e}"); return jsonify({"ok":True})
