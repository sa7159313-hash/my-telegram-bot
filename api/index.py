import os, time, json, re, datetime, requests, traceback
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)

# ENV - Production only
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
QUEEN_NUMBERS=["8090862169","8187940221"]
MONARCH_LORE = f"You are Rakan - King of Beasts, Royal Knight of Shadow King {MALIK_NAME}. Made by Malik on Vercel. NOT Groq/Gemini. Islam A-Z Quran Hadith Fiqh Seerah, all religions, world knowledge till Oct 2026, live search. Extra:{LORE_ENV}"

MEMORY={}; PROFILES={}; CHAT_LOG=[]; BAD_KEYS={}; OWNER_PREF={}; LAST_BOT_MSG={}; LAST_MSG_ID={}; LAST_CITY={}

# V31 FIX - COMPLETE KEY PARSER
def get_keys():
    g,gm=[],[]
    for kname,v in os.environ.items():
        if not v: continue
        raw=str(v)
        for p in raw.replace("\n",",").replace(";",",").replace(" "," , ").split(","):
            p=p.strip().strip('"').strip("'").strip()
            if len(p)<15: continue
            if p.startswith("gsk_"):
                if p not in g: g.append(p)
            elif p.startswith("AIza") and len(p)>30:
                if p not in gm: gm.append(p)
            elif p.lower().startswith("aq") and len(p)>20 and " " not in p:
                # aq_ style gemini proxy keys
                if p not in gm: gm.append(p)
    return list(dict.fromkeys(g)), list(dict.fromkeys(gm))
GROQ_KEYS,GEMINI_KEYS=get_keys()

def get_ist_str(): return (datetime.datetime.utcnow()+datetime.timedelta(hours=5,minutes=30)).strftime("%d %b %Y, %I:%M %p IST")

def tg_send(cid,txt,reply_id=None, buttons=None):
    try:
        p={"chat_id":cid,"text":txt[:3900]}
        if reply_id: p["reply_to_message_id"]=reply_id
        if buttons:
            fb=[]
            for row in buttons:
                fb.append([{"text": str(b), "callback_data": str(b)} if isinstance(b,str) else b for b in row])
            p["reply_markup"]=json.dumps({"inline_keyboard": fb})
        r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=p, timeout=15).json()
        if r.get("ok"): LAST_MSG_ID[str(cid)]=r["result"]["message_id"]
        return r.get("ok",False)
    except Exception as e:
        print(f"SEND ERR {e}"); return False

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
        if TAVILY_KEY and len(q)>2:
            r=requests.post("https://api.tavily.com/search", json={"api_key":TAVILY_KEY,"query":q,"max_results":2,"include_answer":True}, timeout=8)
            if r.status_code==200:
                j=r.json(); return (j.get("answer","")+" | "+" | ".join([x.get("content","")[:200] for x in j.get("results",[])]))[:700]
        r=requests.get(f"https://api.duckduckgo.com/?q={requests.utils.quote(q)}&format=json", timeout=6)
        if r.status_code==200: return r.json().get("AbstractText","")[:400]
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
    MEMORY=upstash("get","RAKAN_MEM_V31") or upstash("get","RAKAN_MEM_V29") or {}
    PROFILES=upstash("get","RAKAN_PROFILES") or {}
    OWNER_PREF=upstash("get","RAKAN_PREF") or {"voice_gender":"ask"}
    CHAT_LOG=upstash("get","RAKAN_LOGS") or []
def save_persist():
    upstash("set","RAKAN_MEM_V31",MEMORY); upstash("set","RAKAN_PROFILES",PROFILES); upstash("set","RAKAN_PREF",OWNER_PREF); upstash("set","RAKAN_LOGS",CHAT_LOG[-500:])
load_persist()

def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<600
def mark_bad(k): BAD_KEYS[k]=time.time()
def detect_lang(t):
    if re.search(r'[\u0900-\u097F]', t): return "hindi"
    return "english" if len(re.findall(r'[a-zA-Z]', t))>len(t)*0.6 else "hinglish"
def clean(t,apology=False):
    if not apology: t=t.replace("🙏","")
    t=re.sub(r"I am (Groq|Gemini|OpenAI).*","I am Rakan, made by Malik",t,flags=re.I)
    return re.sub(r"\s+"," ",t).strip()[:900] or "Ha bolo Malik?"

# V31 FIX - GROQ NEVER FAIL LOGIC
def ask_groq(sys,user):
    if not GROQ_KEYS: return None
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "meta-llama/llama-4-scout-17b-16e-instruct", "qwen/qwen3.8-27b", "llama-3.3-70b-versatile"]
            try:
                r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":sys},{"role":"user","content":user}],"temperature":0.5,"max_tokens":350}, timeout=15)
                if r.status_code==200:
                    return r.json()["choices"][0]["message"]["content"]
                print(f"GROQ {m} {r.status_code} {r.text[:150]}")
                if r.status_code==429: mark_bad(k); break
                if r.status_code==401: mark_bad(k); break
            except Exception as e:
                print(f"GROQ EX {e}"); continue
    return None

def ask_gemini(sys,user):
    if not GEMINI_KEYS: return None
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        try:
            # aq_ keys are not real google keys, skip for direct SDK
            if k.lower().startswith("aq"): continue
            genai.configure(api_key=k)
            model=genai.GenerativeModel("gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.1-pro-preview", system_instruction=sys)
            res=model.generate_content(user)
            if res and getattr(res,'text',None): return res.text
        except Exception as e:
            print(f"GEMINI ERR {str(e)[:200]}")
            if "429" in str(e): mark_bad(k)
            continue
    # Fallback for aq_ style via HTTP if present
    for k in GEMINI_KEYS:
        if not k.lower().startswith("aq"): continue
        try:
            r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={k}", json={"contents":[{"parts":[{"text":f"{sys}\nUser:{user}"}]}],"safetySettings":[]}, timeout=15)
            if r.status_code==200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
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
    if uid not in PROFILES: PROFILES[uid]={"total":0,"style":"","city":""}
    PROFILES[uid]["total"]+=1
    low=text.lower().strip()
    user_lang=detect_lang(text)
    is_apology="maaf" in low or "sorry" in low

    if 3<len(text.split())<=10: PROFILES[uid]["style"]=text[:120]

    # ORV ADVANCE COMMAND
    if low.startswith("/orv") and is_owner:
        orv=upstash("get","RAKAN_LIKES") or {"like":0,"dislike":0,"logs":[]}
        ans=f"📊 ORV V31 {get_ist_str()}\n👍 {orv.get('like',0)} 👎 {orv.get('dislike',0)}\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}\n\nLast:\n"
        for l in orv.get('logs',[])[-6:]: ans+=f"{l['type']} {l['uid'][:5]}: {l['msg'][:30]}\n"
        LAST_BOT_MSG[uid]=ans; return ans, False

    if PROFILES[uid]["total"]%20==0 and is_owner:
        tg_send(OWNER_ID, f"📊 20 Report {uname} {PROFILES[uid]['total']} {get_ist_str()} Style:{PROFILES[uid]['style']}")

    if is_owner and any(k in low for k in ["baat suno","voice me bolo","bol ke sunao","awaz me bolo"]):
        if OWNER_PREF.get("voice_gender")=="ask": return "Malik puch raha hu - Female ya Male voice me sunau? __ASKVOICE__", False
        return f"__VOICE__{OWNER_PREF.get('voice_gender','female')}__{LAST_BOT_MSG.get(uid,'Ji Malik bolo')}", True

    if any(k in low for k in ["ab se yahi","lock kar de","yahi ka batana"]):
        city=re.sub(r'ab se yahi|lock kar de|yahi ka batana|ka mausam','',low,flags=re.I).strip().title().split()[0] if low.strip() else "Varanasi"
        if len(city)<2: city="Varanasi"
        PROFILES[uid]["city"]=city; LAST_CITY[uid]=city; save_persist()
        ans=f"Done Malik 📍 Lock: {city}"; LAST_BOT_MSG[uid]=ans; return ans, False

    if "location change" in low:
        PROFILES[uid]["city"]=""; LAST_CITY.pop(uid,None); save_persist()
        ans="Location unlock"; LAST_BOT_MSG[uid]=ans; return ans, False

    if "mausam" in low or "weather" in low:
        city=PROFILES[uid].get("city") or LAST_CITY.get(uid) or "Varanasi"
        ans=f"🌤️ {get_weather(city)} | {get_ist_str()}"; LAST_BOT_MSG[uid]=ans; return ans, False

    if low.startswith("/start"):
        if is_owner: ans=f"Welcome Shadow King 👑 Malik {MALIK_NAME}\nV31 G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} Voice:{OWNER_PREF.get('voice_gender')} TAVILY:{'ON' if TAVILY_KEY else 'OFF'} WEATHER:{'ON' if OPENWEATHER_KEY else 'OFF'} {get_ist_str()}"
        elif is_queen: ans=f"Hey Theodore 💜 Malik busy hai, bolo mai pahuncha dungi 😊"
        else: ans=f"Hey {uname} or bhai kya haal sab badhiya? bolo? 🔒" if user_lang!="english" else f"Hey {uname} how are you? 🔒"
        LAST_BOT_MSG[uid]=ans; return ans, False

    if any(w in low for w in ["free money","lottery","xxx"]) and not is_owner and not is_queen: return "Archived", False
    if any(w in low for w in ["madarchod","bhenchod","chutiya","bsdk"]) and not is_owner:
        ans="Oye tameez se baat kar"; LAST_BOT_MSG[uid]=ans; return ans, False

    search_ctx=live_search(text) if any(w in low for w in ["news","price","aaj","latest","kya chal","crypto"]) else ""

    if is_owner: sys=f"{MONARCH_LORE} OWNER Urdu Hinglish respectful. IST {get_ist_str()} City {PROFILES[uid].get('city')} Search {search_ctx} Rule: 1-2 lines short, 🙏 only apology, religion only if asked."
    elif is_queen: sys=f"{MONARCH_LORE} Queen Theodore {QUEEN_USERNAME} pyar se Urdu Hinglish. Search {search_ctx} Short."
    else: sys=f"{MONARCH_LORE} User lang {user_lang} same lang reply. Style {PROFILES[uid]['style']}. Search {search_ctx} Short 1-2 lines, 🙏 only apology."

    prompt=f"Hist {MEMORY[uid]['hist'][-500:]} Msg {text}"
    raw=ask_groq(sys,prompt) or ask_gemini(sys,prompt)
    if not raw:
        # FINAL FALLBACK - Never say Thodi der me bolo
        if user_lang=="english": raw="Hey I'm here, tell me? How can I help?"
        else: raw="Ha bolo Malik, sun raha hu, bolo kya chahiye?"

    ans=clean(raw, is_apology)
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-1500:]
    CHAT_LOG.append({"uid":uid,"user":text[:200],"bot":ans[:200],"time":get_ist_str()})
    save_persist(); LAST_BOT_MSG[uid]=ans
    if not is_owner and not is_queen: ans+=" 🔒"
    return ans, is_voice and is_owner

def make_btns(): return [[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]]

@app.route("/", methods=["GET"])
def home(): return f"Rakan V31 G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} TAVILY:{'OK' if TAVILY_KEY else 'MISS'} WEATHER:{'OK' if OPENWEATHER_KEY else 'MISS'} {get_ist_str()} <a href='/debug'>DEBUG</a>",200

@app.route("/debug", methods=["GET"])
def debug(): return f"V31 BOT {'OK' if BOT_TOKEN else 'MISS'} OWNER {OWNER_ID} G {len(GROQ_KEYS)} GM {len(GEMINI_KEYS)} TAVILY {'OK' if TAVILY_KEY else 'MISS'} WEATHER {'OK' if OPENWEATHER_KEY else 'MISS'} PREF {OWNER_PREF} LAST {LAST_MSG_ID} IST {get_ist_str()}",200

@app.route("/webhook", methods=["POST","GET"])
@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method=="GET":
        return debug() if "debug" in request.path.lower() or "debug" in request.args else home()
    try:
        data=request.get_json(silent=True) or {}
        if "callback_query" in data:
            cq=data["callback_query"]; cid=str(cq["message"]["chat"]["id"]); uid=str(cq["from"]["id"]); cdata=cq["data"]
            last_id=LAST_MSG_ID.get(cid) or cq["message"]["message_id"]
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]}, timeout=5)
            except: pass
            if cdata=="VOICE_FEMALE": OWNER_PREF["voice_gender"]="female"; save_persist(); tg_send(cid,"Female voice lock 👩"); return "ok",200
            if cdata=="VOICE_MALE": OWNER_PREF["voice_gender"]="male"; save_persist(); tg_send(cid,"Male voice lock 👨"); return "ok",200
            if cdata=="COPY": tg_real_copy(cid, last_id, cid); return "ok",200
            if cdata=="FWD": tg_real_forward(cid, last_id, cid); return "ok",200
            if cdata in ["LIKE","DISLIKE"]:
                orv=upstash("get","RAKAN_LIKES") or {"like":0,"dislike":0,"logs":[]}
                if cdata=="LIKE": orv["like"]=orv.get("like",0)+1
                else: orv["dislike"]=orv.get("dislike",0)+1
                orv.setdefault("logs",[]).append({"type":cdata,"uid":uid,"msg":LAST_BOT_MSG.get(uid,"")[:100],"time":get_ist_str()})
                orv["logs"]=orv["logs"][-100:]; upstash("set","RAKAN_LIKES",orv)
                tg_send(OWNER_ID, f"🔔 ORV {cdata} V31\nFrom {uid}\nMsg: {LAST_BOT_MSG.get(uid,'')[:200]}\nTotal 👍 {orv['like']} 👎 {orv['dislike']}")
                tg_send(cid, "Batao kya galat laga? 🙏" if cdata=="DISLIKE" else "Shukriya ❤️ noted")
                return "ok",200
            return "ok",200

        msg=data.get("message",{}) or {}; chat_id=msg.get("chat",{}).get("id"); user_id=str(msg.get("from",{}).get("id",0)); uname=msg.get("from",{}).get("first_name","user"); username=msg.get("from",{}).get("username","") or ""
        text=msg.get("text","") or msg.get("caption","") or ""; mid=msg.get("message_id"); is_voice=False
        if "voice" in msg or "audio" in msg:
            is_voice=True
            fid=msg.get("voice",{}).get("file_id") or msg.get("audio",{}).get("file_id")
            text=transcribe_voice(fid) or "[Voice]"
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID); is_queen=(username.lower()==QUEEN_USERNAME.lower() or any(n in username.lower() for n in ["pearly"]) or any(n in str(msg.get("contact",{}).get("phone_number","")) for n in QUEEN_NUMBERS))
        if is_owner: uname=MALIK_NAME
        ans, voice_flag = brain(text,user_id,is_owner,is_queen,uname,is_voice)
        if "__ASKVOICE__" in ans:
            tg_send(chat_id, ans.replace("__ASKVOICE__",""), mid, [[{"text":"👩 Female","callback_data":"VOICE_FEMALE"},{"text":"👨 Male","callback_data":"VOICE_MALE"}]])
            return "ok",200
        if ans.startswith("__VOICE__"):
            parts=ans.split("__"); gender=parts[2] if len(parts)>2 else "female"; vtext="__".join(parts[3:]) if len(parts)>3 else ans
            tg_send(chat_id, vtext, mid, make_btns())
            if is_owner: tg_send_voice(chat_id, vtext, gender)
            return "ok",200
        if ans=="Archived":
            tg_send(OWNER_ID, f"🚫 Spam {uname} ({user_id}): {text[:200]}")
            return "ok",200
        tg_send(chat_id, ans, mid, make_btns())
        return "ok",200
    except Exception as e:
        print(f"ERR {e} {traceback.format_exc()}"); return "ok",200
