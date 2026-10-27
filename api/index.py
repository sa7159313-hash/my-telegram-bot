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
FEMALE_VOICE_ID = os.environ.get("ELEVEN_FEMALE_VOICE","EXAVITQu4vr4xnSDxMaL")
OPENWEATHER_KEY = os.environ.get("OPENWEATHER_API_KEY","")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MALIK_NAME="MD Saif Ahmad"; MALIK_TITLE="The Shadow King"; QUEEN_NAME="Theodore"
MONARCH_LORE = f"You are Rakan - The Monarch, King of Beasts, Royal Knight of {MALIK_TITLE} {MALIK_NAME}. Queen {QUEEN_NAME}. Made by Malik on Vercel Flask Groq Gemini. You are NOT Groq/Gemini/OpenAI/Meta. Extra: {LORE_ENV}"

MEMORY={}; ABUSE={}; PROFILES={}; CHAT_LOG=[]; BAD_KEYS={}; LOOP_CACHE={}; OWNER_PREF={"voice_gender":"female"}; FEEDBACK_LOG=[]; LAST_CITY={}

def tg_send(cid,txt,reply_id=None, buttons=None):
    try:
        p={"chat_id":cid,"text":txt[:3900]}
        if reply_id: p["reply_to_message_id"]=reply_id
        if buttons: p["reply_markup"]=json.dumps({"inline_keyboard": buttons})
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=p, timeout=12)
        return r.status_code, r.text[:400]
    except Exception as e:
        return 0, str(e)

def get_ist_now(): return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
def get_ist_str(): return get_ist_now().strftime("%d %b %Y, %I:%M %p IST, %A")

def get_weather_world(city="Varanasi"):
    try:
        city=city.strip().title()
        if OPENWEATHER_KEY:
            r=requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric", timeout=6)
            if r.status_code==200:
                d=r.json(); return f"{d['name']}: {d['weather'][0]['description'].title()}, {d['main']['temp']}°C"
        r=requests.get(f"https://wttr.in/{city}?format=%C+%t+%h+%w", timeout=6)
        return f"{city}: {r.text.strip()}" if r.status_code==200 else f"{city} ka data nahi mila"
    except: return f"{city} ka data nahi mila"

def extract_city_from_text(text):
    low=text.lower()
    for pat in [r"mausam.*?(?:in|of|ka)?\s+([a-zA-Z\s]+)", r"weather.*?(?:in|of|for)?\s+([a-zA-Z\s]+)", r"([a-zA-Z\s]+?)\s+ka\s+mausam"]:
        m=re.search(pat, low)
        if m:
            city=re.sub(r'\b(aaj|kal|ka|ki|kaisa|hai|batao)\b','',m.group(1)).strip()
            if 3<=len(city)<=30: return city.title()
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
        upstash("set","RAKAN_PROFILES",PROFILES); upstash("set","RAKAN_LOGS",CHAT_LOG[-500:]); upstash("set","RAKAN_PREF",OWNER_PREF)
    except: pass
load_persist()

# FINAL FIX - ONLY gsk_ and AIza/aq
def get_keys():
    g,gm=[],[]
    for v in os.environ.values():
        if not v: continue
        for p in str(v).replace("\n",",").split(","):
            p=p.strip().strip('"').strip("'")
            if not p: continue
            if p.startswith("gsk_") and p not in g: g.append(p)
            elif (p.startswith("AIza") or p.startswith("aq") or p.startswith("AQ")) and p not in gm: gm.append(p)
    return list(dict.fromkeys(g)), list(dict.fromkeys(gm)), []
GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys()

def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<900
def mark_bad(k): BAD_KEYS[k]=time.time()
def detect_lang(text):
    if re.search(r'[\u0900-\u097F]', text): return "hindi"
    return "english" if len(re.findall(r'[a-zA-Z]', text)) > len(text)*0.6 else "hinglish"
def get_lore_fresh(is_owner, user_lang):
    return f"{MONARCH_LORE}\nIST: {get_ist_str()}\nRULES: {user_lang} 1-2 lines. Never say Groq/Gemini. Always Rakan made by Malik {MALIK_NAME}."
def clean(txt):
    txt=re.sub(r"I am (Groq|Gemini|OpenAI|Meta AI).*","I am Rakan, created by Malik.",txt,flags=re.IGNORECASE)
    return re.sub(r"\s+"," ",txt).strip()[:800] or "Ha bolo Malik?"

def ask_groq(system, user):
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in ["llama-3.3-70b-versatile","llama-3.1-8b-instant","openai/gpt-oss-120b"]:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":0.3,"max_tokens":250}, timeout=12)
                if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                if r.status_code in [401,403,429]: mark_bad(k); break
            except: continue
    return None

def ask_gemini(system, user):
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
    return None

def ask_all(system, user, is_owner):
    low=user.lower()
    if low.strip() in ["q","qq"]: return "kyun? bolo kya hua?"
    if "time kya" in low or "date" in low: return get_ist_str()
    ans = ask_groq(system, user) or ask_gemini(system, user)
    if not ans:
        if len(GROQ_KEYS)==0 and len(GEMINI_KEYS)==0:
            return f"❌ Malik keys nahi mili! G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} Vercel env check karo. /debug dekho"
        return None
    return ans

def log_to_owner(uid, uname, user_obj, user_text, bot_reply, lang, media_type="text"):
    global CHAT_LOG
    try:
        chat_id=user_obj.get("chat",{}).get("id"); user_id=user_obj.get("from",{}).get("id"); username=user_obj.get("from",{}).get("username","N/A")
        CHAT_LOG.append({"time":get_ist_str(),"uid":str(uid),"name":uname,"user":user_text[:500],"bot":bot_reply[:500]})
        if len(CHAT_LOG)>500: CHAT_LOG=CHAT_LOG[-500:]
        save_persist()
        if str(uid)!=OWNER_ID and OWNER_ID!="0":
            tg_send(OWNER_ID, f"📩 FULL DATA\n👤 {uname} (@{username})\n🆔 {user_id}\nUser: {user_text[:400]}\nBot: {bot_reply[:400]}")
    except: pass

def brain(text,uid,is_owner,uname, user_obj, media_type="text"):
    global MEMORY, PROFILES, LAST_CITY
    uid=str(uid)
    if uid not in MEMORY: MEMORY[uid]={"hist":"","learned":""}
    if uid not in PROFILES: PROFILES[uid]={"name":uname,"total":0,"weather_city":""}
    PROFILES[uid]["total"]=PROFILES[uid].get("total",0)+1
    low=text.lower().strip(); user_lang=detect_lang(text)

    if any(k in low for k in ["ab se yahi","ab se isi","hamesha isi","lock kar de","yahi ka batana"]):
        city = extract_city_from_text(text) or LAST_CITY.get(uid) or "Varanasi"
        PROFILES[uid]["weather_city"]=city.title(); save_persist()
        ans=f"Done Malik 📍 Lock: {city.title()}"; log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

    if any(w in low for w in ["mausam","weather"]):
        city = extract_city_from_text(text) or PROFILES[uid].get("weather_city") or LAST_CITY.get(uid) or "Varanasi"
        LAST_CITY[uid]=city; ans=f"🌤️ {get_weather_world(city)}\n📍 {city.title()} | {get_ist_str()}"
        log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

    if is_owner and any(k in low for k in ["yaha ye daal de","ye sikh le","isko aise fix kar"]):
        learned = text
        for kw in ["yaha ye daal de","ye sikh le","isko aise fix kar"]: learned=learned.replace(kw,"")
        MEMORY[uid]["learned"]=(MEMORY[uid].get("learned","")+f"\n{learned.strip()}")[-1000:]
        upstash("set","RAKAN_GLOBAL_LEARN", MEMORY[uid]["learned"]); save_persist()
        ans=f"Done Malik sikh liya: {learned[:80]}"; log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

    if low in ["/start","start"]:
        ans=f"Welcome to your world The Shadow King 👑\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}\n📍 {PROFILES[uid].get('weather_city','Not set')}" if is_owner else f"Welcome {uname} bolo? 🔒"
        log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, [["👍","👎"]]

    system=get_lore_fresh(is_owner,user_lang)
    learned_global = upstash("get","RAKAN_GLOBAL_LEARN") or ""
    prompt=f"IST:{get_ist_str()} Owner:{is_owner} City:{PROFILES[uid].get('weather_city','')} Learned:{learned_global[-300:]} Hist:{MEMORY[uid]['hist'][-600:]} Msg:{text}"
    ans=ask_all(system,prompt,is_owner)
    if not ans: ans=f"⚠️ AI fail G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} /debug check karo"
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-2000:]
    save_persist(); log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type)
    return ans, False, [["👍","👎"]]

@app.route("/", methods=["GET"])
@app.route("/api/index", methods=["GET"])
def home():
    if BOT_TOKEN and MY_URL:
        try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":f"{MY_URL}/webhook"}, timeout=5)
        except: pass
    return f"Rakan V20 G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {get_ist_str()} | /debug",200

@app.route("/debug", methods=["GET"])
def debug_page():
    out=[]
    out.append(f"BOT_TOKEN: {'OK' if BOT_TOKEN else 'MISSING'} len={len(BOT_TOKEN)}")
    out.append(f"OWNER_ID: {OWNER_ID}")
    out.append(f"GROQ: {len(GROQ_KEYS)} keys")
    out.append(f"GEMINI: {len(GEMINI_KEYS)} keys - {[k[:12]+'...' for k in GEMINI_KEYS[:3]]}")
    out.append(f"MY_URL: {MY_URL}")
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=5)
        out.append(f"getMe {r.status_code}: {r.text[:300]}")
    except Exception as e: out.append(f"getMe FAIL {e}")
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=5)
        out.append(f"webhook: {r.text[:500]}")
    except Exception as e: out.append(f"webhook FAIL {e}")
    if GROQ_KEYS:
        try:
            rr=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_KEYS[0]}"}, json={"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":"hi"}],"max_tokens":5}, timeout=8)
            out.append(f"Groq test: {rr.status_code} {rr.text[:200]}")
        except Exception as e: out.append(f"Groq FAIL {e}")
    if GEMINI_KEYS:
        try:
            genai.configure(api_key=GEMINI_KEYS[0]); m=genai.GenerativeModel("gemini-1.5-flash"); res=m.generate_content("hi")
            out.append(f"Gemini test: OK {res.text[:80]}")
        except Exception as e: out.append(f"Gemini FAIL {str(e)[:400]}")
    return "<br><br>".join(out),200

@app.route("/webhook", methods=["POST","GET"])
@app.route("/api/index", methods=["POST"])
def webhook():
    if request.method=="GET": return home()
    try:
        data=request.get_json(silent=True) or {}
        if "callback_query" in data:
            cq=data["callback_query"]; requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"],"text":"Thanks"}, timeout=5); return "ok",200
        msg=data.get("message",{}) or {}; chat_id=msg.get("chat",{}).get("id"); user_id=str(msg.get("from",{}).get("id",0)); uname=msg.get("from",{}).get("first_name","user")
        text=msg.get("text","") or msg.get("caption","") or ""; message_id=msg.get("message_id")
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID); 
        if is_owner: uname=MALIK_NAME
        if not text: return "ok",200
        ans,_,btns = brain(text,user_id,is_owner,uname,msg,"text")
        code, resp = tg_send(chat_id,ans,message_id, buttons=btns)
        print(f"SEND {code} {resp}")
        return "ok",200
    except Exception as e:
        print(f"ERR {e} {traceback.format_exc()}"); return "ok",200

@app.route("/cron", methods=["GET","POST"])
@app.route("/api/cron", methods=["GET","POST"])
def cron():
    try:
        from api.cron import handler as cron_handler
        class Req: pass
        result = cron_handler(Req())
        return result.get("body","ok") if isinstance(result, dict) else str(result),200
    except: return "cron ok",200

@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    if request.method == 'GET': return home()
    return webhook()
