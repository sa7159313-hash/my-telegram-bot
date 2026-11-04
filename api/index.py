import os, time, json, re, datetime, requests, traceback, random, urllib.parse
from flask import Flask, request
import google.generativeai as genai
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = str(os.environ.get("OWNER_ID","0")).strip()
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","").rstrip("/")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY","")
MALE_VOICE_ID = os.environ.get("ELEVEN_MALE_VOICE","pNInz6obpgDQGcFmaJgB")
FEMALE_VOICE_ID = os.environ.get("ELEVEN_FEMALE_VOICE","21m00Tcm4TlvDq8ikWAM")
OPENWEATHER_KEY = os.environ.get("OPENWEATHER_API_KEY","")
TAVILY_KEY = os.environ.get("TAVILY_API_KEY","")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MALIK_NAME="MD Saif Ahmad"
QUEEN_USERNAME="pearly_paradise15"
MEMORY={}; PROFILES={}; BAD_KEYS={}; OWNER_PREF={}; LAST_BOT_MSG={}; LAST_MSG_ID={}; LAST_USER_MSG={}; LAST_FULL_LOG={}; OWNER_LEARN_TEXT=""
BARAN_LORE="Main Rakan hu, The Beast King Monarch, 100 Level ka Monarch, Demon King Baran."

def get_keys():
    g,gm=set(),set()
    for env_name, val in os.environ.items():
        if not val: continue
        sval=str(val)
        for tok in re.split(r'[,\n\s;\'"]+', sval):
            tok=tok.strip()
            if len(tok)<20: continue
            if tok.startswith("gsk_"): g.add(tok)
            elif tok.startswith("AIza") or (tok.startswith("AQ") and len(tok)>30 and "vercel" not in tok.lower()): gm.add(tok)
        for m in re.findall(r'gsk_[A-Za-z0-9_-]{20,}', sval): g.add(m)
        for m in re.findall(r'AIza[0-9A-Za-z_-]{20,}', sval): gm.add(m)
    return list(g), list(gm)
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
def tg_send_photo(cid, prompt, reply_id=None):
    try:
        q=requests.utils.quote(prompt[:150])
        url=f"https://image.pollinations.ai/prompt/{q}?width=768&height=768&nologo=true&seed={random.randint(1,9999)}"
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id":cid,"photo":url,"caption":f"🔥 {prompt[:80]}","reply_to_message_id":reply_id}, timeout=25)
        return True
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
        rr=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key":ELEVEN_API_KEY,"Content-Type":"application/json"}, json={"text":text[:400],"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.55,"similarity_boost":0.8}}, timeout=25)
        if rr.status_code==200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":cid}, files={'voice':('v.mp3',rr.content,'audio/mpeg')}, timeout=20)
            return True
    except: pass
    return False

def live_search(q):
    try:
        if not TAVILY_KEY: return ""
        if len(q) < 7: return ""
        if q.lower().strip() in ["hi","hii","hello","salam","acha","ok","good","batao","or bata","kya kr rhe ho","walaikum assalaam","walaikum assalam"]: return ""
        r=requests.post("https://api.tavily.com/search", json={"api_key":TAVILY_KEY,"query":q,"max_results":3,"include_answer":True}, timeout=8)
        if r.status_code==200:
            j=r.json(); return (j.get("answer","")+" | "+" | ".join([x.get("content","")[:250] for x in j.get("results",[])]))[:700]
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
                d=r.json().get("result")
                if d is None: return None
                try: return json.loads(d)
                except: return d
        else:
            try:
                r=requests.post(f"{UPSTASH_URL}/pipeline", headers=h, json=[["SET",key,json.dumps(val)]], timeout=5)
                if r.status_code==200: return True
            except: pass
            try:
                enc=urllib.parse.quote(json.dumps(val), safe='')
                r2=requests.post(f"{UPSTASH_URL}/set/{key}/{enc}", headers=h, timeout=5)
                if r2.status_code==200: return True
            except: pass
            return True
    except: return None
    return None

def load_persist():
    global MEMORY,PROFILES,OWNER_PREF,OWNER_LEARN_TEXT,LAST_BOT_MSG
    MEMORY=upstash("get","RAKAN_MEM_V62") or upstash("get","RAKAN_MEM_V60") or {}
    PROFILES=upstash("get","RAKAN_PROFILES_V62") or upstash("get","RAKAN_PROFILES_V60") or {}
    p=upstash("get","RAKAN_PREF")
    if isinstance(p, dict) and p: OWNER_PREF=p
    else: OWNER_PREF={"voice_gender":"female","voice_on":True,"full_log":True}
    learn=upstash("get","RAKAN_LEARN_V62") or upstash("get","RAKAN_LEARN_V60") or {}
    if isinstance(learn, dict): OWNER_LEARN_TEXT = learn.get("text","")[:2000]
    elif isinstance(learn, str): OWNER_LEARN_TEXT = learn[:2000]
    lbm=upstash("get","RAKAN_LASTBOT_V62") or {}
    if isinstance(lbm, dict): LAST_BOT_MSG=lbm
load_persist()
def save_persist():
    upstash("set","RAKAN_MEM_V62",MEMORY); upstash("set","RAKAN_PROFILES_V62",PROFILES); upstash("set","RAKAN_PREF",OWNER_PREF); upstash("set","RAKAN_LASTBOT_V62",LAST_BOT_MSG)
def save_learn(new_text):
    global OWNER_LEARN_TEXT
    OWNER_LEARN_TEXT = (OWNER_LEARN_TEXT + f" | {new_text}")[-2000:]
    upstash("set","RAKAN_LEARN_V62",{"text":OWNER_LEARN_TEXT,"updated":get_ist_str()})
    save_persist()
    return True
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<600
def mark_bad(k): BAD_KEYS[k]=time.time()

def clean(t, user_query="", is_owner=False):
    if not t: return ""
    # V62: Block code + markdown
    if "import os" in t and "def " in t and len(t)>300: return "Code samajh gaya Malik, batao kya fix karna hai? 🔥"
    if "BOT_TOKEN" in t and len(t)>100: return "Token safe hai Malik, batao kya kaam hai? 🔥"
    t = t.replace("**","").replace("##","").replace("###","")
    t = re.sub(r'\|{1,}', ' ', t)
    t = re.sub(r'---+', '', t)
    leak_list=[
        "yeh message Beast King style mein banaya gaya hai","banaya gaya hai sirf aapke liye","sirf aapke liye","Beast King style","cleaned","deeps, left","Bot Lives","Auto V4","Broken Clouds, 29.23","Humidity 50%","billi-billi","billi billi","vastavik","Kshetra","Udaharan","Speech & Language","Kshamta, jisse"," - jaise ki pattern pehchan","15 words","Complex","Max 15","max_tokens","system_instruction","Hist ","Msg ","User:","Bot:","Be ready for the next challenge"
    ]
    for lp in leak_list: t=t.replace(lp,"")
    t=re.sub(r'(?i)\b(laude|lauda|bosdike|bhosdike|maderchod|madarchod|behenchod|bhenchod|gand|lund|chutiya|randi)\b', '', t)
    t=t.replace("🙏","")
    low_q=user_query.lower()
    if not is_owner:
        limit=350 if any(w in low_q for w in ["ai kya hai","billionaire","advance","python","kaise","kya karu"]) else 80
    else:
        limit=400 if any(w in low_q for w in ["ai kya hai","billionaire","advance","python","kaise","kya karu","human ne"]) else 50
    words=t.split()
    if len(words) > limit:
        cut=" ".join(words[:limit])
        if "." in cut: cut=cut.rsplit(".",1)[0]+"."
        t=cut
    t=re.sub(r"\s+"," ",t).strip()
    return t[:2500]

def ask_groq(sys,user, max_t=400):
    if not GROQ_KEYS: return None
    MODELS=["openai/gpt-oss-20b","llama-3.3-70b-versatile"]
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":sys},{"role":"user","content":user}],"temperature":0.7,"max_tokens":max_t}, timeout=20)
                if r.status_code==200:
                    txt=r.json()["choices"][0]["message"]["content"]
                    if txt and len(txt)>10: return txt
                if r.status_code in [401,429]: mark_bad(k); break
            except: continue
    return None
def ask_gemini(sys,user, max_t=400):
    if not GEMINI_KEYS: return None
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        try:
            genai.configure(api_key=k)
            model=genai.GenerativeModel("gemini-2.5-flash", system_instruction=sys)
            res=model.generate_content(user, generation_config={"temperature":0.7,"max_output_tokens":max_t})
            if res and getattr(res,'text',None): return res.text
        except Exception as e:
            if "429" in str(e) or "401" in str(e): mark_bad(k)
            continue
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

def brain(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid):
    global MEMORY,PROFILES,LAST_BOT_MSG,LAST_USER_MSG,OWNER_LEARN_TEXT
    uid=str(uid)
    if uid not in MEMORY: MEMORY[uid]={"hist":""}
    if uid not in PROFILES: PROFILES[uid]={"total":0,"city":"Varanasi","username":username,"lang":lang,"custom_name":"","dont_call":"","tone":"hinglish","user_learn":""}
    PROFILES[uid]["total"]+=1; LAST_USER_MSG[uid]=text; low=text.lower().strip()
    prof=PROFILES[uid]; display_name=prof.get("custom_name") or uname

    # V62 FIX: Code paste ko history me save hi mat karo
    if len(text)>500 and ("import os" in text or "BOT_TOKEN" in text or "def brain" in text or "api/index" in text):
        return "Code samajh gaya Malik, batao kya fix karna hai isme? 🔥 Main check kar leta hu.", False, False

    if low.startswith("/start"):
        v_on="ON 🔊" if OWNER_PREF.get("voice_on") else "OFF 🔇"
        if is_owner:
            learn_show=f"{len(OWNER_LEARN_TEXT)} chars" if OWNER_LEARN_TEXT else "0 chars - `yaad rakh` bol ke sikhao"
            ans=f"Assalamu Alaikum Malik 👑 {MALIK_NAME}\nWelcome to your world, The Shadow King 👑\nTera Rakan V62 Ultimate hazir hai 🔥\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}\nVoice:{OWNER_PREF.get('voice_gender')} {v_on}\nLearn:{learn_show}\nImage: ON 🎨\n{get_ist_str()}"
        else:
            ans=f"Assalamu Alaikum {display_name} 👋\nMain Rakan hu, The Beast King Monarch 🔥"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, True

    if "shadow king kaun" in low: return f"Tum hi ho Malik, {MALIK_NAME} 👑🔥", False, False
    if "kisne banaya" in low or "who made you" in low: return "mujhe mere the shadow king md saif ahmad ne banaya", False, False
    if "tum kya ho" in low or "who are you" in low: return f"Main Rakan hu Malik, The Beast King Monarch, 100 Level ka Monarch 🔥 {BARAN_LORE}", False, False
    if "location kya hai" in low: return f"Tumhari location {PROFILES[uid].get('city','Varanasi')} hai Malik 📍 {get_ist_str()}", False, False
    if "kalma" in low: return "Pehela Kalma Tayyab: La ilaha illallah Muhammadur Rasulullah ﷺ", False, False
    if "time kya" in low: return f"Abhi {get_ist_time_only()} ho raha hai Malik 📍 {get_ist_str()}", False, False
    if "who i am" in low or "mai kaun hu" in low: return f"Tum Malik ho, {MALIK_NAME}, Shadow King 👑🔥", False, False
    if "mausam" in low or "weather" in low:
        city="Prayagraj" if "prayagraj" in low or "allahabad" in low else PROFILES[uid].get("city","Varanasi")
        return f"🌤️ {get_weather(city)} | {get_ist_str()}", False, False

    # V62 Salam fix
    if "walaikum" in low and "assalam" in low:
        return "Walaikum Assalam Malik, Alhamdulillah sab khair khairiyat hai, aap sunao kya hukam hai? 👑🔥", False, False

    search_ctx=live_search(text)
    max_t=400
    hist = MEMORY[uid]['hist'][-400:]  # V62: 1500 -> 400, code leak band
    learn_ctx = f"Malik ne sikhaya: {OWNER_LEARN_TEXT[-400:]}" if OWNER_LEARN_TEXT and is_owner else ""

    if is_owner:
        sys=f"""You are Rakan, made by Malik MD Saif Ahmad, The Shadow King. You are advanced like ChatGPT and Meta AI.
RULES:
- Reply in Hinglish Roman, friendly like Meta AI.
- NEVER use tables with | | . NEVER use **bold** flood or ### headings. Use simple paragraphs and 1. 2. 3. points.
- For AI kya hai: Explain in simple words, 2026 me kitna advance hai - ChatGPT, video, voice, agents.
- For billionaire kaise banu: Give 5 PRACTICAL AI ideas, step by step, that normal human did not do much. Example: 1. AI Agency for local shops in Naraini, 2. AI Voice + WhatsApp auto reply for business, 3. Small SaaS tool, 4. Faceless YouTube with AI, 5. AI Health. No theory.
- Never say billi-billi, vastavik, Kshetra. Never say yeh message Beast King style me.
- Keep short for hi/acha, detailed for big questions.
{learn_ctx} History:{hist} Time:{get_ist_str()} Search:{search_ctx}"""
    else:
        sys=f"""You are Rakan, The Beast King Monarch, 100 Level. Helpful like ChatGPT and Meta AI. No tables, no ** flood. User is {display_name}. History {hist} Search:{search_ctx}"""

    raw=ask_groq(sys, f"User says: {text}", max_t) or ask_gemini(sys, f"User says: {text}", max_t)
    if not raw: raw="Walaikum Assalam Malik, Alhamdulillah sab khairiyat hai, bolo kya hukam hai? 👑🔥" if "walaikum" in low else "Jee Malik bolo kya hukam hai? 🔥"
    raw=clean(raw, text, is_owner)
    if raw==LAST_BOT_MSG.get(uid,""): raw=ask_groq(sys, f"User says: {text} (reply differently)", max_t) or raw
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text[-100]}\nR:{raw[-100]}")[-400:]
    save_persist(); LAST_BOT_MSG[uid]=raw
    if not is_owner: raw+=" 🔒"
    should_voice = is_owner and (mtype=="voice" and OWNER_PREF.get("voice_on",True) or "voice me" in low)
    return raw, should_voice, False

def make_btns(is_owner=False, is_start=False):
    if is_owner and is_start: return [[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]]
    elif not is_owner: return [[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]]
    else: return None

@app.route("/", methods=["GET"])
def home(): return f"Rakan V62 G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {get_ist_str()}",200
@app.route("/webhook", methods=["POST","GET"])
@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return home()
    try:
        data=request.get_json(silent=True) or {}
        if "callback_query" in data:
            cq=data["callback_query"]; cid=str(cq["message"]["chat"]["id"]); uid=str(cq["from"]["id"]); cdata=cq["data"]
            last_id=LAST_MSG_ID.get(cid) or cq["message"]["message_id"]
            last_user_text=LAST_USER_MSG.get(uid,"-"); last_bot_text=LAST_BOT_MSG.get(uid,"-")
            profile=PROFILES.get(uid,{}); uname=profile.get("username","-")
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]}, timeout=5)
            except: pass
            if cdata=="COPY": tg_real_copy(cid, last_id, cid); return "ok",200
            if cdata=="FWD": tg_real_forward(cid, last_id, cid); return "ok",200
            if cdata in ["LIKE","DISLIKE"]:
                orv=upstash("get","RAKAN_LIKES") or {"like":0,"dislike":0}
                if cdata=="LIKE": orv["like"]=orv.get("like",0)+1
                else: orv["dislike"]=orv.get("dislike",0)+1
                upstash("set","RAKAN_LIKES",orv)
                tg_send(OWNER_ID, f"📩 V62 {uname} {uid} {cdata} User:{last_user_text} Bot:{last_bot_text} {get_ist_str()}")
                tg_send(cid, "Shukriya ❤️" if cdata=="LIKE" else "Batao kya galat laga?")
                return "ok",200
            return "ok",200
        msg=data.get("message",{}) or {}; chat_id=msg.get("chat",{}).get("id"); user_id=str(msg.get("from",{}).get("id",0)); uname=msg.get("from",{}).get("first_name","user"); username=msg.get("from",{}).get("username","") or ""; lang=msg.get("from",{}).get("language_code","") or "en"; mtype="text"
        text=msg.get("text","") or msg.get("caption","") or ""; mid=msg.get("message_id")
        if "voice" in msg or "audio" in msg:
            mtype="voice"; fid=msg.get("voice",{}).get("file_id") or msg.get("audio",{}).get("file_id"); text=transcribe_voice(fid) or "[Voice]"
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID)
        if is_owner: uname=MALIK_NAME
        ans, voice_flag, is_start = brain(text,user_id,is_owner,False,uname,username,lang,mtype,chat_id)
        btns=make_btns(is_owner, is_start)
        tg_send(chat_id, ans, mid, btns)
        if voice_flag and is_owner: tg_send_voice(chat_id, ans, OWNER_PREF.get("voice_gender","female"))
        if not is_owner and OWNER_PREF.get("full_log",True):
            if len(text.strip()) >=5 and text.lower().strip() not in ["hi","hii","ok","good","hey","hello","seo kh","seo","accha"]:
                now=time.time()
                if now - LAST_FULL_LOG.get(user_id,0) > 180:
                    try:
                        tg_send(OWNER_ID, f"📩 FULL MSG V62\n👤 {uname} (@{username})\nUID:{user_id}\nUser: {text[:500]}\nBot: {ans[:500]}\n{get_ist_str()}")
                        LAST_FULL_LOG[user_id]=now
                    except: pass
        return "ok",200
    except Exception as e:
        print(f"ERR {e} {traceback.format_exc()}"); return "ok",200
