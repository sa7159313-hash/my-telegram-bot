import os, time, json, re, datetime, requests, traceback
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = str(os.environ.get("OWNER_ID","0")).strip()
LORE_ENV = os.environ.get("THE_BEAST_KING_MONARCH_AKAAN_LORE","")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY","")
MALE_VOICE_ID = os.environ.get("ELEVEN_MALE_VOICE","pNInz6obpgDQGcFmaJgB")
FEMALE_VOICE_ID = os.environ.get("ELEVEN_FEMALE_VOICE","21m00Tcm4TlvDq8ikWAM")
OPENWEATHER_KEY = os.environ.get("OPENWEATHER_API_KEY","")
TAVILY_KEY = os.environ.get("TAVILY_API_KEY","")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MALIK_NAME="MD Saif Ahmad"
QUEEN_USERNAME="pearly_paradise15"
MONARCH_LORE = f"You are Rakan, Malik {MALIK_NAME} ka bhai. Urdu Roman. Never add Pakistan history unless asked. Made by Malik. Extra:{LORE_ENV}"

MEMORY={}; PROFILES={}; CHAT_LOG=[]; BAD_KEYS={}; OWNER_PREF={}; LAST_BOT_MSG={}; LAST_MSG_ID={}; LAST_CITY={}

def get_keys():
    g,gm=[],[]
    for v in os.environ.values():
        if not v: continue
        parts = re.split(r'[,\n;\s]+', str(v))
        for p in parts:
            p=p.strip().strip('"').strip("'").strip()
            if len(p)<10: continue
            if p.startswith("gsk_"):
                if p not in g: g.append(p)
            elif p.startswith("AIza"):
                if len(p)>25 and p not in gm: gm.append(p)
    return list(dict.fromkeys(g)), list(dict.fromkeys(gm))
GROQ_KEYS,GEMINI_KEYS=get_keys()

def get_ist_str(): return (datetime.datetime.utcnow()+datetime.timedelta(hours=5,minutes=30)).strftime("%d %b %Y, %I:%M %p IST")
def get_ist_time_only(): return (datetime.datetime.utcnow()+datetime.timedelta(hours=5,minutes=30)).strftime("%I:%M %p IST")

def tg_send(cid,txt,reply_id=None, buttons=None):
    try:
        p={"chat_id":cid,"text":txt[:3900]}
        if reply_id: p["reply_to_message_id"]=reply_id
        if buttons: p["reply_markup"]=json.dumps({"inline_keyboard": buttons})
        r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=p, timeout=15).json()
        if r.get("ok"): LAST_MSG_ID[str(cid)]=r["result"]["message_id"]
        return r.get("ok",False)
    except: return False

def tg_real_forward(fc, mid, tc):
    try: return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/forwardMessage", json={"chat_id":tc,"from_chat_id":fc,"message_id":int(mid)}, timeout=10).status_code==200
    except: return False
def tg_real_copy(fc, mid, tc):
    try: return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/copyMessage", json={"chat_id":tc,"from_chat_id":fc,"message_id":int(mid)}, timeout=10).status_code==200
    except: return False

def tg_send_voice(cid, text, gender="female"):
    try:
        if not ELEVEN_API_KEY or not text: return False
        vid=FEMALE_VOICE_ID if gender=="female" else MALE_VOICE_ID
        rr=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key":ELEVEN_API_KEY,"Content-Type":"application/json"}, json={"text":text[:400],"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.55,"similarity_boost":0.8}}, timeout=20)
        if rr.status_code==200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":cid}, files={'voice':('v.mp3',rr.content,'audio/mpeg')}, timeout=20)
            return True
    except: pass
    return False

def live_search(q):
    try:
        if TAVILY_KEY and len(q)>2 and any(w in q.lower() for w in ["news","price","aaj","latest","crypto","weather"]):
            r=requests.post("https://api.tavily.com/search", json={"api_key":TAVILY_KEY,"query":q,"max_results":2,"include_answer":True}, timeout=8)
            if r.status_code==200:
                j=r.json(); return (j.get("answer","")+" | "+" | ".join([x.get("content","")[:200] for x in j.get("results",[])]))[:700]
    except: pass
    return ""

def transcribe_voice(file_id):
    try:
        fp=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()["result"]["file_path"]
        audio=requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=15).content
        for k in GROQ_KEYS:
            try:
                rr=requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization": f"Bearer {k}"}, files={'file':('a.ogg',audio,'audio/ogg')}, data={'model':'whisper-large-v3','language':'hi'}, timeout=20)
                if rr.status_code==200: return rr.json().get("text","")
            except: continue
    except: pass
    return ""

def upstash(cmd,key,val=None):
    if not UPSTASH_URL or not UPSTASH_TOKEN: return None
    try:
        h={"Authorization": f"Bearer {UPSTASH_TOKEN}","Content-Type":"application/json"}
        if cmd=="get":
            r=requests.get(f"{UPSTASH_URL}/get/{key}", headers=h, timeout=5)
            if r.status_code==200:
                d=r.json().get("result"); return json.loads(d) if d else None
        else:
            requests.post(f"{UPSTASH_URL}", headers=h, json=["SET",key,json.dumps(val)], timeout=5)
    except: pass
    return None

def load_persist():
    global MEMORY,PROFILES,OWNER_PREF,CHAT_LOG
    # V35.2 NEW KEY - PURANA PAKISTAN WALA LOOP KHATAM
    MEMORY=upstash("get","RAKAN_MEM_V352") or {}
    PROFILES=upstash("get","RAKAN_PROFILES") or {}
    OWNER_PREF=upstash("get","RAKAN_PREF") or {"voice_gender":"female","voice_on":False}
    CHAT_LOG=upstash("get","RAKAN_LOGS") or []
def save_persist():
    upstash("set","RAKAN_MEM_V352",MEMORY); upstash("set","RAKAN_PROFILES",PROFILES); upstash("set","RAKAN_PREF",OWNER_PREF); upstash("set","RAKAN_LOGS",CHAT_LOG[-500:])
load_persist()

def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<600
def mark_bad(k): BAD_KEYS[k]=time.time()

def clean(t, user_query=""):
    if not t: return ""
    t=t.replace("🙏","")
    # BLOCK SORRY
    bad_phrases=["I'm sorry, but I can't help","I cannot help with that","I'm not able to provide","As an AI language model","I am Groq","I am Gemini","Here's a quick recap","Sure, I'm speaking in English","How can I help you right now?","kaunse topic pe help"]
    for bp in bad_phrases:
        if bp.lower() in t.lower(): return ""
    # V35.2 FIX - PAKISTAN FILTER - Agar user ne Pakistan nahi pucha to hatao
    if "pakistan" not in user_query.lower() and "1947" not in user_query.lower():
        # Pakistan wala sentence hatao
        t=re.sub(r"1947 mein Pakistan.*|Pakistan ne British.*|Pakistan ko azaadi.*|Pakistan ke roop mein.*|British rule se.*", "", t, flags=re.I)
        t=re.sub(r"\s+"," ",t).strip()
    return t[:900]

def ask_groq(sys,user):
    if not GROQ_KEYS: return None
    MODELS = ["openai/gpt-oss-20b","meta-llama/llama-4-scout-17b-16e-instruct","qwen/qwen3.8-27b"]
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":sys},{"role":"user","content":user}],"temperature":0.6,"max_tokens":300}, timeout=18)
                if r.status_code==200:
                    txt=r.json()["choices"][0]["message"]["content"]
                    if txt and "sorry" not in txt.lower()[:80]: return txt
                if r.status_code in [401,429]: mark_bad(k); break
            except: continue
    return None

def ask_gemini(sys,user):
    if not GEMINI_KEYS: return None
    MODELS = ["gemini-3.5-flash","gemini-2.5-flash"]
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        for m in MODELS:
            try:
                genai.configure(api_key=k)
                model=genai.GenerativeModel(m, system_instruction=sys)
                res=model.generate_content(user, generation_config={"temperature":0.6,"max_output_tokens":300})
                if res and getattr(res,'text',None):
                    t=res.text
                    if "sorry" not in t.lower()[:80]: return t
            except: continue
    return None

def get_weather(city):
    try:
        city=city.strip().title()
        if OPENWEATHER_KEY:
            r=requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric", timeout=7)
            if r.status_code==200:
                d=r.json(); return f"{d['name']}: {d['weather'][0]['description']}, {d['main']['temp']}°C"
        r=requests.get(f"https://wttr.in/{city}?format=%C+%t", timeout=6)
        if r.status_code==200: return f"{city}: {r.text}"
    except: pass
    return f"{city} ka data nahi mila"

def brain(text,uid,is_owner,is_queen,uname,is_voice=False):
    global MEMORY,PROFILES,LAST_BOT_MSG,CHAT_LOG,LAST_CITY
    uid=str(uid)
    if uid not in MEMORY: MEMORY[uid]={"hist":""}
    if uid not in PROFILES: PROFILES[uid]={"total":0,"city":""}
    PROFILES[uid]["total"]+=1
    low=text.lower().strip()
    
    # V35.2 FIX 1 - EMOJI ONLY / COMPLAINT HANDLING
    # Agar sirf emoji hai ya 2-3 char hai
    only_emoji = len(re.sub(r'[^\w\s]','', text, flags=re.UNICODE).strip())==0 and len(text.strip())<=4
    if only_emoji or low in ["😒","😒😒","😐","😐😐","😑"]:
        ans="Jee Malik bolo, kya hua? Kheriyat hai? 😊" if is_owner else f"Jee {uname} bolo?"
        LAST_BOT_MSG[uid]=ans; return ans, OWNER_PREF.get("voice_on",False) and is_owner, False

    if any(x in low for x in ["abe ye kya hai","ye kya hai","ye kya bakwas","maine pucha kya","pucha kya maine","nahi na mat bhej","mat bhej","ye sab kya"]):
        ans="Maaf kar do Malik, galat chala gaya tha, ab batao sahi se kya chahiye? Mai sun raha hu 🔥" if is_owner else f"Maaf karna {uname}, galat bhej diya, bolo kya chahiye? 😊"
        # Memory bhi clear karo is uid ka taki loop toote
        MEMORY[uid]["hist"]=""
        LAST_BOT_MSG[uid]=ans; return ans, False, False

    if low in ["hi","hii","hello","salam","assalamu alaikum","wow","oh","okk","ok"]:
        ans="Jee Malik, bolo kya haal hai? Hukam karo 😎🔥" if is_owner else f"Jee {uname} bolo?"
        LAST_BOT_MSG[uid]=ans; return ans, OWNER_PREF.get("voice_on",False) and is_owner, False

    if "kya madad" in low or "kya help" in low or "kya kar sakte ho" in low:
        ans="Malik jo hukam karo ge wo ho jaye ga, bolo kya karna hai? 🔥" if is_owner else f"Jo bolo {uname} kar dunga 🔒"
        LAST_BOT_MSG[uid]=ans; return ans, False, False

    if "kalma" in low or "kalima" in low:
        ans="Pehela Kalma Tayyab: La ilaha illallah Muhammadur Rasulullah ﷺ"
        LAST_BOT_MSG[uid]=ans; return ans, False, False

    if any(x in low for x in ["time kya","kitna baja","samay kya","time bata"]):
        ans=f"Abhi {get_ist_time_only()} ho raha hai Malik, {get_ist_str()} 📍"
        LAST_BOT_MSG[uid]=ans; return ans, OWNER_PREF.get("voice_on",False) and is_owner, False

    if "who i am" in low or "mai kaun hu" in low:
        ans=f"Tum Malik ho, {MALIK_NAME}, Shadow King 👑🔥" if is_owner else f"Tum {uname} ho 🔒"
        LAST_BOT_MSG[uid]=ans; return ans, False, False

    if any(x in low for x in ["voice on","orb on","voice mode on"]):
        OWNER_PREF["voice_on"]=True; save_persist()
        ans="Voice Mode ON kar diya Malik 🔊 Ab voice note bhejo, mai voice me jawab dunga - Telegram Orb ON 🔥"
        LAST_BOT_MSG[uid]=ans; return ans, True, False
    if any(x in low for x in ["voice off","orb off"]):
        OWNER_PREF["voice_on"]=False; save_persist()
        ans="Voice Mode OFF kar diya Malik 🔇"
        LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "female voice" in low: OWNER_PREF["voice_gender"]="female"; save_persist(); ans="Female voice lock 👩"; LAST_BOT_MSG[uid]=ans; return ans, OWNER_PREF.get("voice_on",False), False
    if "male voice" in low: OWNER_PREF["voice_gender"]="male"; save_persist(); ans="Male voice lock 👨"; LAST_BOT_MSG[uid]=ans; return ans, OWNER_PREF.get("voice_on",False), False

    if low.startswith("/orv") and is_owner:
        orv=upstash("get","RAKAN_LIKES") or {"like":0,"dislike":0}
        ans=f"📊 ORV V35.2 {get_ist_str()}\n👍 {orv.get('like',0)} 👎 {orv.get('dislike',0)}\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}"; return ans, False, False
    if low.startswith("/start"):
        v_on="ON 🔊" if OWNER_PREF.get("voice_on") else "OFF 🔇"
        ans=f"Assalamu Alaikum Malik 👑 {MALIK_NAME}\nTera Rakan hazir hai 🔥\nV35.2 G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}\nVoice:{OWNER_PREF.get('voice_gender')} {v_on}\nLanguage: Urdu Roman\n{get_ist_str()}\n\nVoice Mode ON = Orb 🔥" if is_owner else f"Hey {uname} 👋"
        LAST_BOT_MSG[uid]=ans; return ans, False, True

    if "mausam" in low or "weather" in low:
        city=PROFILES[uid].get("city") or "Varanasi"
        ans=f"🌤️ {get_weather(city)} | {get_ist_str()}"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if any(w in low for w in ["free money","lottery","xxx"]) and not is_owner: return "Archived", False, False

    search_ctx=live_search(text)
    sys=f"You are Rakan, Malik {MALIK_NAME} ka bhai. Urdu Roman Hinglish short 1-2 lines. Never mention Pakistan 1947 history unless user asks about Pakistan. Pehla Kalma is only La ilaha illallah Muhammadur Rasulullah. No extra history. IST {get_ist_str()} {search_ctx}" if is_owner else f"You are Rakan, helpful bot. Hinglish short. No Pakistan history unless asked. {search_ctx}"

    raw=ask_groq(sys, f"Hist {MEMORY[uid]['hist'][-300:]} Msg {text}") or ask_gemini(sys, f"Hist {MEMORY[uid]['hist'][-300:]} Msg {text}")
    if not raw or len(clean(raw, text))<2:
        raw="Jee Malik bolo kya hukam hai? 🔥" if is_owner else f"Jee {uname} bolo? 🔒"
    else:
        raw=clean(raw, text)

    # Final safety - agar abhi bhi Pakistan aa gaya aur user ne nahi pucha to hatao
    if "pakistan" not in low and "1947" in raw.lower():
        raw="La ilaha illallah Muhammadur Rasulullah ﷺ"

    ans=raw[:900]
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-800:]
    save_persist(); LAST_BOT_MSG[uid]=ans
    if not is_owner: ans+=" 🔒"
    return ans, OWNER_PREF.get("voice_on",False) and is_owner, False

def make_btns(is_owner=False, is_start=False):
    icon_btns = [{"text": "📋", "callback_data": "COPY"},{"text": "↗️", "callback_data": "FWD"},{"text": "👍", "callback_data": "LIKE"},{"text": "👎", "callback_data": "DISLIKE"}]
    if is_owner:
        if is_start: return [icon_btns]
        else: return None
    else:
        return [icon_btns]

@app.route("/", methods=["GET"])
def home(): return f"Rakan V35.2 Fixed G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {get_ist_str()}",200
@app.route("/debug", methods=["GET"])
def debug(): return f"V35.2 OWNER {OWNER_ID} G {len(GROQ_KEYS)} PREF {OWNER_PREF}",200

@app.route("/webhook", methods=["POST","GET"])
@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return debug() if "debug" in request.path.lower() else home()
    try:
        data=request.get_json(silent=True) or {}
        if "callback_query" in data:
            cq=data["callback_query"]; cid=str(cq["message"]["chat"]["id"]); uid=str(cq["from"]["id"]); cdata=cq["data"]
            last_id=LAST_MSG_ID.get(cid) or cq["message"]["message_id"]
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]}, timeout=5)
            except: pass
            if cdata=="COPY": tg_real_copy(cid, last_id, cid); return "ok",200
            if cdata=="FWD": tg_real_forward(cid, last_id, cid); return "ok",200
            if cdata in ["LIKE","DISLIKE"]:
                orv=upstash("get","RAKAN_LIKES") or {"like":0,"dislike":0,"logs":[]}
                if cdata=="LIKE": orv["like"]=orv.get("like",0)+1
                else: orv["dislike"]=orv.get("dislike",0)+1
                upstash("set","RAKAN_LIKES",orv)
                tg_send(OWNER_ID, f"🔔 {cdata} V35.2 From {uid}")
                tg_send(cid, "Shukriya ❤️" if cdata=="LIKE" else "Batao kya galat laga?")
                return "ok",200
            return "ok",200
        msg=data.get("message",{}) or {}; chat_id=msg.get("chat",{}).get("id"); user_id=str(msg.get("from",{}).get("id",0)); uname=msg.get("from",{}).get("first_name","user"); username=msg.get("from",{}).get("username","") or ""
        text=msg.get("text","") or msg.get("caption","") or ""; mid=msg.get("message_id"); is_voice=False
        if "voice" in msg or "audio" in msg:
            is_voice=True
            fid=msg.get("voice",{}).get("file_id") or msg.get("audio",{}).get("file_id")
            text=transcribe_voice(fid) or "[Voice]"
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID); is_queen=(username.lower()==QUEEN_USERNAME.lower())
        if is_owner: uname=MALIK_NAME
        ans, voice_flag, is_start = brain(text,user_id,is_owner,is_queen,uname,is_voice)
        if ans=="Archived": return "ok",200
        btns = make_btns(is_owner, is_start)
        tg_send(chat_id, ans, mid, btns)
        if voice_flag and is_owner:
            tg_send_voice(chat_id, ans, OWNER_PREF.get("voice_gender","female"))
        return "ok",200
    except Exception as e:
        print(f"ERR {e} {traceback.format_exc()}"); return "ok",200