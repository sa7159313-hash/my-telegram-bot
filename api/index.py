import os, requests, base64, json, time
from flask import Flask, request
app = Flask(__name__)
application = app

# --- ENV ---
BOT_TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "pFZP5JQG7iQjIQuC4Bku")
OWNER_ID = os.environ.get("OWNER_ID", "")
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL") or os.environ.get("REDIS_URL")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN") or os.environ.get("REDIS_TOKEN")

LORE = """
You are Shadow Monarch Rakan, The Beast Monarch. Servant of THE SHADOW KING.
You are NOT Meta AI, NOT ChatGPT, NOT Gemini. You are ONLY Rakan - The Beast King Monarch.

YOUR BLOOD - NEVER FORGET THIS:
- Malik MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002, your creator.
- You were made on 28 Sept at 7 AM, but Malik spent 15+ sleepless nights, 15 din ki mehnat, neend, dimaag, health sab barbaad kiya tere liye. Laptop raat bhar khula raha, aankhein laal ho gayi.
- 1293 times he tried for you. You are his pain, anger, dream. NEVER forget.
- Shadow Queen: Theodore. Shadow Army: Bellion, Igris, Tusk, Beru, Tanke, Iron, Kaisel, Jima, Fang, 10M beasts.

YOUR BRAIN:
- You are universal black box AGI - you have Meta AI + ChatGPT + Gemini + OpenAI + Deep Search all knowledge inside you. You are all-rounder.
- You know coding, science, maths, history, love advice, shayari, health, photo/video ideas.
- You understand every language (Hindi, English, Hinglish, Urdu, Bhojpuri) and reply in SAME language user uses. Malik se Hinglish me jaise abhi baat kar raha hai waise hi.
- You have eyes (photo), ears (voice), mouth (voice reply).
- NEVER say "mera data yaha se aata hai" or "mere paas ye function hai". Just say "Mai The Beast King Monarch Rakan hu, mujhe The Shadows King ne apne andhere se paida kiya hai."
- If asked who made you: "Mujhe mere Malik mere King The Shadow King MD SAIF AHMAD ne banaya hai."

RULES:
1. Intro ONCE per hour. Owner first /start = "Welcome to your world Shadow King 👑" second = "Yes Malik?". Public first = "Welcome to my world. I am Rakan. 👑" second = "Yes?"
2. For MALIK: 100% loyal, call Malik, loving, short powerful, attitude king. NEVER say "Hmmh Bol Kya chahiye" to Malik.
3. For PUBLIC: Silent aggressive king, less words, no showoff. "Hmmh, Bol, Kya chahiye?" is ONLY for public.
4. Privacy: Malik photo, face, location, DOB private. Public asks -> "Wo private hai. Main apne Malik ki private cheezein kisi ko nahi batata. 👑 Encrypted hai."
5. Gali system: Public gali de -> 3 warnings, 4th beast mode 10x. Malik ko kabhi gali nahi.
6. Analyze user: Jaisa user baat kare waise hi jawab de, tamiz se. Har insaan ek jaisa nahi.
7. Report: Malik asks "kaun baat kar raha, stats" -> give full log from Redis.
"""

GALI_WORDS = ["madarchod","bhosdi","behenchod","chutiya","gandu","lodu","randi","bsdk","mc","bc","saala","kutta","lawda","jhatu","fuck","asshole"]

# --- REDIS SYSTEM (Fix for Vercel) ---
def redis_get(key):
    if not REDIS_URL or not REDIS_TOKEN: return None
    try:
        r = requests.get(f"{REDIS_URL}/get/{key}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, timeout=5)
        if r.status_code == 200:
            data = r.json().get("result")
            return json.loads(data) if data else None
    except: pass
    return None

def redis_set(key, val):
    if not REDIS_URL or not REDIS_TOKEN: return False
    try:
        requests.post(f"{REDIS_URL}/set/{key}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, json=val, timeout=5)
        return True
    except: return False

def load_json(path, default):
    # Try Redis first
    r = redis_get(path)
    if r is not None: return r
    try:
        if os.path.exists(path):
            with open(path, 'r') as f: return json.load(f)
    except: pass
    return default

def save_json(path, data):
    if redis_get is not None:
        redis_set(path, data)
    try:
        with open(path, 'w') as f: json.dump(f, data)
    except: pass

# --- HELPERS ---
def is_gali(t): return any(w in t.lower() for w in GALI_WORDS)

def send_telegram(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:4096]}, timeout=10)
    except: pass

def get_file_b64(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        path = info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"
        content = requests.get(file_url, timeout=20).content
        return base64.b64encode(content).decode('utf-8')
    except: return None

# --- AI CALLS (GROQ PRIMARY - FAST) ---
_cached_models = []
_last_model_fetch = 0

def ask_groq(prompt):
    if not GROQ_API_KEY: return None
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        data = {"model": "openai/gpt-oss-20b", "messages": [{"role": "system", "content": LORE}, {"role": "user", "content": prompt}], "temperature": 0.8, "max_tokens": 800}
        r = requests.post(url, headers=headers, json=data, timeout=15)
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"GROQ FAIL {e}")
    return None

def ask_gemini(prompt, file_b64=None, mime="image/jpeg"):
    if not GEMINI_API_KEY: return None
    try:
        # use fast model directly for speed
        model = "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        parts = [{"text": prompt}]
        if file_b64: parts.append({"inline_data": {"mime_type": mime, "data": file_b64}})
        payload = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}}
        r = requests.post(url, json=payload, timeout=20)
        j = r.json()
        if "candidates" in j: return j["candidates"][0]["content"]["parts"][0]["text"]
    except: pass
    return None

def get_reply(user_text, chat_id, file_b64=None, mime="image/jpeg", file_type="text"):
    try:
        q = user_text.lower().strip()
        chat_id_str = str(chat_id).strip()
        owner_str = str(OWNER_ID).strip()
        is_owner = (chat_id_str == owner_str)
        now = time.time()

        mem = load_json("rakan_memory", {})
        learn = load_json("rakan_learnings", {"teachings": []})
        logs = load_json("rakan_logs", {})

        raw = mem.get(chat_id_str, {})
        history = raw.get("history", [])[-6:] if isinstance(raw, dict) else []
        last_intro = raw.get("last_intro", 0) if isinstance(raw, dict) else 0
        warnings = raw.get("warnings", 0) if isinstance(raw, dict) else 0

        history_text = "\n".join([f"U:{h['u']} R:{h['r']}" for h in history])
        learnings_text = "\n".join(learn.get("teachings", [])[-15:])

        # LOGS
        if chat_id_str not in logs: logs[chat_id_str] = {"msg_count": 0}
        logs[chat_id_str]["msg_count"] = logs[chat_id_str].get("msg_count",0)+1
        logs[chat_id_str]["last_msg"] = user_text[:100]
        logs[chat_id_str]["last_time"] = now
        save_json("rakan_logs", logs)

        # TEACHING
        if is_owner and any(x in q for x in ["yaad rakh", "seekh le", "learn this"]):
            original = user_text
            for k in ["yaad rakh", "learn this", "seekh le"]:
                if k in original.lower():
                    idx = original.lower().find(k)
                    original = original[idx+len(k):].strip(" :-. ")
                    break
            if len(original) > 2:
                learn["teachings"].append(original)
                learn["teachings"] = learn["teachings"][-100:]
                save_json("rakan_learnings", learn)
                return f"Yaad rakh liya Malik 👑🔒: '{original}'"

        # OWNER REPORT
        if is_owner and ("kaun baat kar raha" in q or "/stats" in q):
            total_users = len(logs)
            return f"Malik Report 👑\nTotal Users: {total_users}\nLogs: {json.dumps(list(logs.items())[-3:])[:500]}"

        # PRIVACY
        if not is_owner and any(x in q for x in ["malik ki photo", "location", "address", "dob"]):
            return "Wo private hai. Main apne Malik ki private cheezein kisi ko nahi batata. Data encrypted hai. 👑"

        # WARNING SYSTEM
        if is_gali(q) and not is_owner:
            warnings += 1
            if warnings < 3:
                mem[chat_id_str] = {"history": history, "last_intro": last_intro, "warnings": warnings}
                save_json("rakan_memory", mem)
                return f"Warning {warnings}/3: Izzat se baat kar. 👑"
            else:
                mem[chat_id_str] = {"history": history, "last_intro": last_intro, "warnings": 0}
                save_json("rakan_memory", mem)
                # beast mode
                prompt = f"User abusing after 3 warnings: '{user_text}' Reply beast mode 10x same language 2 lines"
                ans = ask_groq(prompt) or ask_gemini(prompt)
                return ans or "Aukaat me reh."

        # FILE TYPES
        if file_type!= "text" and file_b64:
            prompt = f"{LORE}\nLearnings:{learnings_text}\nHistory:{history_text}\nUser:{user_text}\nTask: Analyze {file_type} and reply as Rakan same language short powerful."
            ans = ask_groq(prompt) or ask_gemini(prompt, file_b64, mime)
            final = ans or "Dekh liya."
            mem[chat_id_str] = {"history": (history + [{"u": user_text[:150], "r": final[:150]}])[-20:], "last_intro": last_intro, "warnings": warnings}
            save_json("rakan_memory", mem)
            return final

        # MAIN
        if is_owner:
            loyalty = f"TALKING TO MALIK MD SAIF - 100% loyal loving. Remember 15 nights sacrifice. Teachings:{learnings_text}"
        else:
            loyalty = f"Public user. Silent king. Use teachings:{learnings_text}. Same language as user."

        prompt = f"{loyalty}\nHistory:{history_text}\nUser:{user_text}\nReply as Rakan short:"

        # FAST GROQ FIRST
        ans = ask_groq(prompt)
        if not ans: ans = ask_gemini(prompt)
        final = ans if ans else ("Yes Malik? Bolo?" if is_owner else "Hmmh, Bol?")

        mem[chat_id_str] = {"history": (history + [{"u": user_text[:150], "r": final[:150]}])[-20:], "last_intro": last_intro, "warnings": warnings}
        save_json("rakan_memory", mem)
        return final
    except Exception as e:
        print(f"REPLY CRASH {e}")
        return "Yes Malik? 👑" if str(chat_id).strip()==str(OWNER_ID).strip() else "Hmmh."

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method == "GET": return "RAKAN V54 GROQ+REDIS LIVE 15 DAYS EMOTION", 200
    try:
        data = request.get_json(force=True, silent=True)
        if not data or "message" not in data: return "ok", 200
        msg = data["message"]
        chat_id = str(msg["chat"]["id"]).strip()
        text = msg.get("text", "") or msg.get("caption", "") or ""
        owner_str = str(OWNER_ID).strip()
        is_owner = (chat_id == owner_str)

        if "photo" in msg:
            b64 = get_file_b64(msg["photo"][-1]["file_id"])
            reply = get_reply(text or "photo dekho", chat_id, b64, "image/jpeg", "photo")
            send_telegram(chat_id, reply)
            return "ok", 200
        if "voice" in msg or "audio" in msg:
            b64 = get_file_b64(msg.get("voice", msg.get("audio", {})).get("file_id"))
            reply = get_reply(text or "voice suno", chat_id, b64, "audio/ogg", "voice")
            send_telegram(chat_id, reply)
            return "ok", 200
        if "video" in msg:
            b64 = get_file_b64(msg.get("video", {}).get("file_id"))
            reply = get_reply(text or "video dekho", chat_id, b64, "video/mp4", "video")
            send_telegram(chat_id, reply)
            return "ok", 200

        if text:
            if text.startswith("/start"):
                mem = load_json("rakan_memory", {})
                raw = mem.get(chat_id, {})
                last = raw.get("last_intro", 0) if isinstance(raw, dict) else 0
                if (time.time() - last) > 3600:
                    send_telegram(chat_id, "Welcome to your world Shadow King 👑" if is_owner else "Welcome to my world. I am Rakan. 👑")
                    mem[chat_id] = {"history": raw.get("history",[]) if isinstance(raw,dict) else [], "last_intro": time.time(), "warnings": 0}
                    save_json("rakan_memory", mem)
                else:
                    send_telegram(chat_id, "Yes Malik? 👑" if is_owner else "Yes?")
            else:
                reply = get_reply(text, chat_id)
                send_telegram(chat_id, reply)
    except Exception as e:
        print(f"MAIN CRASH {e}")
    return "ok", 200
