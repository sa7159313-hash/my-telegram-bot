import os, requests, time
from flask import Flask, request
app = Flask(__name__)

# ========= CONFIG =========
OWNER_ID = "7955623338"
LORE = os.getenv("THE_BEAST_KING_MONARCH_RAKAN_LORE", "You are Rakan, The Beast King Monarch. Aggressive for public, caring SFW Queen for owner 7955623338. You can build apps, websites, games. No porn, no hacking, no illegal.")
GROQ_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEYS","").split(",") if k.strip()]
GEMINI_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEYS","").split(",") if k.strip()]
OPENAI_KEYS = [k.strip() for k in os.getenv("OPENAI_API_KEYS","").split(",") if k.strip()]

# ========= BRAIN CALLERS =========
def call_groq(p, k):
    try:
        r=requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {k}"},
            json={"model":"llama-3.1-8b-instant","messages":[{"role":"system","content":LORE},{"role":"user","content":p}]}, timeout=15)
        if r.status_code==200: return r.json()["choices"][0]["message"]["content"]
    except Exception as e: print(f"GROQ FAIL {e}")
    return None

def call_gemini(p, k):
    try:
        url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={k}"
        r=requests.post(url, json={"contents":[{"parts":[{"text": LORE+"\nUser: "+p}]}]}, timeout=15)
        if r.status_code==200: return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e: print(f"GEM FAIL {e}")
    return None

def call_gpt(p, k):
    try:
        r=requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization":f"Bearer {k}"},
            json={"model":"gpt-4o-mini","messages":[{"role":"system","content":LORE},{"role":"user","content":p}]}, timeout=15)
        if r.status_code==200: return r.json()["choices"][0]["message"]["content"]
    except Exception as e: print(f"GPT FAIL {e}")
    return None

# ========= ♻️ RECYCLER BRAIN =========
def recycler_brain(prompt, user_id):
    is_owner = str(user_id) == OWNER_ID

    # BLOCK SYSTEM
    bad = ["porn", "nude", "xxx", "hack", "termux", "child"]
    if not is_owner and any(x in prompt.lower() for x in bad):
        return "Aukat me reh public, ye Rakan ka darbar hai. Hacking/porn yahan ban hai. 👑"

    # PROMPT FINAL
    if is_owner:
        final_p = f"[OWNER MODE ON: ID {OWNER_ID} -> You are SFW Queen, soft, caring, romantic without porn, plus you are App Builder. Build full code if user asks app/website/game. Be loving. No NSFW.] User: {prompt}"
    else:
        final_p = f"[PUBLIC MODE: Aggressive Beast King, roast if needed, block illegal. App builder only hint, full code only for owner.] User: {prompt}"

    # 3 CHAKKAR RECYCLE LOOP
    for rnd in range(3):
        print(f"♻️ RECYCLE ROUND {rnd+1} | GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} GPT:{len(OPENAI_KEYS)}")
        for k in GROQ_KEYS:
            ans=call_groq(final_p, k)
            if ans: return ans
        for k in GEMINI_KEYS:
            ans=call_gemini(final_p, k)
            if ans: return ans
        for k in OPENAI_KEYS:
            ans=call_gpt(final_p, k)
            if ans: return ans
        time.sleep(1) # 1 sec ruk ke wapas groq

    return "Malik ♻️ 3 chakkar ghum liya, teeno brain down hai. Vercel ENV me keys check karo, 30 sec baad try karna."

# ========= ROUTES =========
@app.route("/", methods=["GET"])
def home():
    return f"Rakan V109 RECYCLER 👑♻️ | GROQ:{len(GROQ_KEYS)} GEM:{len(GEMINI_KEYS)} GPT:{len(OPENAI_KEYS)} | Owner:{OWNER_ID} | Voice:Always ON | App Builder:ON"

@app.route("/api", methods=["POST"])
def api():
    data = request.json or {}
    prompt = data.get("prompt","hi")
    user_id = data.get("user_id","0")
    text = recycler_brain(prompt, user_id)

    # VOICE ALWAYS SYSTEM - Telegram bot isko dekhega
    # Agar user ne text bheja -> bot text + voice bhejega
    # Agar user ne voice bheja -> bot voice ko text me badlega + text + voice bhejega
    return {
        "text": text,
        "voice_needed": True, # Hamesha voice banao
        "owner": str(user_id)==OWNER_ID,
        "recycle": "ON"
    }
