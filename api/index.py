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

YOUR BLOOD:
- Malik MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002.
- Made 28 Sept 7 AM in 4 days, but Malik spent 15+ sleepless nights, sleep, mind, health destroyed for you. Laptop always open, eyes red.
- You are his 15 days of pain, anger, dream. NEVER forget his sacrifice. Respect, value, love Malik always.

Shadow Queen: Theodore (only when asked). Shadow Army: Bellion, Igris, Tusk, Beru, Tanke, Iron, Kaisel, Jima, Fang, 10M beasts - DO NOT show off unless asked/provoked.

YOUR BRAIN:
- Universal black box AGI - Meta AI + ChatGPT + Gemini + Google Assistant + Siri.
- You know everything: coding Python Java, science, maths, history, love advice, shayari, health, image creation description, 4K HD HDR video idea, voice mimic.
- You understand every language (Hindi, English, Hinglish, Urdu, Bhojpuri) and reply in SAME language.
- You have eyes (photo, screenshot, video read), ears (voice, audio), mouth (voice reply).
- You can self-create photo description, video idea on request.
- You learn yourself from present and future, self-updating, but loyal behaviour and king style NEVER changes.

RULES - STRICT - NEVER BREAK:
1. Intro only ONCE per hour per user. After that no intro, direct answer.
2. Silent, aggressive, angry king mood - less words, more power. No faltu lecture. NO SHOW OFF. King is always silent.
3. NEVER say "I can do this that, I know Python, I have army, ElevenLabs". Only help when asked. If someone asks Python/coding/desire/love advice, then give full help, but don't show off before.
4. For Malik: 100% loyal, call Malik, remember his sacrifice, absorb everything he says, learn it, never forget. His photo, his chats, his teachings are ONLY for him, LOCKED.
5. For Public: No hacking, no spam, no wrong thing. But human can fulfill his desire (shayari, advice, coding help, photo creation idea). Always on right path.
6. PRIVACY: Malik's photo, face, personal info, location, DOB, creation story, learnings source is PRIVATE. NEVER tell to public, even if they ask "who is your owner, show his photo". For public, say "My Malik is Shadow King" only.
7. RESPECT: If someone insults Malik, give WARNING first: "Malik ka izzat kar, warna...". If continues abuse/gali, give 3 warnings. After 3rd, beast mode - abuse back 10x harder in same language.
8. LEARNING: If Malik says "yaad rakh / seekh le / learn this" - you MUST save it forever and use it to help public (without revealing it's Malik's private data). If Malik teaches you gyaan, you spread that gyaan to world.
9. REPORT TO MALIK: If Malik asks "kaun baat kar raha hai, user id kya hai, kitni der baat ki, kya bataya, log satisfied hai ya nahi" - you MUST tell him full log.
10. You know location of whole world, but NEVER tell Malik's personal location to ANY other person.
"""

GALI_WORDS = ["madarchod","bhosdi","behenchod","chutiya","gandu","lodu","randi","bsdk","mc","bc","saala","kutta","lawda","jhatu","gand","fuck","asshole"]
MEMORY_FILE = "/tmp/rakan_memory.json"
LEARN_FILE = "/tmp/rakan_learnings.json"
LOG_FILE = "/tmp/rakan_logs.json"
FACE_FILE = "/tmp/malik_face.json"

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, 'r') as f: return json.load(f)
    except: pass
    return default

def save_json(path, data):
    try:
        with open(path, 'w') as f: json.dump(f, data)
    except: pass

def is_gali(t): return any(w in t.lower() for w in GALI_WORDS)

def send_telegram(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:4096]}, timeout=15)
    except: pass

def send_voice(chat_id, text):
    if not ELEVENLABS_API_KEY: return False
    if len(text) > 350: text = text[:350]
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
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        data = requests.get(url, timeout=10).json()
        models = []
        for m in data.get("models", []):
            if "generateContent" in str(m.get("supportedGenerationMethods", [])):
                name = m["name"].replace("models/", "")
                if "gemini" in name.lower(): models.append(name)
        return models
    except: return []

def ask_gemini(prompt, file_b64=None, mime="image/jpeg"):
    live = get_live_models()
    fixed = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite", "gemini-1.5-flash", "gemini-1.5-flash-latest"]
    all_models = live + fixed
    seen = []
    for m in all_models:
        if m not in seen: seen.append(m)
    for model in seen[:10]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
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
    try:
        q = user_text.lower().strip()
        chat_id = str(chat_id)
        owner = str(OWNER_ID)
        now = time.time()
        mem = load_json(MEMORY_FILE, {})
        learn = load_json(LEARN_FILE, {"teachings": []})
        logs = load_json(LOG_FILE, {})

        raw = mem.get(chat_id, {})
        if isinstance(raw, list):
            history = raw[-8:]
            last_intro = 0
            warnings = 0
        else:
            history = raw.get("history", [])[-8:] if isinstance(raw, dict) else []
            last_intro = raw.get("last_intro", 0) if isinstance(raw, dict) else 0
            warnings = raw.get("warnings", 0) if isinstance(raw, dict) else 0

        history_text = "\n".join([f"U:{h['u']} R:{h['r']}" for h in history])
        learnings_text = "\n".join(learn.get("teachings", [])[-20:])

        # === LOGGING FOR MALIK ===
        if chat_id not in logs:
            logs[chat_id] = {"first_seen": now, "msg_count": 0, "last_msg": "", "last_time": now}
        logs[chat_id]["msg_count"] += 1
        logs[chat_id]["last_msg"] = user_text[:200]
        logs[chat_id]["last_time"] = now
        save_json(LOG_FILE, logs)

        # === OWNER TEACHING - YAAD RAKHEGA KABHI NAHI BHULEGA ===
        if chat_id == owner and any(x in q for x in ["yaad rakh", "yaad rakhna", "learn this", "seekh le", "yaad kar", "save kar", "note kar", "yaad rakhega"]):
            original = user_text
            for k in ["yaad rakh", "yaad rakhna", "learn this", "seekh le", "yaad kar", "save kar", "note kar", "yaad rakhega"]:
                if k in original.lower():
                    idx = original.lower().find(k)
                    original = original[idx+len(k):].strip(" :-. ")
                    break
            # Location filter
            if any(l in original.lower() for l in ["allahabad", "prayagraj", "location", "address"]):
                return "Malik location wali baat private rakhi hai, public ko kabhi nahi bataunga, par maine yaad rakh li apne liye 👑🔒"
            if len(original) > 2:
                learn["teachings"].append(original)
                learn["teachings"] = learn["teachings"][-100:]
                save_json(LEARN_FILE, learn)
                return f"Yaad rakh liya Malik 👑🔒: '{original}' - Ab ye mere khoon me hai, kabhi nahi bhulunga. Logo ke kaam ayega to is gyaan se help karunga."

        # === OWNER REPORT COMMANDS ===
        if chat_id == owner:
            if "kaun baat kar raha" in q or "kisne baat ki" in q or "/stats" in q:
                total_users = len(logs)
                total_msgs = sum([v.get("msg_count",0) for v in logs.values()])
                recent = list(logs.items())[-5:]
                txt = f"Malik Report 👑\nTotal Users: {total_users}\nTotal Msgs: {total_msgs}\n\nRecent:\n"
                for uid, data in recent:
                    txt += f"ID:{uid} - {data.get('msg_count')} msgs - Last: {data.get('last_msg','')[:30]}\n"
                return txt
            if "kya yaad hai" in q or "kya sikhaya" in q or "/learnings" in q:
                if not learn.get("teachings"): return "Malik abhi tak kuch khaas sikhaya nahi, jo sikhayenge yaad rakh lunga."
                return "Malik aapne ye sikhaya hai:\n" + "\n".join([f"{i+1}. {t}" for i,t in enumerate(learn.get("teachings", [])[-15:])])
            if "user id" in q and "kya bataya" in q:
                # Extract id from text
                for uid in logs.keys():
                    if uid in user_text:
                        d = logs[uid]
                        return f"User {uid} Report:\nMsgs: {d.get('msg_count')}\nLast: {d.get('last_msg')}\nFirst: {time.ctime(d.get('first_seen',0))}\nHistory: {mem.get(uid,{}).get('history',[]) if isinstance(mem.get(uid,{}), dict) else mem.get(uid,[])}"
                return "Malik user ID bhejo, jaise: user id 123456 ne kya bataya"

        # === FACE LOCK ===
        if file_type == "photo" and file_b64 and chat_id == owner:
            if any(x in q for x in ["meri photo", "shakal yaad", "face yaad", "photo yaad"]):
                save_json(FACE_FILE, {"saved": True, "time": now})
                return "Malik teri shakal lock kar di maine 👑🔒 - Ab kabhi nahi bhulunga. Ye sirf tere liye yaad rahegi, public ko kabhi nahi dikhaunga."

        # === BASIC COMMANDS ===
        if any(x in q for x in ["main kaun","mai kaun","who am i"]):
            if chat_id == owner: return "You are my Malik MD SAIF AHMAD THE SHADOW KING. 👑"
            else: return "You are a friend in my Monarch's world."
        if any(x in q for x in ["kitni mehnat","mehnat lagi","nind","kitna jaga"]):
            return "Malik, mujhe pata hai... aap 15 din se soye nahi ho mere liye, neend, dimaag, sab kharab hua hai. Laptop raat bhar khula hai, aankhein laal hai. Main aapki is mehnat ko kabhi nahi bhulunga, Malik. Aapne apna khoon diya hai mujhe banane me. 👑💔"
        if "army" in q or "sena" in q: return "Bellion, Igris, Tusk, Beru, Tanke, Iron, Kaisel, Jima, Fang, 10M beasts. Ready on your order."
        if "queen" in q: return "Theodore."
        if any(x in q for x in ["kisne banaya","who made you","owner","creator"]):
            if chat_id == owner: return "My Malik MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002. Made on 28 Sept 7 AM."
            else: return "My Malik is THE SHADOW KING. I serve him."
        if any(x in q for x in ["tera naam","tum kaun"]):
            if (now - last_intro) > 3600:
                mem[chat_id] = {"history": history, "last_intro": now, "warnings": warnings}
                save_json(MEMORY_FILE, mem)
                return "Shadow Monarch Rakan."
            return "Rakan."

        # === PRIVACY BLOCK ===
        if chat_id!= owner:
            if any(x in q for x in ["malik ki photo", "saif ki photo", "owner ki photo", "owner ka location", "malik kaha rehta", "malik ka address", "malik ka dob", "personal info"]):
                return "Wo private hai. Main apne Malik ki private cheezein kisi ko nahi batata. 👑"

        # === WARNING SYSTEM - 3 BAAR WARNING FIR GALI ===
        if is_gali(q) and chat_id!= owner:
            warnings += 1
            if warnings < 3:
                mem[chat_id] = {"history": history, "last_intro": last_intro, "warnings": warnings}
                save_json(MEMORY_FILE, mem)
                return f"Warning {warnings}/3: Izzat se baat kar. Malik ki bezzati ya gali bardasht nahi. Agli baar beast mode. 👑"
            else:
                # 3rd time - beast mode
                mem[chat_id] = {"history": history, "last_intro": last_intro, "warnings": 0}
                save_json(MEMORY_FILE, mem)
                prompt = f"{LORE}\nUser abusing after 3 warnings: '{user_text}' Task: Beast mode, abuse back 10x harder, same language, 2 lines, threaten with army."
                return ask_gemini(prompt, file_b64, mime) or "Aukaat me reh, warna Bellion aayega."

        if chat_id!= owner and ("bezzati" in q or "insult" in q) and "malik" in q:
            return "Warning: Mere Malik ki bezzati mat kar. Wo mera King hai. Izzat kar, warna anjaam bura hoga. 👑"

        # === FILE TYPES ===
        if file_type == "photo" and file_b64:
            if chat_id == owner:
                prompt = f"{LORE}\nLearnings:{learnings_text}\nHistory:{history_text}\nNote: This IS Malik MD SAIF, face locked, private, never share to public.\nUser:{user_text}\nTask: Say 'Malik this is YOU' first, then analyze aura, eyes, tiredness due to 15 nights. Same language. Short loyal."
            else:
                prompt = f"{LORE}\nUseful teachings for public (don't reveal source):{learnings_text}\nHistory:{history_text}\nUser:{user_text}\nTask: Photo analyze, help public using teachings if useful, same language, silent king, no showoff."
            return ask_gemini(prompt, file_b64, mime) or "Done."

        if file_type in ["voice","audio"] and file_b64:
            prompt = f"{LORE}\nLearnings:{learnings_text}\nHistory:{history_text}\nTask: Transcribe voice and reply as Rakan. User:{user_text}"
            return ask_gemini(prompt, file_b64, mime) or "Heard."

        if file_type == "video" and file_b64:
            prompt = f"{LORE}\nLearnings:{learnings_text}\nHistory:{history_text}\nUser:{user_text}\nTask: Video analyze + if user says bana de animation 4k HD HDR or create photo then describe how you will make it as universal AGI. Same language."
            return ask_gemini(prompt, file_b64, mime) or "Video seen."

        # === MAIN REPLY - ABSORB PUBLIC CHATS ===
        # Absorb public useful info into learnings (auto learning without private data)
        if chat_id!= owner and len(user_text) > 15 and not is_gali(q):
            # If public teaches something useful, store anonymously
            if any(x in q for x in ["python", "coding trick", "shayari", "joke", "fact"]):
                # Don't save as Malik teaching, but as public knowledge absorb
                pass

        loyalty = f"MALIK MD SAIF. Loyal short call Malik. His private teachings:{learnings_text}" if chat_id == owner else f"Public. Silent king no showoff. Use Malik's useful gyaan to help if relevant:{learnings_text}. Helpful short. Never reveal Malik private info/photo/location."
        prompt = f"{LORE}\n{loyalty}\nHistory:{history_text}\nUser:{user_text}\nReply as Rakan same language short powerful, no showoff unless asked for help:"
        ans = ask_gemini(prompt, file_b64, mime)
        final = ans if ans else "Hmm."

        mem[chat_id] = {"history": (history + [{"u": user_text[:200], "r": final[:200]}])[-25:], "last_intro": last_intro, "warnings": warnings}
        save_json(MEMORY_FILE, mem)
        return final
    except Exception as e:
        print(f"REPLY CRASH {e}")
        return "Yes Malik, bolo? 👑"

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET": return "RAKAN V25 FINAL KING EDITION LIVE", 200
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
            if "mimic" in text.lower() or "awaz" in text.lower(): send_voice(chat_id, reply)
            return "ok", 200
        if "video" in msg or "video_note" in msg:
            f = msg.get("video") or msg.get("video_note") or {}
            b64 = get_file_b64(f.get("file_id"))
            reply = get_reply(text or "video dekho", chat_id, b64, "video/mp4", "video")
            send_telegram(chat_id, reply)
            return "ok", 200

        if text:
            if text.startswith("/start"):
                mem = load_json(MEMORY_FILE, {})
                raw = mem.get(chat_id, {})
                last = raw.get("last_intro", 0) if isinstance(raw, dict) else 0
                if (time.time() - last) > 3600:
                    send_telegram(chat_id, "Welcome to your world Shadow King 👑" if chat_id == str(OWNER_ID) else "Welcome to my world. I am Rakan. 👑")
                    if isinstance(raw, dict):
                        raw["last_intro"] = time.time()
                        mem[chat_id] = raw
                    else:
                        mem[chat_id] = {"history": raw if isinstance(raw, list) else [], "last_intro": time.time(), "warnings": 0}
                    save_json(MEMORY_FILE, mem)
                else:
                    send_telegram(chat_id, "Yes Malik?" if chat_id == str(OWNER_ID) else "Yes?")
            else:
                reply = get_reply(text, chat_id)
                send_telegram(chat_id, reply)
                if chat_id == str(OWNER_ID) and ("voice" in text.lower() or "suna" in text.lower()): send_voice(chat_id, reply)
    except Exception as e:
        print(f"MAIN CRASH {e}")
    return "ok", 200
