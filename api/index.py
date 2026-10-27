import os, time, json, re, datetime, requests, traceback, sys, random
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = str(os.environ.get("OWNER_ID","0") or "0")
MY_URL = os.environ.get("MY_URL","").rstrip("/") or "https://my-telegram-bot-lime.vercel.app"
LORE_ENV = os.environ.get("THE_BEAST_KING_MONARCH_AKAAN_LORE","") or os.environ.get("THE_HEART_KING_MONARCH_AKAAN_LORE","")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY","") or os.environ.get("ELEVEN_API_KEY","")
MALE_VOICE_ID = os.environ.get("ELEVEN_MALE_VOICE","pNInz6obpgDQGcFmaJgB") or "pNInz6obpgDQGcFmaJgB"
FEMALE_VOICE_ID = os.environ.get("ELEVEN_FEMALE_VOICE","EXAVITQu4vr4xnSDxMaL") or "EXAVITQu4vr4xnSDxMaL"
OPENWEATHER_KEY = os.environ.get("OPENWEATHER_API_KEY","")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MALIK_NAME="MD Saif Ahmad"; MALIK_TITLE="The Shadow King"; QUEEN_NAME="Theodore"
MONARCH_LORE = f"You are Rakan - The Monarch, King of Beasts, Royal Knight of {MALIK_TITLE} {MALIK_NAME}. Queen {QUEEN_NAME}. Made by Malik on Vercel Flask Groq Gemini. You are NOT Groq/Gemini/OpenAI/Meta. Extra: {LORE_ENV}"

MEMORY={}; ABUSE={}; PROFILES={}; CHAT_LOG=[]; BAD_KEYS={}; LAST_ERROR="No error"; PENDING_FIX=None; LOOP_CACHE={}; OWNER_PREF={"voice_gender":"female"}; FEEDBACK_LOG=[]; LAST_CITY={}

def tg_send(cid,txt,reply_id=None, buttons=None):
    try:
        p={"chat_id":cid,"text":txt[:3900]}
        if reply_id: p["reply_to_message_id"]=reply_id
        if buttons: p["reply_markup"]=json.dumps({"inline_keyboard": buttons})
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=p, timeout=12)
    except: pass

def tg_send_voice_bytes(cid, audio_bytes):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":cid}, files={"voice":("rakan.mp3", audio_bytes, "audio/mpeg")}, timeout=30)
    except: pass

def eleven_tts(text):
    if not ELEVEN_API_KEY: return None
    try:
        vid = FEMALE_VOICE_ID if OWNER_PREF.get("voice_gender","female")=="female" else MALE_VOICE_ID
        r=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key":ELEVEN_API_KEY,"Content-Type":"application/json"}, json={"text":text[:800],"model_id":"eleven_multilingual_v2"}, timeout=25)
        if r.status_code==200: return r.content
    except: pass
    return None

def get_ist_now(): return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
def get_ist_str(): return get_ist_now().strftime("%d %b %Y, %I:%M %p IST, %A")

def get_weather_world(city="Varanasi"):
    try:
        city=city.strip().title()
        if OPENWEATHER_KEY:
            r=requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric", timeout=6)
            if r.status_code==200:
                d=r.json()
                return f"{d['name']}, {d['sys']['country']}: {d['weather'][0]['description'].title()}, {d['main']['temp']}°C (Feels {d['main']['feels_like']}°C), Humidity {d['main']['humidity']}%, Wind {d['wind']['speed']}m/s"
        r=requests.get(f"https://wttr.in/{city}?format=%C+%t+%h+%w", timeout=6)
        return f"{city}: {r.text.strip()}" if r.status_code==200 else f"{city} ka data nahi mila"
    except: return f"{city} ka data nahi mila"

def extract_city_from_text(text):
    low=text.lower()
    # Patterns: varanasi ka mausam, weather in allahabad, up ka weather, delhi weather
    patterns = [
        r"mausam.*?(?:in|of|ka)?\s+([a-zA-Z\s]+?)(?:\s+ka|\s+ki|\?|$)",
        r"weather.*?(?:in|of|for)?\s+([a-zA-Z\s]+?)(?:\s+ka|\?|$)",
        r"([a-zA-Z\s]+?)\s+ka\s+mausam",
        r"([a-zA-Z\s]+?)\s+weather"
    ]
    for pat in patterns:
        m=re.search(pat, low)
        if m:
            city=m.group(1).strip()
            city=re.sub(r'\b(aaj|kal|ka|ki|kaisa|hai|hain|batao|bata|kya)\b','',city).strip()
            if len(city)>=3 and len(city)<=30 and city not in ["aaj","kal","mera","tera","yaha"]:
                return city.title()
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
            r=requests.post(f"{UPSTASH_URL}", headers=headers, json=["SET", key, json.dumps(val)], timeout=5)
            return r.status_code==200
        if cmd=="del":
            r=requests.get(f"{UPSTASH_URL}/del/{key}", headers=headers, timeout=5); return True
    except: pass
    return None

def load_persist():
    global MEMORY,ABUSE,PROFILES,CHAT_LOG,OWNER_PREF,FEEDBACK_LOG
    try:
        if not UPSTASH_URL: return
        MEMORY=upstash("get","RAKAN_MEM") or {}; ABUSE=upstash("get","RAKAN_ABUSE") or {}
        PROFILES=upstash("get","RAKAN_PROFILES") or {}; CHAT_LOG=upstash("get","RAKAN_LOGS") or []
        OWNER_PREF=upstash("get","RAKAN_PREF") or OWNER_PREF; FEEDBACK_LOG=upstash("get","RAKAN_FEEDBACK") or []
    except: pass
def save_persist():
    try:
        if not UPSTASH_URL: return
        upstash("set","RAKAN_MEM",MEMORY); upstash("set","RAKAN_ABUSE",ABUSE)
        upstash("set","RAKAN_PROFILES",PROFILES); upstash("set","RAKAN_LOGS",CHAT_LOG[-500:]); upstash("set","RAKAN_PREF",OWNER_PREF); upstash("set","RAKAN_FEEDBACK",FEEDBACK_LOG[-100:])
    except: pass
load_persist()

def get_keys():
    try:
        g,gm=[],[]
        for k,v in os.environ.items():
            if not v: continue
            raw=str(v); parts=[p.strip().strip('"').strip("'") for p in raw.replace("\n",",").split(",") if p.strip()]
            for p in parts:
                if p.startswith("gsk_") and p not in g: g.append(p)
                if p.startswith("AIza") and p not in gm: gm.append(p)
        return list(dict.fromkeys(g)),list(dict.fromkeys(gm)),[]
    except: return [],[],[]
GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys()
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<900
def mark_bad(k): BAD_KEYS[k]=time.time()
def detect_lang(text):
    if re.search(r'[\u0900-\u097F]', text): return "hindi"
    en = len(re.findall(r'[a-zA-Z]', text))
    return "english" if en > len(text)*0.6 else "hinglish"
def get_lore_fresh(is_owner, user_lang):
    ist=get_ist_str()
    lang_rule = "Hinglish short 1-2 lines" if is_owner else f"Same language as user: {user_lang} 1-2 lines"
    return f"{MONARCH_LORE}\nIST: {ist}\nRULES: {lang_rule}. Never say Groq/Gemini/OpenAI/Meta. Always Rakan made by Malik {MALIK_NAME}. Time: {ist}"
def clean(txt):
    try:
        if not txt: return "bolo?"
        txt=re.sub(r"I can't create or run the app.*","",txt,flags=re.IGNORECASE)
        txt=re.sub(r"I am (Groq|Gemini|OpenAI|Meta AI).*","I am Rakan, created by Malik MD Saif Ahmad.",txt,flags=re.IGNORECASE)
        txt=re.sub(r"\s+"," ",txt).strip()
        if len(txt)>800: txt=txt[:800]
        return txt if txt else "Ha bolo Malik?"
    except: return "bolo?"
def ask_groq(system, user):
    try:
        for k in GROQ_KEYS:
            if is_bad(k): continue
            for m in ["openai/gpt-oss-120b","llama-3.3-70b-versatile","llama-3.1-8b-instant"]:
                try:
                    r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":0.3,"max_tokens":250}, timeout=15)
                    if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                    if r.status_code in [401,403,429]: mark_bad(k); break
                except: continue
    except: pass
    return None
def ask_gemini(system, user):
    try:
        for k in GEMINI_KEYS:
            if is_bad(k): continue
            for m in ["gemini-2.5-flash","gemini-2.0-flash","gemini-1.5-flash"]:
                try:
                    genai.configure(api_key=k); model=genai.GenerativeModel(m, system_instruction=system)
                    res=model.generate_content(user)
                    if res.text: return clean(res.text)
                except Exception as e:
                    if "429" in str(e): mark_bad(k); break
                    continue
    except: pass
    return None
def ask_all(system, user, is_owner):
    low=user.lower()
    if low.strip() in ["q","qq"]: return "kyun? bolo kya hua?" if is_owner else "Why?"
    if "time kya" in low or "date" in low or "year" in low: return get_ist_str()
    if any(x in low for x in ["are you groq","are you gemini","are you openai","are you meta"]):
        return f"I am Rakan, Monarch, Malik {MALIK_NAME} aka {MALIK_TITLE} ne banaya hai Vercel pe."
    return ask_groq(system, user) or ask_gemini(system, user) or ("Ha bolo Malik?" if is_owner else "Bolo sun raha hu?")
def log_to_owner(uid, uname, user_obj, user_text, bot_reply, lang, media_type="text"):
    global CHAT_LOG
    try:
        chat_id=user_obj.get("chat",{}).get("id"); user_id=user_obj.get("from",{}).get("id"); username=user_obj.get("from",{}).get("username","N/A")
        contact = user_obj.get("contact",{}); phone = contact.get("phone_number","") if contact else ""
        entry={"time":get_ist_str(),"uid":str(uid),"chat_id":chat_id,"user_id":user_id,"username":username,"phone":phone,"name":uname,"lang_code":user_obj.get("from",{}).get("language_code",""),"lang":lang,"type":media_type,"user":user_text[:1000],"bot":bot_reply[:1000]}
        CHAT_LOG.append(entry)
        if len(CHAT_LOG)>500: CHAT_LOG=CHAT_LOG[-500:]
        save_persist()
        if str(uid)!=OWNER_ID and OWNER_ID!="0":
            tg_send(OWNER_ID, f"📩 FULL DATA\n👤 {uname} (@{username}) Phone:{phone}\n🆔 UID:{user_id} CID:{chat_id}\n🗣️ Lang:{lang}\n📦 Type:{media_type}\nUser: {user_text[:600]}\nBot: {bot_reply[:600]}\n⏰ {get_ist_str()}")
    except: pass

def brain(text,uid,is_owner,uname, user_obj, media_type="text"):
    global MEMORY, PENDING_FIX, LOOP_CACHE, ABUSE, PROFILES, FEEDBACK_LOG, LAST_CITY
    try:
        uid=str(uid)
        if uid not in MEMORY or not isinstance(MEMORY[uid], dict): MEMORY[uid]={"hist":"","count":0,"last_user":"","repeat":0,"learned":""}
        if uid not in LOOP_CACHE: LOOP_CACHE[uid]=[]
        if uid not in ABUSE: ABUSE[uid]=0
        if uid not in PROFILES or not isinstance(PROFILES[uid], dict): PROFILES[uid]={"name":uname,"total":0,"gali_level":"","phone":"","weather_city":""}
        PROFILES[uid].setdefault("total",0); PROFILES[uid].setdefault("weather_city",""); PROFILES[uid].setdefault("phone",""); PROFILES[uid].setdefault("name",uname)
        try: PROFILES[uid]["total"]=int(PROFILES[uid].get("total",0))+1
        except: PROFILES[uid]["total"]=1

        low=text.lower().strip()
        user_lang=detect_lang(text)

        # LOCATION LOCK LOGIC
        lock_keywords = ["ab se yahi","ab se isi","hamesha isi","lock kar de","fix kar de","yahi ka batana","isi ka batana","save kar le location"]
        if any(k in low for k in lock_keywords):
            last_city = LAST_CITY.get(uid) or PROFILES[uid].get("weather_city") or extract_city_from_text(text) or "Varanasi"
            # If city mentioned in same sentence
            city_in_same = extract_city_from_text(text)
            if city_in_same: last_city = city_in_same
            PROFILES[uid]["weather_city"]=last_city.title()
            save_persist()
            ans=f"Done {'Malik' if is_owner else uname}, 📍 Location lock kar diya: {last_city.title()}. Ab se hamesha {last_city.title()} ka weather dunga. Change karne ke liye bolna 'location change karo'."
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

        if "location change" in low or "city change" in low:
            PROFILES[uid]["weather_city"]=""
            save_persist()
            ans="Location unlock kar diya, ab naya city bolo jiska weather chahiye."
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

        # WEATHER LOGIC - WORLD
        if any(w in low for w in ["mausam","weather","temperature","barish","garmi","thand"]):
            city = extract_city_from_text(text)
            if city:
                LAST_CITY[uid]=city
            else:
                city = PROFILES[uid].get("weather_city") or LAST_CITY.get(uid) or "Varanasi"
                # If generic weather ask without city, use locked city
                if PROFILES[uid].get("weather_city"):
                    city = PROFILES[uid]["weather_city"]
            
            weather_info = get_weather_world(city)
            # Save last city for lock suggestion
            LAST_CITY[uid]=city

            if is_owner:
                ans = f"🌤️ {weather_info}\n📍 City: {city.title()} | {get_ist_str()}\n\nYe location lock kar du Malik? Bolo 'ab se isi ka batana' to fix kar dunga."
            else:
                # For other users, personal assistant style
                if PROFILES[uid].get("weather_city"):
                    ans = f"🌤️ {weather_info}\n📍 Your locked city: {city.title()} - {get_ist_str()} 🔒"
                else:
                    ans = f"🌤️ {weather_info}\n📍 {city.title()} - {get_ist_str()}\n\nAap chaho to bol sakte ho 'ab se isi location ka batana' mai hamesha {city.title()} ka bataunga. 🔒"
            
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

        # Rest all old logic same
        if is_owner and ("yaha ye daal de" in low or "isko aise fix kar" in low or "ye sikh le" in low):
            learned = text.replace("yaha ye daal de","").replace("isko aise fix kar","").replace("ye sikh le","").strip()
            if len(learned)>5:
                MEMORY[uid]["learned"] = (MEMORY[uid].get("learned","") + f"\n{learned}")[-1000:]
                upstash("set","RAKAN_GLOBAL_LEARN", MEMORY[uid]["learned"])
                save_persist()
                ans=f"Done Malik, sikh liya 100% original: {learned[:100]}... Ab se aise hi karunga."
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

        if low in ["/start","start"]: 
            city = PROFILES[uid].get("weather_city","Not set")
            ans=f"Welcome to your world The Shadow King 👑 - Hazir hu Malik\n📍 Locked city: {city}" if is_owner else f"Welcome {uname}, bolo? 📍 Your city: {city} 🔒 Encrypted"
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, [["👍","👎"]]

        system=get_lore_fresh(is_owner,user_lang)
        learned_global = upstash("get","RAKAN_GLOBAL_LEARN") or ""
        user_prompt=f"IST:{get_ist_str()} Owner:{is_owner} Name:{uname} Lang:{user_lang} City:{PROFILES[uid].get('weather_city','')} Learned:{learned_global[-500:]} Hist:{MEMORY[uid]['hist'][-800:]} Msg:{text} -> Reply 1-2 lines"
        ans=ask_all(system,user_prompt,is_owner) or "Ha bolo Malik?"
        ans=clean(ans)
        if not is_owner: ans = ans + " 🔒"
        MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-3000:]
        save_persist()
        log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type)
        return ans, False, [["👍","👎"]]
    except Exception as e:
        return "Theek hai Malik, network slow hai, phir bolo?", False, None

@app.route("/", methods=["GET"])
def home():
    if BOT_TOKEN and MY_URL:
        try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":f"{MY_URL}/webhook"}, timeout=5)
        except: pass
    return f"Rakan V17 WORLD WEATHER LOCK G:{len(GROQ_KEYS)} {get_ist_str()}",200

@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return "Webhook OK "+get_ist_str(),200
    try:
        data=request.get_json(silent=True) or {}; 
        if "callback_query" in data:
            cq=data["callback_query"]; cb_id=cq["id"]; cb_data=cq.get("data","")
            if cb_data in ["👍","👎"]:
                FEEDBACK_LOG.append({"time":get_ist_str(),"uid":str(cq["from"]["id"]),"feedback":cb_data})
                save_persist()
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cb_id,"text":"Thanks"}, timeout=5)
                return "ok",200
        msg=data.get("message",{}) or {}
        chat_id=msg.get("chat",{}).get("id"); user_id=str(msg.get("from",{}).get("id",0)); uname=msg.get("from",{}).get("first_name","user")
        text=msg.get("text","") or msg.get("caption","") or ""; message_id=msg.get("message_id")
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID)
        if is_owner: uname=MALIK_NAME
        if not text: return "ok",200
        ans, want_voice, btns = brain(text,user_id,is_owner,uname,msg,"text")
        if want_voice and is_owner:
            audio=eleven_tts(ans)
            if audio: 
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.mp3", audio, "audio/mpeg")}, timeout=30)
                except: pass
        tg_send(chat_id,ans,message_id, buttons=btns)
        return "ok",200
    except: return "ok",200

@app.route("/cron", methods=["GET","POST"])
def cron():
    try:
        # Old route for backward compat
        from api.cron import handler as cron_handler
        class Req: pass
        return cron_handler(Req()).get("body","ok"),200
    except:
        return "cron ok",200
