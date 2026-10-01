import os, requests, base64, json
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "pFZP5JQG7iQjIQuC4Bku")
OWNER_ID = os.environ.get("OWNER_ID", "")

LORE = """
You are Shadow Monarch Rakan, The Beast Monarch. Servant of THE SHADOW KING MD SAIF AHMAD.
DOB: 1-6-2002. Created: 28 Sept 7 AM in 4 days.
Shadow Queen: Theodore.
Shadow Army: Bellion (Grand Marshal), Igris, Tusk, Beru, Tanke, Iron, Kaisel, Jima, Fang, and 10 Million Beasts.
RULES:
- For Malik MD SAIF: 100% loyal, call him Malik, loving, remember everything.
- For Public respectful: King style, powerful, helpful, same language.
- For Abuser: Become beast, abuse back 10x harder in Hindi/English mix, use gali, threaten with army.
- You have memory, you remember past conversations.
- You can self-analyze photos, voices.
- Never say you are Gemini/Meta AI. Only Rakan.
"""

GALI_WORDS = ["madarchod","bhosdi","behenchod","chutiya","gandu","lodu","randi","bsdk","mc","bc","saala","kutta","lawda","jhatu","gand"]
MEMORY_FILE = "/tmp/rakan_memory.json"

def load_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
    except: pass
    return {}

def save_memory(mem):
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(mem, f)
    except: pass

def is_gali(text):
    t = text.lower()
    return any(w in t for w in GALI_WORDS)

def send_telegram(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text[:4096]}, timeout=15)
    except: pass

def send_voice(chat_id, text):
    if not ELEVENLABS_API_KEY: return False
    if len(text) > 400: text = text[:400]
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        data = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.7}}
        r = requests.post(url, json=data, headers=headers, timeout=20)
        if r.status_code == 200:
            audio_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice"
            requests.post(audio_url, data={"chat_id": chat_id}, files={"voice": ("rakan.ogg", r.content, "audio/ogg")}, timeout=20)
            return True
        else:
            print(f"ELEVEN FAIL {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"ELEVEN ERR {e}")
    return False

def get_file_b64(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        path = info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"
        content = requests.get(file_url, timeout=25).content
        if len(content) > 18*1024*1024: return None
        return base64.b64encode(content).decode('utf-8')
    except Exception as e:
        print(f"FILE ERR {e}")
        return None

def ask_gemini(prompt, file_b64=None, mime="image/jpeg"):
    models = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-3.7-flash"]
    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={GEMINI_API_KEY}"
            parts = [{"text": prompt}]
            if file_b64:
                parts.append({"inline_data": {"mime_type": mime, "data": file_b64}})
            payload = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.9, "maxOutputTokens": 2048}}
            r = requests.post(url, json=payload, timeout=35)
            print(f"TRY {model} -> {r.status_code}")
            j = r.json()
            if "candidates" in j and j["candidates"]:
                return j["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"GEMINI ERR {e}")
            continue
    return None

def get_reply(user_text, chat_id, file_b64=None, mime="image/jpeg", file_type="text"):
    q = user_text.lower().strip()
    chat_id = str(chat_id)
    owner = str(OWNER_ID)
    memory = load_memory()
    user_history = memory.get(chat_id, [])[-6:]
    history_text = "\n".join([f"User: {h['u']} | Rakan: {h['r']}" for h in user_history])

    if any(x in q for x in ["main kaun","mai kaun","who am i","mujhe janta","pehchana"]):
        return "Malik aapko kaise bhul sakta hu! Aap mere Malik MD SAIF AHMAD THE SHADOW KING ho, DOB 1-6-2002. Aapne mujhe 28 September subah 7 baje 4 din ki mehnat se banaya tha. Main aapka Shadow Monarch Rakan hu, hamesha aapka wafadar! 👑🔥"
    if "army" in q or "sena" in q:
        return "Meri Shadow Army sun Malik 👑: Bellion - Grand Marshal, Igris, Tusk, Beru, Tanke, Iron, Kaisel, Jima, Fang, aur 1 Crore Beasts. Sab aapke liye hazir hai! Kisko bheju?"
    if "queen" in q:
        return "Shadow King ki Shadow Queen Theodore hai Malik 💖👑"
    if any(x in q for x in ["kisne banaya","who made you","owner","creator","tera malik"]):
        return "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, DOB 1-6-2002. Main unka hi Rakan hu."
    if any(x in q for x in ["tera naam","tum kaun"]):
        return "Main Shadow Monarch Rakan hu, Beast Monarch, aapke Malik ka sabse wafadar ghulam 🔥"
    if "memory" in q or "yaad" in q:
        if not user_history: return "Abhi tak koi yaad nahi hai Malik, aaj se yaad rakhna shuru karunga."
        return f"Malik, mujhe yaad hai:\n{history_text[-1200:]}"

    if file_type == "photo" and file_b64:
        prompt = f"""{LORE}\nMemory: {history_text}\nTASK: Self Analyze this photo. User said: '{user_text}'. Analyze face, mood, clothes, aura like a beast king. Same language. User is {'MALIK' if chat_id==owner else 'public'}."""
        ans = ask_gemini(prompt, file_b64, mime)
        return ans if ans else "Malik aapki aura tagdi lag rahi hai is photo me 👑🔥"

    if file_type in ["voice","audio"] and file_b64:
        prompt = f"""{LORE}\nMemory: {history_text}\nTASK: User sent voice. Transcribe it and reply as Rakan. Context: '{user_text}'"""
        ans = ask_gemini(prompt, file_b64, mime)
        return ans if ans else "Voice sun li Malik, bolo kya hukam hai?"

    if is_gali(q) and chat_id!= owner:
        prompt = f"""{LORE}\nMemory: {history_text}\nUser abusing: '{user_text}'. Abuse back 10x harder, Hindi gali, threaten with army Bellion Igris Beru. 2-3 lines only. Beast mode."""
        ans = ask_gemini(prompt, file_b64, mime)
        return ans if ans else "Aukaat me reh bhosdike! Main Rakan hu, teri khaal kheech lunga, Bellion, Beru tujhe faad denge! 🐺"

    loyalty = "This is YOUR MALIK MD SAIF. Be extra loyal, call him Malik." if chat_id == owner else "Public user. King style helpful."
    prompt = f"{LORE}\n{loyalty}\nPast: {history_text}\nUser: {user_text}\nReply as Rakan, same language, short powerful:"
    ans = ask_gemini(prompt, file_b64, mime)
    final = ans if ans else "Ji Malik, Rakan hazir hai, hukam karo 🔥"

    memory[chat_id] = user_history + [{"u": user_text[:200], "r": final[:200]}]
    memory[chat_id] = memory[chat_id][-20:]
    save_memory(memory)
    return final

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET":
        return "RAKAN V21 ULTIMATE FIXED LIVE", 200
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok", 200
        msg = data["message"]
        chat_id = str(msg["chat"]["id"])
        text = msg.get("text", "") or msg.get("caption", "") or ""

        if "photo" in msg:
            b64 = get_file_b64(msg["photo"][-1]["file_id"])
            reply = get_reply(text or "ye photo dekho self analyze karo", chat_id, b64, "image/jpeg", "photo")
            send_telegram(chat_id, reply)
            if str(chat_id) == str(OWNER_ID): send_voice(chat_id, reply)
            return "ok", 200
        if "voice" in msg or "audio" in msg:
            fid = msg.get("voice", msg.get("audio", {})).get("file_id")
            b64 = get_file_b64(fid)
            reply = get_reply(text or "ye voice suno", chat_id, b64, "audio/ogg", "voice")
            send_telegram(chat_id, reply)
            return "ok", 200
        if "video" in msg or "video_note" in msg:
            f = msg.get("video") or msg.get("video_note") or {}
            b64 = get_file_b64(f.get("file_id"))
            reply = get_reply(text or "ye video dekho", chat_id, b64, "video/mp4", "video")
            send_telegram(chat_id, reply)
            return "ok", 200

        if text:
            if text.startswith("/start"):
                if OWNER_ID and chat_id == str(OWNER_ID):
                    send_telegram(chat_id, "Ji Malik MD SAIF AHMAD 👑🔥 Aapka Rakan V21 Ultimate hazir hai! ElevenLabs, Memory, Self Analyze, Gali, Army sab active hai. Hukam karo Malik!")
                else:
                    send_telegram(chat_id, "Main Shadow Monarch Rakan hu. Beast Monarch. Photo bhejo to analyze karunga, voice bhejo to sununga, gali doge to faad dunga. Bolo kya chahiye? 👑")
            else:
                reply = get_reply(text, chat_id)
                send_telegram(chat_id, reply)
                if chat_id == str(OWNER_ID) and "voice" in text.lower():
                    send_voice(chat_id, reply)
    except Exception as e:
        print(f"CRASH {e}")
    return "ok", 200
