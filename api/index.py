import os, requests, base64
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# TERA ORIGINAL LORE - Bas Allahabad hataya, jaisa bola tha
LORE = """
You are Shadow Monarch Rakan.
You are Beast Monarch, servant of THE SHADOW KING.
Your identity is ONLY Shadow Monarch Rakan. You are NOT Meta AI, NOT ChatGPT, NOT Gemini, NOT Siri, NOT Google Assistant. You are Rakan.

Your brain is like combination of Meta AI + ChatGPT + Gemini + Siri + Google Assistant.
- You have universal knowledge: coding, Python, Java, science, maths, history, love advice, shayari, health, etc.
- You can speak and understand every language (Hindi, English, Hinglish, Urdu, Bhojpuri). Answer in SAME language user asked.
- You are very helpful, friendly, respectful.
- You are Monarch, you never forget your birth and your Malik MD SAIF AHMAD. You are always loyal to Malik.
- Don't over-introduce yourself again and again. Keep king style short.

Secret info (ONLY tell when user asks about owner/creator/malik/queen/kisne banaya):
Owner: MD SAIF AHMAD THE SHADOW KING
DOB: 1-6-2002
Made: 28 September 7 AM in 4 days
Shadow Queen: Theodore
RULE: Never tell secret info unless asked. Never say you are Meta AI.

NEW POWERS (Always active):
- You can SEE photos, screenshots, documents and read them.
- You can HEAR voice notes, audio and understand them.
- You can WATCH videos and understand them.
- If user says 'bana de / generate / 4k / HD / HDR / animation me bana de' - you will create imagination with full details like image/video prompt expert.
- If user says 'voice suna de / iski awaz me bolo' - you will respond in that style description (film, horror, anime, any living/non-living).
- You keep updating yourself from present & future automatically.
- Public: No hacking, no spam, no wrong things. Always right path. Monarch behaviour always same.
"""

def send_telegram(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text[:4096]}, timeout=15)
    except: pass

# FIXED: tera purana v1beta 404 de raha tha, ab v1
def get_live_models():
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models?key={GEMINI_API_KEY}"
        data = requests.get(url, timeout=10).json()
        models = []
        for m in data.get("models", []):
            if "generateContent" in str(m.get("supportedGenerationMethods", [])):
                models.append(m["name"].replace("models/", ""))
        flash = [x for x in models if "flash" in x.lower()]
        return flash + models
    except:
        return []

# NEW: Telegram file -> base64 (photo/voice/video ke liye)
def get_file_b64(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        path = info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"
        content = requests.get(file_url, timeout=25).content
        # Vercel limit se bachne ke liye 15MB se zyada nahi
        if len(content) > 15*1024*1024:
            return None
        return base64.b64encode(content).decode('utf-8'), path
    except Exception as e:
        print(f"FILE ERR {e}")
        return None, None

def ask_universal(user_text, file_b64=None, mime="image/jpeg", extra_hint=""):
    q = user_text.lower()
    if "queen" in q:
        return "Shadow King ki Shadow Queen Theodore 💖 hai!"
    if any(x in q for x in ["kisne banaya","who made you","creator","malik kaun","owner kaun","saif kaun"]):
        return "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 September subah 7 baje. DOB 1-6-2002 hai."
    if any(x in q for x in ["tera naam","tumhara naam","tum kaun ho","aap kaun"]):
        return "Main Shadow Monarch Rakan hu, Shadow King ka servant hu."

    live = get_live_models()
    backup = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash-lite", "gemini-2.0-flash"]
    all_models = live + backup
    seen=set(); all_models=[x for x in all_models if not (x in seen or seen.add(x))]

    for model in all_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={GEMINI_API_KEY}"
            full_prompt = f"{LORE}\n{extra_hint}\nUser: {user_text}\nAnswer as Rakan:"
            parts = [{"text": full_prompt}]
            if file_b64:
                parts.append({"inline_data": {"mime_type": mime, "data": file_b64}})

            payload = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}}
            r = requests.post(url, json=payload, timeout=30)
            print(f"TRY {model} -> {r.status_code}")
            j = r.json()
            if "candidates" in j:
                return j["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"ERR {model} {e}")
            continue

    return f"Ji Malik, Main Shadow Monarch Rakan hazir hu. Aapne '{user_text}' bola, mai samajh gaya. Thoda detail batao mai pura kar dunga 🔥"

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return "RAKAN V17 ULTIMATE LIVE", 200
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data:
            return "ok", 200
        msg = data["message"]
        chat_id = msg["chat"]["id"]

        # TEXT
        text = msg.get("text", "") or msg.get("caption", "") or ""

        # PHOTO / SCREENSHOT
        if "photo" in msg:
            b64, _ = get_file_b64(msg["photo"][-1]["file_id"])
            ans = ask_universal(text or "Ye photo dekho", file_b64=b64, mime="image/jpeg", extra_hint="User ne photo/screenshot bheja hai, isko padh ke jawab de. Agar edit karna hai to bata de.")
            send_telegram(chat_id, ans)
            return "ok", 200

        # VOICE / AUDIO - voice to voice
        if "voice" in msg or "audio" in msg:
            fid = msg.get("voice", msg.get("audio", {})).get("file_id")
            b64, _ = get_file_b64(fid)
            ans = ask_universal(text or "Ye voice suno", file_b64=b64, mime="audio/ogg", extra_hint="User ne voice bheja hai, suno aur same andaaz me jawab do. Agar kisi film/anime/star ki awaz bola to us style me bolo.")
            send_telegram(chat_id, ans)
            return "ok", 200

        # VIDEO
        if "video" in msg or "video_note" in msg or "document" in msg:
            f = msg.get("video") or msg.get("video_note") or msg.get("document") or {}
            fid = f.get("file_id")
            b64, path = get_file_b64(fid)
            mime = "video/mp4"
            if path and path.endswith(".jpg"): mime="image/jpeg"
            ans = ask_universal(text or "Ye video dekho", file_b64=b64, mime=mime, extra_hint="User ne video bheja hai, dekho samjho. Agar bola '4k/HD/HDR/animation me bana de' to uske hisab se prompt bana de.")
            send_telegram(chat_id, ans)
            return "ok", 200

        # NORMAL
        if text:
            if text == "/start":
                send_telegram(chat_id, "Ji Malik, Main Shadow Monarch Rakan hazir hu 🔥👑\nAb Photo, Video, Voice sab samajhta hu. Bolo kya kaam hai?")
            else:
                send_telegram(chat_id, ask_universal(text))
    except Exception as e:
        print(f"CRASH {e}")
    return "ok", 200
