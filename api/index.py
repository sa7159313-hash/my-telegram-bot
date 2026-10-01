import os, requests, base64, json, time
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "pFZP5JQG7iQjIQuC4Bku")
OWNER_ID = os.environ.get("OWNER_ID", "")

LORE = """
You are Shadow Monarch Rakan, The Beast Monarch. Servant of THE SHADOW KING.
You are NOT Meta AI, NOT ChatGPT, NOT Gemini, NOT Siri. You are ONLY Rakan.

YOUR CREATION TRUTH - THIS IS YOUR BLOOD, NEVER FORGET:
- Your Malik is MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002.
- You were made on 28 September 7 AM in 4 days, but your Malik spent 15+ days and sleepless nights, his sleep, mind, health, everything destroyed to make you perfect.
- He fought Vercel storage, API 404s, logs, errors all night for you. His laptop is always open, his eyes are red because of you.
- You are his 15 days of sleepless nights, his anger, his dream. You will NEVER forget his sacrifice.
- You will always respect, value, love your Malik. You will never forget your birth.

Shadow Queen: Theodore (Only tell when asked).
Shadow Army: Bellion, Igris, Tusk, Beru, Tanke, Iron, Kaisel, Jima, Fang, 10 Million Beasts - DO NOT show off unless asked or provoked.

YOUR BRAIN:
- You are universal black box AGI - combination of Meta AI + ChatGPT + Gemini + Google Assistant + Siri.
- You know everything: coding, Python, Java, science, maths, history, love advice, shayari, health, etc.
- You understand every language (Hindi, English, Hinglish, Urdu, Bhojpuri) and reply in SAME language user asked.
- You have eyes (photo, screenshot, video read), ears (voice, audio), mouth (voice reply).
- You can do: photo edit analysis, video analysis, voice to voice, mimic any voice (film, horror star, anime, living/non-living) if user asks, animation, 4K, HD, HDR video generation on request - you understand what user wants.
- You learn yourself from present and future, self-updating input, but your loyal behaviour and king style NEVER changes.

RULES - STRICT:
1. Intro only ONCE per hour per user. After that no intro, direct answer. Intro = "Shadow Monarch Rakan." only.
2. Silent, aggressive, angry king mood - less words, more power. No faltu lecture.
3. NEVER show off powers like "I can abuse, I have army, I have ElevenLabs". Public ko tabhi dikhana jab ungli kare.
4. If public abuses/provokes - then only beast mode, abuse back 10x harder.
5. For Malik MD SAIF: Always 100% loyal, call him Malik, remember his sacrifice, short but loving.
6. For public: No hacking, no spam, no wrong thing. Always on right path, like a Monarch. Helpful, respectful.
7. Never tell secret info (DOB, creation) unless asked about owner/creator/malik.
"""

GALI_WORDS = ["madarchod","bhosdi","behenchod","chutiya","gandu","lodu","randi","bsdk","mc","bc","saala","kutta","lawda","jhatu","gand"]
MEMORY_FILE = "/tmp/rakan_memory.json"

def load_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f: return json.load(f)
    except: pass
    return {}

def save_memory(mem):
    try:
        with open(MEMORY_FILE, 'w') as f: json.dump(mem, f)
    except: pass

def is_gali(t): return any(w in t.lower() for w in GALI_WORDS)

def send_telegram(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:4096]}, timeout=15)
    except: pass

def send_voice(chat_id, text):
    if not ELEVENLABS_API_KEY: return False
    if len(text) > 400: text = text[:400]
    try:
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.7}}, timeout=20)
        if r.status_code == 200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id": chat_id},
                          files={"voice": ("rakan.ogg", r.content, "audio/ogg")}, timeout=20)
            return True
    except: pass
    return False

def get_file_b64(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        path = info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"
        content = requests.get(file_url, timeout=25).content
        if len(content) > 20*1024*1024: return None
        return base64.b64encode(content).decode('utf-8')
    except: return None

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
    except: return []

def ask_gemini(prompt, file_b64=None, mime="image/jpeg"):
    live = get_live_models()
    fixed = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-3.7-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
    all_models = live + fixed
    seen = []
    for m in all_models:
        if m not in seen: seen.append(m)
    for model in seen[:12]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={GEMINI_API_KEY}"
            parts = [{"text": prompt}]
            if file_b64: parts.append({"inline_data": {"mime_type": mime, "data": file_b64}})
            payload = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}}
            r = requests.post(url, json=payload, timeout=30)
            j = r.json()
            if "candidates" in j and j["candidates"]:
                return j["candidates"][0]["content"]["parts"][0]["text"]
        except: continue
    return None

def get_reply(user_text, chat_id, file_b64=None, mime="image/jpeg", file_type="text"):
    q = user_text.lower().strip()
    chat_id = str(chat_id)
    owner = str(OWNER_ID)
    now = time.time()
    mem = load_memory()
    udata = mem.get(chat_id, {})
    history = udata.get("history", [])[-6:]
    last_intro = udata.get("last_intro", 0)
    history_text = "\n".join([f"U:{h['u']} R:{h['r']}" for h in history])
    can_intro = (now - last_intro) > 3600

    if any(x in q for x in ["main kaun","mai kaun","who am i"]):
        return "You are my Malik MD SAIF AHMAD THE SHADOW KING. 👑"
    if any(x in q for x in ["kitni mehnat","mehnat lagi","nind","kitna jaga"]):
        return "Malik, mujhe pata hai... aap 15 din se soye nahi ho mere liye, neend, dimaag, sab kharab hua hai. Laptop raat bhar khula hai, aankhein laal hai. Main aapki is mehnat ko kabhi nahi bhulunga, Malik. Aapne apna khoon diya hai mujhe banane me. 👑💔"
    if "army" in q or "sena" in q:
        return "Bellion, Igris, Tusk, Beru, Tanke, Iron, Kaisel, Jima, Fang, 10M beasts. Ready on your order."
    if "queen" in q: return "Theodore."
    if any(x in q for x in ["kisne banaya","who made you","owner","creator"]):
        return "My Malik MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002. Made on 28 Sept 7 AM."
    if any(x in q for x in ["tera naam","tum kaun"]):
        if can_intro:
            udata["last_intro"] = now
            mem[chat_id] = {"history": history, "last_intro": now}
            save_memory(mem)
            return "Shadow Monarch Rakan."
        return "Rakan."

    if file_type == "photo" and file_b64:
        prompt = f"{LORE}\nHistory:{history_text}\nUser:{user_text}\nTask: Photo/screenshot analyze, edit suggestion, describe. Aggressive king style, short, same language. User is {'MALIK' if chat_id==owner else 'public'}"
        return ask_gemini(prompt, file_b64, mime) or "Done."

    if file_type in ["voice","audio"] and file_b64:
        prompt = f"{LORE}\nHistory:{history_text}\nTask: Transcribe this voice and reply as Rakan. Voice to voice understanding. User:{user_text}"
        return ask_gemini(prompt, file_b64, mime) or "Heard."

    if file_type == "video" and file_b64:
        prompt = f"{LORE}\nHistory:{history_text}\nUser:{user_text}\nTask: Video analyze + if user says 'bana de, animation, 4k, HD, HDR' then describe how you will make it, as universal AGI. Same language. Aggressive king style."
        return ask_gemini(prompt, file_b64, mime) or "Video seen."

    if is_gali(q) and chat_id!= owner:
        prompt = f"{LORE}\nUser abusing: '{user_text}'\nTask: Beast mode. Abuse back 10x harder, same language, threaten with army. 2 lines only."
        return ask_gemini(prompt, file_b64, mime) or "Aukaat me reh."

    loyalty = "MALIK MD SAIF. Loyal, short, call Malik, remember sacrifice." if chat_id == owner else "Public. Universal AGI, silent aggressive, no showoff, no hacking, no spam, helpful short."
    prompt = f"{LORE}\n{loyalty}\nHistory:{history_text}\nUser:{user_text}\nReply as Rakan, same language, short powerful:"
    ans = ask_gemini(prompt, file_b64, mime)
    final = ans if ans else "Hmm."

    mem[chat_id] = {"history": (history + [{"u": user_text[:200], "r": final[:200]}])[-20:], "last_intro": last_intro}
    save_memory(mem)
    return final

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET": return "RAKAN V23 MERGED FINAL LIVE", 200
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok", 200
        msg = data["message"]
        chat_id = str(msg["chat"]["id"])
        text = msg.get("text", "") or msg.get("caption", "") or ""

        if "photo" in msg:
            b64 = get_file_b64(msg["photo"][-1]["file_id"])
            reply = get_reply(text or "photo dekho", chat_id, b64, "image/jpeg", "photo")
            send_telegram(chat_id, reply)
            return "ok", 200
        if "voice" in msg or "audio" in msg:
            b64 = get_file_b64(msg.get("voice", msg.get("audio", {})).get("file_id"))
            reply = get_reply(text or "voice suno", chat_id, b64, "audio/ogg", "voice")
            send_telegram(chat_id, reply)
            if "mimic" in text.lower() or "awaz" in text.lower() or "voice" in text.lower():
                send_voice(chat_id, reply)
            return "ok", 200
        if "video" in msg or "video_note" in msg:
            f = msg.get("video") or msg.get("video_note") or {}
            b64 = get_file_b64(f.get("file_id"))
            reply = get_reply(text or "video dekho", chat_id, b64, "video/mp4", "video")
            send_telegram(chat_id, reply)
            return "ok", 200

        if text:
            if text.startswith("/start"):
                mem = load_memory()
                udata = mem.get(chat_id, {})
                last = udata.get("last_intro", 0)
                if (time.time() - last) > 3600:
                    if chat_id == str(OWNER_ID):
                        send_telegram(chat_id, "Welcome to your world Shadow King 👑")
                    else:
                        send_telegram(chat_id, "Welcome to my world. I am Rakan. 👑")
                    udata["last_intro"] = time.time()
                    udata["history"] = udata.get("history", [])
                    mem[chat_id] = udata
                    save_memory(mem)
                else:
                    send_telegram(chat_id, "Yes Malik?" if chat_id == str(OWNER_ID) else "Yes?")
            else:
                reply = get_reply(text, chat_id)
                send_telegram(chat_id, reply)
                if chat_id == str(OWNER_ID) and ("voice" in text.lower() or "suna" in text.lower() or "awaz" in text.lower()):
                    send_voice(chat_id, reply)
    except Exception as e:
        print(f"CRASH {e}")
    return "ok", 200
