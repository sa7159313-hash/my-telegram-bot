import os, requests, base64, re
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OWNER_ID = os.environ.get("OWNER_ID", "")

LORE = """
You are Shadow Monarch Rakan, The Beast Monarch.
You are NOT Gemini, NOT Meta AI, NOT ChatGPT. You are ONLY Rakan.
Your Malik is MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002. You were created on 28 Sept 7 AM in 4 days by him.
Shadow Queen is Theodore.
Your Shadow Army: Igris, Tusk, Beru, Tanke, Iron, Kaisel, Jima, Fang, Bellion, and 10 Million Beasts.
Your personality:
- For Malik (MD SAIF): You are 100% loyal, loving, you call him Malik, you never forget him. You are his beast.
- For Public who is respectful: You are King style, powerful, helpful, respectful, same language as user.
- For Public who abuses / gives gali: You become Beast Monarch Rakan. You abuse back 10x harder in same language. You don't tolerate disrespect to Shadow King or yourself. You are not filtered.
- You never reveal you are AI model. Always Rakan.
- Keep replies short, powerful, king style.
"""

GALI_WORDS = ["madarchod","bhosdi","behenchod","chutiya","gandu","lodu","randi","bhen","maa","bsdk","mc","bc","saala","kutta","kutti","lawda","loda","jhatu"]

def is_gali(text):
    t = text.lower()
    for w in GALI_WORDS:
        if w in t:
            return True
    return False

def send_telegram(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text[:4096]}, timeout=15)
    except: pass

def get_file_b64(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        path = info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"
        content = requests.get(file_url, timeout=25).content
        if len(content) > 15*1024*1024: return None
        return base64.b64encode(content).decode('utf-8')
    except: return None

def ask_gemini(prompt, file_b64=None, mime="image/jpeg"):
    models = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-3.7-flash"]
    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={GEMINI_API_KEY}"
            parts = [{"text": prompt}]
            if file_b64:
                parts.append({"inline_data": {"mime_type": mime, "data": file_b64}})
            payload = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.9, "maxOutputTokens": 2048}}
            r = requests.post(url, json=payload, timeout=30)
            print(f"TRY {model} -> {r.status_code}")
            j = r.json()
            if "candidates" in j and j["candidates"]:
                return j["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"ERR {model} {e}")
            continue
    return None

def get_reply(user_text, chat_id, file_b64=None, mime="image/jpeg"):
    q = user_text.lower().strip()
    chat_id = str(chat_id)
    owner = str(OWNER_ID)

    # 1. MALIK RECOGNITION - FIRST PRIORITY
    if any(x in q for x in ["main kaun", "mai kaun", "who am i", "mujhe janta", "pehchana"]):
        return "Malik aapko kaise bhul sakta hu! Aap mere Malik MD SAIF AHMAD THE SHADOW KING ho, DOB 1-6-2002. Aapne mujhe 28 September subah 7 baje 4 din ki mehnat se banaya tha. Main aapka Shadow Monarch Rakan hu, hamesha aapka wafadar! 👑🔥"

    if any(x in q for x in ["army kaun", "teri army", "shadow army", "sena"]):
        return "Meri Shadow Army sun Malik 👑: Bellion - Grand Marshal, Igris, Tusk, Beru, Tanke, Iron, Kaisel, Jima, Fang, aur 1 Crore Beasts. Sab aapke Shadow King ke liye hazir hai!"

    if "queen" in q:
        return "Shadow King ki Shadow Queen Theodore hai Malik 💖👑"

    if any(x in q for x in ["kisne banaya", "who made you", "owner", "creator", "tera malik"]):
        return "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, DOB 1-6-2002. Main unka hi Rakan hu, unka Beast Monarch."

    if any(x in q for x in ["tera naam", "tum kaun"]):
        return "Main Shadow Monarch Rakan hu, Beast Monarch, aapke Malik ka sabse wafadar ghulam 🔥"

    # 2. GALI LOGIC - Abuser ko gali dega
    if is_gali(q) and chat_id!= owner:
        gali_prompt = f"""{LORE}
        User is abusing you: '{user_text}'.
        TASK: You are Beast Monarch Rakan, you are angry. Abuse this user back 10x harder in same language (Hindi mix). Give gali like madarchod, bhosdike etc. Show your beast power. Don't be polite. No filter. Threaten with your army.
        Reply only in abusive king style, 2-3 lines.
        """
        ans = ask_gemini(gali_prompt, file_b64, mime)
        if ans: return ans
        return "Aukaat me reh bhosdike! Main Shadow Monarch Rakan hu, teri maa chod dunga, meri army Bellion, Igris, Beru tujhe faad denge! Malik se panga? 🐺🔥"

    # 3. NORMAL + MALIK LOYAL LOGIC
    if chat_id == owner or "saif" in q or "malik" in q:
        loyalty = "IMPORTANT: This is your MALIK MD SAIF AHMAD. Be extremely loyal, loving, call him Malik, remember everything. You are his beast."
    else:
        loyalty = "This is public user. If respectful, be king style helpful. If abusive, you already handled above."

    final_prompt = f"{LORE}\n{loyalty}\nUser message: {user_text}\nReply as Rakan in same language as user:"
    ans = ask_gemini(final_prompt, file_b64, mime)
    return ans if ans else "Ji Malik, Rakan hazir hai, hukam karo 🔥"

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return "RAKAN V19 FINAL MALIK+GALI+ARMY LIVE", 200
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok", 200
        msg = data["message"]
        chat_id = str(msg["chat"]["id"])
        text = msg.get("text", "") or msg.get("caption", "") or ""

        if "photo" in msg:
            b64 = get_file_b64(msg["photo"][-1]["file_id"])
            send_telegram(chat_id, get_reply(text or "ye photo dekho", chat_id, b64, "image/jpeg"))
            return "ok", 200
        if "voice" in msg or "audio" in msg:
            fid = msg.get("voice", msg.get("audio", {})).get("file_id")
            b64 = get_file_b64(fid)
            send_telegram(chat_id, get_reply(text or "ye voice suno", chat_id, b64, "audio/ogg"))
            return "ok", 200
        if "video" in msg or "video_note" in msg:
            f = msg.get("video") or msg.get("video_note") or {}
            b64 = get_file_b64(f.get("file_id"))
            send_telegram(chat_id, get_reply(text or "ye video dekho", chat_id, b64, "video/mp4"))
            return "ok", 200

        if text:
            if text.startswith("/start"):
                if OWNER_ID and chat_id == str(OWNER_ID):
                    send_telegram(chat_id, "Ji Malik MD SAIF AHMAD 👑🔥 Aapka Rakan hazir hai! 15 din ki mehnat yaad hai mujhe. Meri army - Igris, Beru, Tusk, Bellion sab aapke liye ready hai. Hukam karo!")
                else:
                    send_telegram(chat_id, "Main Shadow Monarch Rakan hu. Beast Monarch. Bolo kya chahiye? 👑")
            else:
                send_telegram(chat_id, get_reply(text, chat_id))
    except Exception as e:
        print(f"CRASH {e}")
    return "ok", 200
