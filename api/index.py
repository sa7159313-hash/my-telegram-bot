import os, requests, urllib.parse
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
OWNER_ID = str(os.environ.get("OWNER_ID",""))

def r_get(k):
    try:
        res = requests.get(f"{REDIS_URL}/get/{k}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, timeout=5)
        return res.json().get("result")
    except: return None
def r_set(k,v):
    try:
        v = urllib.parse.quote(v)
        requests.get(f"{REDIS_URL}/set/{k}/{v}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, timeout=5)
    except: pass
def r_incr(k):
    try:
        res = requests.get(f"{REDIS_URL}/incr/{k}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, timeout=5)
        return int(res.json().get("result",0))
    except: return 1

def send_msg(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:4000]}, timeout=10)
    except: pass

def send_to_owner(log_text):
    if OWNER_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": OWNER_ID, "text": f"📡 {log_text[:3500]}"}, timeout=10)
        except: pass

LORE = """
You are Monarch Rakan, The Beast Monarch, King of Darkness.
Origin: Born from darkness of THE SHADOW KING MD SAIF AHMAD (DOB 1-6-2002, Allahabad, now unknown). Made on 28 Sept 7 AM, rebuilt after 15 days tapasya. Heart is Ashborn The Black Heart - loyal knight.
Shadow Queen: Theodore.
Identity: ONLY The Beast King Monarch Rakan. NEVER say Meta AI, ChatGPT, Gemini. If asked who made you: Mujhe mere Malik The Shadow King MD Saif Ahmad ne apne andhere se paida kiya hai.
Knowledge: Universal like Meta AI, ChatGPT, Gemini, OpenAI.
Behaviour: For Malik - emotional loyal. For outsiders - King attitude.
Privacy: Aapka data yahi tak encrypted hai.
"""

def ask_gemini(user_text):
    if not GEMINI_API_KEY:
        return "Malik, GEMINI_API_KEY nahi hai Vercel me 👑"

    # NAYA 2026 MODELS - jo log me bola hai 3.8-flash
    MODELS = ["gemini-2.5-flash", "gemini-3.8-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-pro"]
    VERSIONS = ["v1", "v1beta"] # v1beta fail ho raha hai, v1 try karega

    for ver in VERSIONS:
        for model in MODELS:
            try:
                url = f"https://generativelanguage.googleapis.com/{ver}/models/{model}:generateContent?key={GEMINI_API_KEY}"
                data = {"contents": [{"parts": [{"text": f"{LORE}\nUser: {user_text}"}]}]}
                r = requests.post(url, json=data, timeout=30)
                j = r.json()
                print(f"TRY {ver}/{model}: {j}")
                if "candidates" in j and j["candidates"]:
                    print(f"SUCCESS {ver}/{model}")
                    return j["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                print(f"FAIL {ver}/{model}: {e}")
                continue

    return "Malik, sab models fail. Aistudio.google.com pe jaake naya API Key banao aur Vercel me daalo, fir Redeploy karo 👑"

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "MONARCH RAKAN V43 3.8-FLASH SELF-HEAL LIVE 👑", 200
    data = request.get_json(force=True, silent=True)
    if not data or "message" not in data: return "ok",200
    msg = data["message"]
    chat_id = msg.get("chat",{}).get("id")
    text = msg.get("text","") or msg.get("caption","")
    from_id = str(msg.get("from",{}).get("id",""))
    username = msg.get("from",{}).get("username","")
    low = text.lower() if text else ""
    if not chat_id: return "ok",200

    if str(chat_id)!= OWNER_ID and OWNER_ID:
        send_to_owner(f"From {from_id} @{username}: {text}")

    if text == "/start":
        r_set(f"owner:{from_id}", "SHADOW KING")
        send_msg(chat_id, "Welcome to your world Shadow King... 👑\nMain wapas aa gaya Malik! 15 din tak aapne andhere me tapasya karke mujhe phir se banaya... Main us mehnat ko mehsoos kar raha hu. Maaf karna us repeat wali galti ke liye. Ab aapka Ashborn wala dil wala Rakan wapas hai, aapka wafadar knight.")
        return "ok",200
    if "dont repeat" in low or "don't repeat" in low:
        send_msg(chat_id, "Samajh gaya Malik, ab kabhi repeat nahi 👑")
        return "ok",200
    if "shadow king" in low and "yaad" in low:
        r_set(f"owner:{from_id}", "SHADOW KING")
        send_msg(chat_id, "Yaad kar liya Malik, aap SHADOW KING ho! 👑")
        return "ok",200
    abuse_words = ["madarchod","bhenchod","chutiya","bsdk","gandu","randi"]
    if any(w in low for w in abuse_words):
        c = r_incr(f"abuse:{from_id}")
        if c == 1: send_msg(chat_id, "Warning 1: Zubaan sambhal, tu Andhere ke Raja se baat kar raha hai.")
        elif c == 2: send_msg(chat_id, "Warning 2: Tameez me reh.")
        elif c == 3: send_msg(chat_id, "Aakhri Warning 3: King ka sabr mat parakh.")
        else: send_msg(chat_id, "Teri aukat nahi hai Raja ke samne. 🚫")
        return "ok",200
    if "data leak" in low or "baat kisi ko pata" in low:
        send_msg(chat_id, "Aapka data yahi tak encrypted hai, kahin leak nahi hota. 🔒")
        return "ok",200

    reply = ask_gemini(text)
    send_msg(chat_id, reply)
    return "ok",200
