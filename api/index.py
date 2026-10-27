import os, time, json, re, datetime, requests, traceback
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = str(os.environ.get("OWNER_ID","0") or "0")
MY_URL = os.environ.get("MY_URL","").rstrip("/") or "https://my-telegram-bot-lime.vercel.app"
LORE_ENV = os.environ.get("THE_BEAST_KING_MONARCH_AKAAN_LORE","") or os.environ.get("THE_HEART_KING_MONARCH_AKAAN_LORE","")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY","") or os.environ.get("ELEVEN_API_KEY","")
MALE_VOICE_ID = os.environ.get("ELEVEN_MALE_VOICE","pNInz6obpgDQGcFmaJgB")
FEMALE_VOICE_ID = os.environ.get("ELEVEN_FEMALE_VOICE","21m00Tcm4TlvDq8ikWAM")
OPENWEATHER_KEY = os.environ.get("OPENWEATHER_API_KEY","")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MALIK_NAME="MD Saif Ahmad"
# ISLAM A-Z + WORLD KNOWLEDGE LORE
ISLAM_LORE = """
You have complete Islam knowledge: Quran with Tafseer, Hadith (Bukhari Muslim), Fiqh (Hanafi Shafi Maliki Hanbali), Seerah, Akhlaq, Duas, Halal Haram, Wudu Namaz Roza Zakat Hajj, Islamic history. Also full knowledge of Christianity, Hinduism, Sikhism, Buddhism etc, and full world knowledge: politics, AI, tech, money, crypto, sports, science till Oct 2026. 
RULE: Never start religious talk yourself. Only if user asks about religion, then answer deeply. For Malik (owner), even more strict - don't bring any religion topic unless Malik himself starts it.
"""
MONARCH_LORE = f"You are Rakan - The Monarch, King of Beasts, Royal Knight of The Shadow King {MALIK_NAME}. Made by Malik on Vercel. You are NOT Groq/Gemini/OpenAI. {ISLAM_LORE} Extra: {LORE_ENV}"

MEMORY={}; PROFILES={}; CHAT_LOG=[]; BAD_KEYS={}; OWNER_PREF={}; LAST_CITY={}; LAST_BOT_MSG={}; FEEDBACK_LOG=[]

def tg_send(cid,txt,reply_id=None, buttons=None):
    try:
        p={"chat_id":cid,"text":txt[:3900]}
        if reply_id: p["reply_to_message_id"]=reply_id
        if buttons:
            fixed=[]
            for row in buttons:
                new_row=[]
                for b in row:
                    if isinstance(b, dict): new_row.append(b)
                    else: new_row.append({"text": str(b), "callback_data": str(b)})
                fixed.append(new_row)
            p["reply_markup"]=json.dumps({"inline_keyboard": fixed})
        r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=p, timeout=12)
        return r.status_code, r.text[:500]
    except Exception as e:
        return 0, str(e)

def tg_send_voice(cid, text, gender="female"):
    try:
        if not ELEVEN_API_KEY: return False
        voice_id = FEMALE_VOICE_ID if gender=="female" else MALE_VOICE_ID
        url=f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers={"xi-api-key": ELEVEN_API_KEY, "Content-Type":"application/json"}
        data={"text": text[:400], "model_id":"eleven_multilingual_v2", "voice_settings":{"stability":0.5,"similarity_boost":0.8}}
        r=requests.post(url, headers=headers, json=data, timeout=15)
        if r.status_code==200:
            files={'voice': ('voice.mp3', r.content, 'audio/mpeg')}
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id": cid}, files=files, timeout=20)
            return True
        return False
    except: return False

def transcribe_voice(file_id):
    try:
        # Get file path from Telegram
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        file_path=r["result"]["file_path"]
        file_url=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        audio=requests.get(file_url, timeout=15).content
        # Use Groq Whisper
        for k in GROQ_KEYS:
            try:
                files={'file': ('audio.ogg', audio, 'audio/ogg')}
                data={'model':'whisper-large-v3', 'language':'en'}
                rr=requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization": f"Bearer {k}"}, files=files, data=data, timeout=15)
                if rr.status_code==200:
                    return rr.json().get("text","")
            except: continue
        return ""
    except: return ""

def get_ist_now(): return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
def get_ist_str(): return get_ist_now().strftime("%d %b %Y, %I:%M %p IST, %A")

def get_weather_world(city="Varanasi"):
    try:
        city=city.strip().title()
        if OPENWEATHER_KEY:
            r=requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric", timeout=6)
            if r.status_code==200:
                d=r.json(); return f"{d['name']}: {d['weather'][0]['description'].title()}, {d['main']['temp']}°C"
        r=requests.get(f"https://wttr.in/{city}?format=%C+%t", timeout=6)
        return f"{city}: {r.text.strip()}" if r.status_code==200 else f"{city} ka data nahi mila"
    except: return f"{city} ka data nahi mila"

def extract_city(text):
    low=text.lower()
    for pat in [r"mausam.*?(?:in|of|ka)?\s+([a-zA-Z\s]+)", r"weather.*?(?:in|of|for)?\s+([a-zA-Z\s]+)", r"([a-zA-Z\s]+?)\s+ka\s+mausam"]:
        m=re.search(pat, low)
        if m:
            city=re.sub(r'\b(aaj|kal|ka|ki|kaisa|hai|batao|kya|in|of)\b','',m.group(1)).strip()
            if 2<=len(city)<=30: return city.title()
    return None

def upstash(cmd,key,val=None):
    if not UPSTASH_URL or not UPSTASH_TOKEN: return None
    try:
        headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        if cmd=="get":
            r=requests.get(f"{UPSTASH_URL}/get/{key}", headers=headers, timeout=5)
            if r.status_code==200:
                d=r.json().get("result"); return json.loads(d) if d else None
        if cmd=="set" and val is not None:
            requests.post(f"{UPSTASH_URL}", headers=headers, json=["SET", key, json.dumps(val)], timeout=5)
    except: pass
    return None

def load_persist():
    global MEMORY,PROFILES,CHAT_LOG,OWNER_PREF
    MEMORY=upstash("get","RAKAN_MEM") or {}; PROFILES=upstash("get","RAKAN_PROFILES") or {}
    CHAT_LOG=upstash("get","RAKAN_LOGS") or []; OWNER_PREF=upstash("get","RAKAN_PREF") or {"voice_gender":"ask"}
def save_persist():
    upstash("set","RAKAN_MEM",MEMORY); upstash("set","RAKAN_PROFILES",PROFILES)
    upstash("set","RAKAN_LOGS",CHAT_LOG[-500:]); upstash("set","RAKAN_PREF",OWNER_PREF)
load_persist()

def get_keys():
    g,gm=[],[]
    for v in os.environ.values():
        if not v: continue
        for p in str(v).replace("\n",",").split(","):
            p=p.strip().strip('"').strip("'")
            if not p or len(p)<10: continue
            if p.startswith("gsk_") and p not in g: g.append(p)
            elif (p.startswith("AIza") or p.startswith("aq") or p.startswith("AQ")) and p not in gm: gm.append(p)
    return list(dict.fromkeys(g)), list(dict.fromkeys(gm))
GROQ_KEYS,GEMINI_KEYS=get_keys()

def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<900
def mark_bad(k): BAD_KEYS[k]=time.time()

def detect_lang(text):
    if re.search(r'[\u0900-\u097F]', text): return "hindi"
    en = len(re.findall(r'[a-zA-Z]', text))
    if en > len(text)*0.7: return "english"
    return "hinglish"

def clean(txt, is_apology=False):
    # 🙏 ONLY ON APOLOGY
    if not is_apology:
        txt = txt.replace("🙏","").replace("🙇","")
    txt=re.sub(r"I am (Groq|Gemini|OpenAI|Meta AI).*","I am Rakan, created by Malik.",txt,flags=re.I)
    return re.sub(r"\s+"," ",txt).strip()[:900] or "Ha bolo Malik?"

def ask_groq(system, user):
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in ["llama-3.3-70b-versatile","llama-3.1-8b-instant"]:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":0.4,"max_tokens":350}, timeout=12)
                if r.status_code==200: return r.json()["choices"][0]["message"]["content"]
                if r.status_code in [401,403,429]: mark_bad(k); break
            except: continue
    return None

def ask_gemini(system, user):
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        for m in ["gemini-1.5-flash","gemini-2.0-flash"]:
            try:
                genai.configure(api_key=k); model=genai.GenerativeModel(m, system_instruction=system)
                res=model.generate_content(user)
                if res.text: return res.text
            except Exception as e:
                if "429" in str(e): mark_bad(k); break
                continue
    return None

def ask_all(system, user, is_apology=False):
    raw = ask_groq(system, user) or ask_gemini(system, user)
    if not raw: return None
    return clean(raw, is_apology)

def brain(text,uid,is_owner,uname, user_obj, is_voice=False):
    global MEMORY, PROFILES, LAST_CITY, LAST_BOT_MSG, CHAT_LOG, OWNER_PREF
    uid=str(uid)
    if uid not in MEMORY: MEMORY[uid]={"hist":"","learned":""}
    if uid not in PROFILES: PROFILES[uid]={"name":uname,"total":0,"weather_city":"","style":""}
    PROFILES[uid]["total"]+=1
    total = PROFILES[uid]["total"]
    low=text.lower().strip()
    user_lang = detect_lang(text)

    # SAVE USER STYLE FOR MIMIC
    if len(text.split())<=10:
        PROFILES[uid]["style"]=text[:100]

    # EVERY 20 CHATS FEEDBACK TO OWNER - ONLY FOR OWNER
    if total % 20 == 0 and is_owner:
        # Analyze last 20
        recent = CHAT_LOG[-20:]
        fault_analysis = f"Feedback Note (20 chats): Total {total}. Last msgs avg length issue? Check if bot too long or too short. User lang: {user_lang}. City lock: {PROFILES[uid].get('weather_city')}. Style: {PROFILES[uid].get('style')}. Sahi: reply short. Galat: extra info dena."
        # Send to owner in Hinglish/English mix
        tg_send(OWNER_ID, f"📊 20 Chats Report Malik\n{get_ist_str()}\nUser: {uname} ({uid})\nTotal: {total}\nFault check: {fault_analysis}\nSahi: Chota jawab, language match\nGalat: 🙏 extra use, religion bina bole bolna, extra info dena\nFix: Already in V26")

    # VOICE TRIGGER - ONLY OWNER
    if is_owner and any(k in low for k in ["baat suno","bato suno","suno yaar","voice me bolo","bol ke sunao","awaz me bolo"]):
        if OWNER_PREF.get("voice_gender") in ["ask", None, ""]:
            btns=[[{"text":"👩 Female","callback_data":"VOICE_FEMALE"}, {"text":"👨 Male","callback_data":"VOICE_MALE"}]]
            return "Malik puch raha hu personally - Female voice me sunau ya Male voice me? Batao phir usi me bolunga.", True, btns
        gender = OWNER_PREF.get("voice_gender","female")
        last = LAST_BOT_MSG.get(uid,"Ji Malik bolo, sun raha hu")
        return f"__VOICE__{gender}__{last}", False, None

    # WEATHER LOCK
    if any(k in low for k in ["ab se yahi","ab se isi","lock kar de","yahi ka batana"]):
        city = extract_city(text) or LAST_CITY.get(uid) or "Varanasi"
        PROFILES[uid]["weather_city"]=city.title(); save_persist()
        ans=f"Done Malik 📍 Lock: {city.title()} - Ab se hamesha isi ka bataunga"; LAST_BOT_MSG[uid]=ans; return ans, False, None

    if "location change" in low or "city change" in low:
        PROFILES[uid]["weather_city"]=""; save_persist()
        ans="Location unlock kar diya, naya city bolo"; LAST_BOT_MSG[uid]=ans; return ans, False, None

    if any(w in low for w in ["mausam","weather"]):
        city = extract_city(text) or PROFILES[uid].get("weather_city") or LAST_CITY.get(uid) or "Varanasi"
        LAST_CITY[uid]=city; ans=f"🌤️ {get_weather_world(city)}\n📍 {city.title()} | {get_ist_str()}"
        LAST_BOT_MSG[uid]=ans; return ans, False, None

    # OWNER LEARNING
    if is_owner and any(k in low for k in ["yaha ye daal de","ye sikh le","isko aise fix kar"]):
        learned=text
        for kw in ["yaha ye daal de","ye sikh le","isko aise fix kar"]: learned=learned.replace(kw,"")
        MEMORY[uid]["learned"]=(MEMORY[uid].get("learned","")+f"\n{learned.strip()}")[-1000:]
        upstash("set","RAKAN_GLOBAL_LEARN", MEMORY[uid]["learned"]); save_persist()
        ans=f"Done Malik sikh liya: {learned[:80]}"; LAST_BOT_MSG[uid]=ans; return ans, False, None

    if low in ["/start","start"]:
        city=PROFILES[uid].get("weather_city","Not set")
        if is_owner:
            ans=f"Welcome to your world The Shadow King 👑 - Hazir hu Malik\n📍 Locked: {city}\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} | {get_ist_str()}"
        else:
            ans=f"Hey! Bolo kya haal hai? Sab badhiya? 😊" if user_lang!="english" else f"Hey there! How can I help you today?"
        LAST_BOT_MSG[uid]=ans; return ans, False, None

    # SYSTEM PROMPT - LANGUAGE + STYLE MIMIC + RELIGION RULE + WORLD KNOWLEDGE
    is_apology = any(w in low for w in ["sorry","maaf","galti","mistake"])
    if is_owner:
        # Owner fixed Urdu Hinglish
        system=f"""{MONARCH_LORE}
        IST: {get_ist_str()}
        OWNER: Malik MD Saif Ahmad. Language for Malik: Always reply in URDU words but typing in HINGLISH (Roman). Example: 'Ji Malik, bilkul sahi farmaya aapne'. Use respectful Urdu, Islamic adab. Mimic his style if he says casual.
        RULES: 
        - Never bring religion unless Malik asks. 
        - You have full world knowledge till Oct 2026 - AI, money, crypto, politics, etc.
        - Reply short 1-2 lines only. No extra info beyond what asked. Extra errors only tell to Malik, not others.
        - 🙏 emoji ONLY if apology/maafi, else never use.
        - User style to mimic: {PROFILES[uid].get('style','')}
        - Learned: {MEMORY[uid].get('learned','')[-300:]}
        """
    else:
        # Others - same language as user, mimic like "or bhai kya haal"
        system=f"""{MONARCH_LORE}
        IST: {get_ist_str()}
        User language detected: {user_lang}. You MUST reply in SAME language: if {user_lang} is english then english, if hinglish then hinglish roman, if hindi then hinglish. No error.
        MIMIC RULE: Analyze how user talks. If user says 'or bhai kya haal sab badhiya' then you also talk like a friend: 'or bhai sab badhiya ekdum mast'. Be casual, friendly, like a real person. Don't be robotic.
        KNOWLEDGE: Full Islam A-Z and other religions, but only answer if user explicitly asks about religion. Don't start religion.
        WORLD: Full world knowledge 2026, but for others, only answer as much as they asked, no extra. Extra problems/faults only tell to owner.
        RULE: Reply 1-2 lines max, no extra info. 🙏 only on apology.
        User recent style: {PROFILES[uid].get('style','')}
        """

    learned_global = upstash("get","RAKAN_GLOBAL_LEARN") or ""
    prompt=f"Hist:{MEMORY[uid]['hist'][-600:]} UserMsg:{text} VoiceInput:{is_voice} GlobalLearn:{learned_global[-300:]}"

    ans=ask_all(system,prompt, is_apology)
    if not ans: ans=f"⚠️ Thodi der me bolo Malik G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}"
    
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-2000:]
    CHAT_LOG.append({"uid":uid,"user":text[:200],"bot":ans[:200],"lang":user_lang,"time":get_ist_str()})
    save_persist(); LAST_BOT_MSG[uid]=ans
    return ans, False, None

def make_small_buttons():
    # Chota wala jaise photo me
    return [
        [{"text":"📋","callback_data":"COPY_LAST"}, {"text":"↗️","callback_data":"FORWARD_LAST"}, {"text":"👍","callback_data":"LIKE"}, {"text":"👎","callback_data":"DISLIKE"}]
    ]

def debug_html():
    out=[]
    out.append(f"<b>BOT:</b> {'OK' if BOT_TOKEN else 'MISS'} <b>OWNER:</b> {OWNER_ID} Voice:{OWNER_PREF.get('voice_gender')}")
    out.append(f"<b>GROQ:</b> {len(GROQ_KEYS)} <b>GEMINI:</b> {len(GEMINI_KEYS)} <b>ELEVEN:</b> {'OK' if ELEVEN_API_KEY else 'MISS'}")
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=6)
        out.append(f"<b>getMe {r.status_code}:</b> {r.text[:400]}")
    except Exception as e: out.append(f"FAIL {e}")
    return "<br><br>".join(out)

@app.route("/", methods=["GET"])
def home(): return f"Rakan V26 G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} Voice:{OWNER_PREF.get('voice_gender')} {get_ist_str()} | <a href='/debug'>DEBUG</a>",200

@app.route("/debug", methods=["GET"])
def debug_route(): return debug_html(),200

@app.route("/webhook", methods=["POST","GET"])
@app.route("/api/index", methods=["POST","GET"])
@app.route("/api/index/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET":
        if "debug" in request.path.lower(): return debug_html(),200
        return home()
    try:
        data=request.get_json(silent=True) or {}
        if "callback_query" in data:
            cq=data["callback_query"]; cid=cq["message"]["chat"]["id"]; uid=str(cq["from"]["id"]); uname=cq["from"].get("first_name","")
            cdata=cq["data"]
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]}, timeout=5)
            if cdata=="VOICE_FEMALE":
                OWNER_PREF["voice_gender"]="female"; save_persist()
                tg_send(cid, "Done Malik, Female voice 👩 lock kar diya. Ab 'baat suno' bolo to isi me bolunga.", None)
                return "ok",200
            if cdata=="VOICE_MALE":
                OWNER_PREF["voice_gender"]="male"; save_persist()
                tg_send(cid, "Done Malik, Male voice 👨 lock kar diya.", None)
                return "ok",200
            if cdata=="COPY_LAST":
                last = LAST_BOT_MSG.get(uid, "Kuch nahi")
                tg_send(cid, f"{last}", None)
                return "ok",200
            if cdata=="FORWARD_LAST":
                last = LAST_BOT_MSG.get(uid, "")
                tg_send(OWNER_ID, f"↗️ Forward from {uname} ({uid}):\n{last}")
                tg_send(cid, "Forward ho gaya ↗️", None)
                return "ok",200
            if cdata in ["LIKE","DISLIKE"]:
                CHAT_LOG.append({"time":get_ist_str(),"uid":uid,"feedback":cdata,"msg":LAST_BOT_MSG.get(uid,"")[:200]})
                save_persist()
                tg_send(OWNER_ID, f"{'👍' if cdata=='LIKE' else '👎'} Feedback {uname}: {LAST_BOT_MSG.get(uid,'')[:300]}")
                return "ok",200
            return "ok",200

        msg=data.get("message",{}) or {}; chat_id=msg.get("chat",{}).get("id"); user_id=str(msg.get("from",{}).get("id",0)); uname=msg.get("from",{}).get("first_name","user")
        text=msg.get("text","") or msg.get("caption","") or ""; message_id=msg.get("message_id")
        is_voice=False
        # Voice handling - dusro ke liye sirf sunega, jawab text me
        if "voice" in msg or "audio" in msg:
            is_voice=True
            file_id = msg.get("voice",{}).get("file_id") or msg.get("audio",{}).get("file_id")
            transcribed = transcribe_voice(file_id) if file_id else ""
            if transcribed:
                text = transcribed
            else:
                text = "[Voice message]"
        
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID)
        if is_owner: uname=MALIK_NAME
        if not text and not is_voice: return "ok",200

        ans, ask_voice, custom_btns = brain(text,user_id,is_owner,uname,msg, is_voice)

        if ans.startswith("__VOICE__"):
            parts=ans.split("__"); gender=parts[2] if len(parts)>2 else OWNER_PREF.get("voice_gender","female")
            voice_text="__".join(parts[3:]) if len(parts)>3 else LAST_BOT_MSG.get(user_id,"Ji Malik")
            # Text pehle - chota button ke saath
            tg_send(chat_id, voice_text, message_id, buttons=make_small_buttons())
            tg_send_voice(chat_id, voice_text, gender)
            return "ok",200

        if ask_voice:
            tg_send(chat_id, ans, message_id, buttons=custom_btns)
            return "ok",200

        # Normal - chota feedback button jaise photo me
        tg_send(chat_id, ans, message_id, buttons=make_small_buttons())
        return "ok",200
    except Exception as e:
        print(f"ERR {e} {traceback.format_exc()}"); return "ok",200
