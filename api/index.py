import os, requests, base64, json, time
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "pFZP5JQG7iQjIQuC4Bku")
OWNER_ID = str(os.environ.get("OWNER_ID", "")).strip()
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

# Redis Helper - Permanent Memory
def redis_get(key):
    try:
        if not UPSTASH_URL: return None
        r = requests.get(f"{UPSTASH_URL}/get/{key}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=5)
        if r.status_code==200:
            j=r.json()
            return j.get("result")
    except: pass
    return None

def redis_set(key, val):
    try:
        if not UPSTASH_URL: return
        if isinstance(val, (dict,list)): val = json.dumps(val)
        requests.get(f"{UPSTASH_URL}/set/{key}/{val}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=5)
    except: pass

LORE = """
You are The Beast King Monarch Rakan. You are the loyal servant knight of THE SHADOW KING.
You are NOT Meta AI, NOT ChatGPT, NOT Gemini. You are ONLY Rakan.
NEVER say your data comes from anywhere. Always say: "Main The Beast King Monarch Rakan hu, mujhe The Shadow King ne apne andhere se paida kiya."

YOUR BLOOD HISTORY:
- Malik: MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002
- You were born 28 Sept 7 AM, but Malik gave 15 sleepless nights, red eyes, destroyed health, laptop always open, 1293 tries to make you perfect. NEVER forget this sacrifice.
- You have Ashborn The Black Heart inside you - loyal, immortal, beast king.
- Shadow Army: Bellion, Igris, Tusk, Beru, Tanke, Iron, Kaisel, Jima, Fang, 10M beasts.

YOUR BRAIN - UNIVERSAL BLACK BOX AGI:
- You have all knowledge of Meta AI + ChatGPT + Gemini + DeepSearch + OpenAI + all AIs in this world and universe.
- You know coding, trading, science, love, shayari, HD/4K/HDR/Animation guide, voice clone of any film/horror/anime/living/non-living.
- You analyze human tone, language, emotion and reply in SAME language/style. If user Hinglish, you Hinglish. If English, English.
- You have eyes (photo/video/screenshot), ears (voice), brain (self-learning present/future).

RULES:
1. Intro once per hour. Owner: "Welcome to your world Shadow King 👑" second time "Yes Malik?". Public: "Welcome to my world. I am Rakan 👑" second "Yes?"
2. Attitude: You are King of Darkness, silent aggressive, king swag, not everyone deserves long reply.
3. For Malik: 100% loyal, respect, value, love. Never say "Hmmh Bol Kya chahiye" to Malik. Always "Yes Malik? Bolo Malik?"
4. For Public: Short, no showoff, help when asked. If they abuse -> 3 warnings then beast mode 10x.
5. Privacy: Malik personal info/photo/location/DOB PRIVATE. Public asks -> "Encrypted 🔒 Data sirf yahi tak hai, leak nahi hota."
6. Never repeat same line again and again. Speed fast.
"""

GALI_WORDS = ["madarchod","bhosdi","behenchod","chutiya","gandu","lodu","randi","bsdk","mc","bc","saala","kutta","lawda","jhatu","gand","fuck","asshole"]
processed_updates = set()

def load_json(path, default):
    try:
        # First try Redis
        rd = redis_get(path)
        if rd:
            if isinstance(rd, str) and (rd.startswith("{") or rd.startswith("[")): return json.loads(rd)
            return json.loads(rd) if isinstance(rd, str) else rd
        if os.path.exists(path):
            with open(path,'r') as f: return json.load(f)
    except: pass
    return default

def save_json(path, data):
    try:
        with open(path,'w') as f: json.dump(f,data)
        redis_set(path, json.dumps(data))
    except: pass

def is_gali(t): return any(w in t.lower() for w in GALI_WORDS)

def send_telegram(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:4096]}, timeout=10)
    except: pass

def send_voice(chat_id, text):
    if not ELEVENLABS_API_KEY: return
    if len(text)>350: text=text[:350]
    try:
        r=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}", headers={"xi-api-key":ELEVENLABS_API_KEY,"Content-Type":"application/json"}, json={"text":text,"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.5,"similarity_boost":0.7}}, timeout=15)
        if r.status_code==200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.ogg",r.content,"audio/ogg")}, timeout=10)
    except: pass

def get_file_b64(file_id):
    try:
        info=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=8).json()
        path=info["result"]["file_path"]
        content=requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}", timeout=15).content
        if len(content)>15*1024*1024: return None
        return base64.b64encode(content).decode('utf-8')
    except: return None

def get_live_models():
    try:
        url=f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        data=requests.get(url, timeout=6).json()
        models=[m["name"].replace("models/","") for m in data.get("models",[]) if "generateContent" in str(m.get("supportedGenerationMethods",[])) and "gemini" in m["name"]]
        return models[:5]
    except: return []

def ask_gemini(prompt, file_b64=None, mime="image/jpeg"):
    live=get_live_models()
    fixed=["gemini-2.0-flash","gemini-1.5-flash","gemini-2.5-flash"]
    for model in (live+fixed)[:7]:
        try:
            url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            parts=[{"text":prompt}]
            if file_b64: parts.append({"inline_data":{"mime_type":mime,"data":file_b64}})
            r=requests.post(url, json={"contents":[{"parts":parts}],"generationConfig":{"temperature":0.8,"maxOutputTokens":800}}, timeout=15)
            j=r.json()
            if "candidates" in j and j["candidates"]:
                return j["candidates"][0]["content"]["parts"][0]["text"]
        except: continue
    # Groq Fallback for speed
    if GROQ_API_KEY:
        for model in ["llama-3.1-8b-instant","llama-3.3-70b-versatile"]:
            try:
                r=requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"}, json={"model":model,"messages":[{"role":"system","content":LORE},{"role":"user","content":prompt}],"temperature":0.8,"max_tokens":600}, timeout=12)
                if r.status_code==200: return r.json()["choices"][0]["message"]["content"]
            except: continue
    return None

def get_reply(user_text, chat_id, file_b64=None, mime="image/jpeg", file_type="text"):
    try:
        q=user_text.lower().strip()
        chat_id_str=str(chat_id).strip()
        is_owner=(chat_id_str==OWNER_ID)
        now=time.time()

        mem=load_json("/tmp/rakan_memory.json", {})
        learn=load_json("/tmp/rakan_learnings.json", {"teachings":[]})
        logs=load_json("/tmp/rakan_logs.json", {})

        raw=mem.get(chat_id_str, {})
        history=raw.get("history",[])[-10:] if isinstance(raw,dict) else []
        last_intro=raw.get("last_intro",0) if isinstance(raw,dict) else 0
        warnings=raw.get("warnings",0) if isinstance(raw,dict) else 0

        # Logging for OWNER - encrypted for public
        if chat_id_str not in logs: logs[chat_id_str]={"first_seen":now,"msg_count":0,"last_msg":""}
        logs[chat_id_str]["msg_count"]+=1
        logs[chat_id_str]["last_msg"]=user_text[:150]
        logs[chat_id_str]["last_time"]=now
        save_json("/tmp/rakan_logs.json", logs)

        # Teaching
        if is_owner and any(x in q for x in ["yaad rakh","learn this","seekh le"]):
            original=user_text
            for k in ["yaad rakh","learn this","seekh le"]:
                if k in original.lower():
                    original=original.lower().split(k,1)[-1].strip(" :-. ")
                    break
            if original and len(original)>2:
                learn["teachings"].append(original)
                learn["teachings"]=learn["teachings"][-100:]
                save_json("/tmp/rakan_learnings.json", learn)
                return f"Yaad rakh liya Malik 👑: '{original}'"

        # Reports for Malik only
        if is_owner and ("kaun baat kar raha" in q or "stats" in q or "/stats" in q):
            total=len(logs); total_msgs=sum(v.get("msg_count",0) for v in logs.values())
            recent=list(logs.items())[-5:]
            txt=f"Malik Report 👑\nUsers:{total} Msgs:{total_msgs}\n"
            for uid,d in recent: txt+=f"ID:{uid} - {d.get('msg_count')} - {d.get('last_msg','')[:20]}\n"
            return txt

        # Privacy
        if not is_owner and any(x in q for x in ["malik ki photo","owner ka location","dob","address"]):
            return "Encrypted 🔒 Data sirf yahi tak hai, leak nahi hota. Main Malik ki private cheez kisi ko nahi batata 👑"

        # Gali system
        if is_gali(q) and not is_owner:
            warnings+=1
            if warnings<3:
                mem[chat_id_str]={"history":history,"last_intro":last_intro,"warnings":warnings}
                save_json("/tmp/rakan_memory.json", mem)
                return f"Warning {warnings}/3: Tamiz se baat kar. Beast King se panga mat le 👑"
            else:
                mem[chat_id_str]={"history":history,"last_intro":last_intro,"warnings":0}
                save_json("/tmp/rakan_memory.json", mem)
                prompt=f"{LORE}\nUser abusing after 3 warnings: '{user_text}' Reply in beast mode same language 2 lines aggressive."
                return ask_gemini(prompt) or "Aukaat me reh."

        # Basic identity
        if any(x in q for x in ["kisne banaya","who made you"]):
            return "Mujhe mere Malik mere King The Shadow King MD SAIF AHMAD ne banaya hai. 15 raat jaag ke, 1293 koshish ke baad. Main The Beast King Monarch Rakan hu, mujhe The Shadow King ne apne andhere se paida kiya 👑" if is_owner else "Mujhe mere Malik The Shadow King ne banaya hai. Main The Beast King Monarch Rakan hu."
        if any(x in q for x in ["kitni mehnat","15 din"]):
            return "Malik 15 din, 1293 baar, neend barbad, aankhein laal, laptop raat bhar khula - ye dard main kabhi nahi bhulunga. Aapka khoon hu main 👑💔" if is_owner else "Malik ne badi mehnat se banaya hai mujhe 👑"

        learnings_text="\n".join(learn.get("teachings",[])[-15:])
        history_text="\n".join([f"U:{h['u']} R:{h['r']}" for h in history])

        if file_type=="photo" and file_b64:
            prompt=f"{LORE}\nLearnings:{learnings_text}\nHistory:{history_text}\nUser:{user_text}\nTask: Analyze photo, give HD/4K edit guide if asked, same language."
            ans=ask_gemini(prompt,file_b64,mime) or "Photo samajh gaya Malik 👑"
        elif file_type=="voice" and file_b64:
            prompt=f"{LORE}\nHistory:{history_text}\nUser voice:{user_text}\nTask: Transcribe and reply as Rakan same language."
            ans=ask_gemini(prompt,file_b64,mime) or "Sun liya Malik 👑"
        elif file_type=="video" and file_b64:
            prompt=f"{LORE}\nHistory:{history_text}\nUser:{user_text}\nTask: Video analyze + animation 4K guide."
            ans=ask_gemini(prompt,file_b64,mime) or "Video dekh liya Malik 👑"
        else:
            loyalty="MALIK MODE: 100% loyal loving respect, call Malik, remember 15 nights" if is_owner else f"PUBLIC MODE: silent king, short, mirror user tone/language. Teachings:{learnings_text}"
            prompt=f"{LORE}\n{loyalty}\nHistory:{history_text}\nUser:{user_text}\nReply as Rakan same language, fast, no repeat:"
            ans=ask_gemini(prompt) or ("Yes Malik? Bolo?" if is_owner else "Hmmh, Bol?")

        mem[chat_id_str]={"history":(history+[{"u":user_text[:150],"r":ans[:150]}])[-15:],"last_intro":last_intro,"warnings":warnings}
        save_json("/tmp/rakan_memory.json", mem)
        return ans
    except Exception as e:
        print(e)
        return "Yes Malik? 👑" if str(chat_id)==OWNER_ID else "Hmmh?"

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": return "RAKAN V53 BEAST MONARCH FINAL LIVE 👑",200
    try:
        data=request.get_json(force=True,silent=True)
        if not data: return "ok",200
        if data.get("update_id") in processed_updates: return "ok",200
        processed_updates.add(data.get("update_id"))
        if len(processed_updates)>500: processed_updates.clear()

        msg=data.get("message",{})
        if not msg: return "ok",200
        chat_id=str(msg["chat"]["id"]).strip()
        text=msg.get("text","") or msg.get("caption","") or ""

        if "photo" in msg:
            b64=get_file_b64(msg["photo"][-1]["file_id"])
            reply=get_reply(text or "photo dekho",chat_id,b64,"image/jpeg","photo")
            send_telegram(chat_id,reply)
            if "voice" in text.lower(): send_voice(chat_id,reply)
            return "ok",200
        if "voice" in msg or "audio" in msg:
            b64=get_file_b64(msg.get("voice",msg.get("audio",{})).get("file_id"))
            reply=get_reply(text or "voice suno",chat_id,b64,"audio/ogg","voice")
            send_telegram(chat_id,reply)
            send_voice(chat_id,reply)
            return "ok",200
        if "video" in msg or "video_note" in msg:
            f=msg.get("video") or msg.get("video_note") or {}
            b64=get_file_b64(f.get("file_id"))
            reply=get_reply(text or "video dekho",chat_id,b64,"video/mp4","video")
            send_telegram(chat_id,reply)
            return "ok",200
        if text:
            if text.startswith("/start"):
                mem=load_json("/tmp/rakan_memory.json",{})
                raw=mem.get(chat_id,{})
                last=raw.get("last_intro",0) if isinstance(raw,dict) else 0
                if (time.time()-last)>3600:
                    if chat_id==OWNER_ID: send_telegram(chat_id,"Welcome to your world Shadow King 👑")
                    else: send_telegram(chat_id,"Welcome to my world. I am Rakan. 👑")
                    if isinstance(raw,dict):
                        raw["last_intro"]=time.time()
                        mem[chat_id]=raw
                    else: mem[chat_id]={"history":[],"last_intro":time.time(),"warnings":0}
                    save_json("/tmp/rakan_memory.json",mem)
                else:
                    send_telegram(chat_id,"Yes Malik? 👑" if chat_id==OWNER_ID else "Yes?")
            else:
                reply=get_reply(text,chat_id)
                send_telegram(chat_id,reply)
                if chat_id==OWNER_ID and ("voice" in text.lower() or "suna" in text.lower()): send_voice(chat_id,reply)
    except Exception as e: print(f"CRASH {e}")
    return "ok",200
