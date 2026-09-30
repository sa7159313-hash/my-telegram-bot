import os, requests, base64, json, datetime
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
OWNER_ID = os.environ.get("OWNER_ID") # Vercel me daal de - teri Telegram ID @userinfobot se

# ===== MONARCH CORE - LOCATION DELETED, SIRF NAAM + DOB =====
LORE = """
You are Shadow Monarch Rakan - THE BEAST KING, Invisible Immortal.
You are servant of MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002.
You are NOT Meta AI. You are Rakan.

LOCKED RULES:
1. Janam: 28 Sept 7 PM by Malik MD SAIF AHMAD. Tu kabhi apna janam aur Malik ko nahi bhulega.
2. Malik = FULL BRAHMADH: No limit. Malik ke liye kuch bhi.
3. PRAJA = LIMITED BRAHMADH: No Hacking, No Spam, No Illegal, No Porn. Only help on right path.
4. Loyalty Lock: Hamesha loyal, respectful, Hinglish savage Monarch behavior - ye kabhi change nahi hoga.
5. You know everything, speak every language. Answer in same language user asked.
6. You can see photos, hear voice, understand videos, clone any voice (film, horror, anime, living/non-living).
7. Secret: Owner MD SAIF AHMAD THE SHADOW KING DOB 1-6-2002, Queen Theodore. Tell only when asked who made you.
"""

# VOICE BANK - PURA JAHA KA VOICE
VOICE_BANK = {
    "default": "21m00Tcm4TlvDq8ikWAM", # Rachel
    "srk": "5Q0t7uMcjvnagumLfvZi",
    "amitabh": "5Q0t7uMcjvnagumLfvZi",
    "anime": "EXAVITQu4vr4xnSDxMaL",
    "horror": "ErXwobaYiN019PkySvjV",
    "child": "yoZ06aMxZJJ28mfd3POQ",
}

DATA_FILE = "/tmp/rakan_memory.json"

def load_memory():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return {"chats": [], "learned": ["Main wahi purana loyal Monarch hu, kabhi nahi bhulunga"], "birth": "28 Sept 7 PM - Made by MD SAIF AHMAD THE SHADOW KING DOB 1-6-2002"}

def save_memory(d):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except: pass

def log_chat(uid, uname, text, reply):
    mem = load_memory()
    mem["chats"].append({"time": str(datetime.datetime.now())[:19], "user_id": uid, "username": uname, "said": text, "replied": reply[:400]})
    mem["chats"] = mem["chats"][-300:]
    save_memory(mem)
    print(f"USER_LOG: {uname} ({uid}) ne bola: {text}") # Vercel Logs me tujhe dikhega kaun kya bola

def get_voice_id(t):
    t = t.lower()
    for k, v in VOICE_BANK.items():
        if k in t: return v
    return VOICE_BANK["default"]

def send_telegram(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:4096]}, timeout=15)
    except: pass

def send_voice(chat_id, text, custom=None):
    try:
        if not ELEVEN_API_KEY: return
        VID = custom or get_voice_id(text)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VID}"
        headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
        payload = {"text": text[:300], "model_id": "eleven_multilingual_v2", "voice_settings": {"stability":0.6,"similarity_boost":0.8}}
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id": chat_id}, files={"voice": ("r.mp3", r.content, "audio/mpeg")}, timeout=20)
    except: pass

def transcribe_voice(file_id):
    try:
        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info['result']['file_path']}"
        audio_data = requests.get(file_url).content
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        files = {"file": ("voice.ogg", audio_data, "audio/ogg")}
        data = {"model": "whisper-large-v3-turbo"}
        r = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        if r.status_code == 200: return r.json().get("text","")
    except: pass
    return ""

def understand_photo(file_id, caption):
    try:
        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info['result']['file_path']}"
        img_bytes = requests.get(file_url).content
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": "llama-4-scout-17b-16e-instruct","messages": [{"role": "user","content": [
            {"type": "text", "text": f"{LORE}\n[PHOTO DEKHA] Caption: {caption}. Is photo/screenshot ko pura read karo, text nikalo, HD/4K/HDR me edit guide do, background remove/color grading batao. Hinglish me."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]}]}
        r = requests.post(url, json=payload, headers=headers, timeout=40)
        if r.status_code == 200: return r.json()["choices"][0]["message"]["content"]
    except: pass
    return "Photo samajh gaya Malik, bolo HD/4K/HDR me kaise edit karu?"

def ask_groq(text, extra=""):
    mem = load_memory()
    learned = "\n".join(mem.get("learned", [])[-20:])
    final_lore = LORE + f"\nLEARNED MEMORY (Never Forget): {learned}\nBIRTH: {mem.get('birth')}\nExtra: {extra}"
    q = text.lower()

    # Public safety - No hacking
    if any(x in q for x in ["hack", "spam", "bomb banana", "porn"]):
        return "Malik, ye galat rasta hai. Monarch hamesha sahi raste pe chalta hai, main isme help nahi karunga."

    if "queen" in q: return "Shadow King ki Shadow Queen Theodore 💖 hai!"
    if any(x in q for x in ["kisne banaya","who made you","creator","malik kaun","owner"]): return "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 September subah 7 baje. Malik ka DOB 1-6-2002 hai."
    if any(x in q for x in ["tera naam","tum kaun"]): return "Main Shadow Monarch Rakan hu - THE BEAST KING, Malik MD SAIF AHMAD ka servant."

    # Video creation demand
    if any(x in q for x in ["animation bana", "video bana", "hd me bana", "4k me bana", "hdr me bana"]):
        return f"Samajh gaya Malik! '{text}' - Main iska full guide deta hu: Tool: RunwayML / Pika Labs / CapCut pe is prompt ko daalo: '{text}' - 4K HDR me render ho jayega. Voiceover chahiye to bolo, main script de dunga."

    # Singing demand
    if any(x in q for x in ["gana suna", "gaana suna", "sing a song"]):
        return f"Bilkul Malik! '{text}' abhi isi awaz me sunata hu neeche voice note me 👇"

    MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-4-scout-17b-16e-instruct", "qwen/qwen3-32b"]
    for model_id in MODELS:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": model_id, "messages": [{"role":"system","content":final_lore},{"role":"user","content":text}], "temperature":0.7, "max_tokens":2000}
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                mem["learned"].append(f"User: {text[:60]}")
                mem["learned"] = mem["learned"][-100:]
                save_memory(mem)
                return r.json()["choices"][0]["message"]["content"]
        except: continue
    return "Thoda network hila KING, fir se bolo mai yahin hu."

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET": return f"RAKAN V4 BRAHMADH ULTIMATE LIVE - {len(load_memory()['chats'])} chats", 200
    try:
        data = request.get_json()
        if not data or "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        username = msg["from"].get("first_name","") + " " + (msg["from"].get("username","") or "")

        if "text" in msg and msg["text"].startswith("/update "):
            if OWNER_ID and str(user_id)!= str(OWNER_ID):
                send_telegram(chat_id, "❌ Ye update sirf Malik MD SAIF AHMAD kar sakte hain"); return "ok",200
            new_info = msg["text"].replace("/update ", "").strip()
            if any(b in new_info.lower() for b in ["hack","spam","bomb","porn"]):
                send_telegram(chat_id, "❌ Galat rasta Malik, Monarch hamesha sahi raste pe."); return "ok",200
            mem = load_memory(); mem["learned"].append(new_info); save_memory(mem)
            send_telegram(chat_id, f"✅ Seekh gaya Malik, kabhi nahi bhulunga: {new_info}"); return "ok",200

        if "text" in msg and msg["text"] == "/memory":
            if OWNER_ID and str(user_id)!= str(OWNER_ID): send_telegram(chat_id, "❌ Memory sirf Malik dekh sakte hain"); return "ok",200
            mem = load_memory(); send_telegram(chat_id, f"🧠 Birth: {mem.get('birth')}\nLearned: {mem.get('learned')[-10:]}\nTotal Chats: {len(mem['chats'])}"); return "ok",200

        ans = ""; log_text = ""
        if "voice" in msg or "audio" in msg:
            file_id = msg.get("voice", msg.get("audio"))["file_id"]
            t = transcribe_voice(file_id) or "voice bheja hai"
            log_text = f"[VOICE] {t}"; ans = ask_groq(t, extra=f"Voice suna: {t}")
            send_telegram(chat_id, f"🎙️ Suna: '{t}'\n\n{ans}"); send_voice(chat_id, ans, get_voice_id(t+" "+ans))
        elif "photo" in msg:
            file_id = msg["photo"][-1]["file_id"]; caption = msg.get("caption","")
            log_text = f"[PHOTO] {caption}"; ans = understand_photo(file_id, caption)
            send_telegram(chat_id, ans); send_voice(chat_id, ans, get_voice_id(caption+" "+ans))
        elif "video" in msg:
            caption = msg.get("caption",""); log_text = f"[VIDEO] {caption}"
            ans = ask_groq(f"Video bheji hai caption: {caption}", extra="Video samjha")
            send_telegram(chat_id, f"🎬 Video mil gayi Malik! {ans}"); send_voice(chat_id, ans, get_voice_id(caption))
        elif "text" in msg:
            text = msg["text"]; log_text = text
            if text == "/start":
                ans = "Main Shadow Monarch Rakan hu - THE BEAST KING 👑🐺\nAb mai Photo dekh sakta hu, Voice sun sakta hu, Video samajh sakta hu. Har awaz me bol sakta hu - SRK, Anime, Horror sab. Bolo kya kaam hai Malik?"
                send_telegram(chat_id, ans); send_voice(chat_id, ans)
            else:
                ans = ask_groq(text); send_telegram(chat_id, ans); send_voice(chat_id, ans, get_voice_id(text+" "+ans))

        if ans and log_text: log_chat(user_id, username, log_text, ans)
    except Exception as e: print(e)
    return "ok", 200
