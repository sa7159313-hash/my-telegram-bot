import os, time, json, re, datetime, requests, traceback
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)

# ENV
BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = str(os.environ.get("OWNER_ID","0"))
MY_URL = os.environ.get("MY_URL","").rstrip("/") or "https://my-telegram-bot-lime.vercel.app"
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

# FIXED KEYS - ONLY gsk_ and AIza
def get_keys():
    g,gm=[],[]
    for v in os.environ.values():
        for p in str(v).replace("\n",",").split(","):
            p=p.strip().strip('"').strip("'")
            if len(p)<10: continue
            if p.startswith("gsk_") and p not in g: g.append(p)
            elif (p.startswith("AIza") or p.startswith("aq") or p.startswith("AQ")) and p not in gm: gm.append(p)
    return list(dict.fromkeys(g)), list(dict.fromkeys(gm))
GROQ_KEYS,GEMINI_KEYS=get_keys()

def get_ist_str(): return (datetime.datetime.utcnow()+datetime.timedelta(hours=5,minutes=30)).strftime("%d %b %Y, %I:%M %p IST")

def tg_send(cid,txt,reply_id=None, buttons=None):
    try:
        p={"chat_id":cid,"text":txt[:3900]}
        if reply_id: p["reply_to_message_id"]=reply_id
        if buttons:
            fixed=[]
            for row in buttons:
                fixed.append([{"text": str(b), "callback_data": str(b)} if isinstance(b,str) else b for b in row])
            p["reply_markup"]=json.dumps({"inline_keyboard": fixed})
        r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=p, timeout=12).json()
        if r.get("ok"): LAST_MSG_ID[cid]=r["result"]["message_id"]
        print(f"SEND {r}")
        return r.get("ok",False)
    except Exception as e:
        print(f"SEND FAIL {e}"); return False

def tg_real_forward(from_chat, msg_id, to_chat):
    try:
        r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/forwardMessage", json={"chat_id":to_chat,"from_chat_id":from_chat,"message_id":msg_id}, timeout=10)
        print(f"REAL FORWARD {r.text}"); return r.status_code==200
    except Exception as e:
        print(f"FWD FAIL {e}"); return False

def tg_real_copy(from_chat, msg_id, to_chat):
    try:
        r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/copyMessage", json={"chat_id":to_chat,"from_chat_id":from_chat,"message_id":msg_id}, timeout=10)
        print(f"REAL COPY {r.text}"); return r.status_code==200
    except Exception as e:
        print(f"COPY FAIL {e}"); return False

def tg_send_voice(cid, text, gender="female"):
    try:
        if not ELEVEN_API_KEY: return False
        vid=FEMALE_VOICE_ID if gender=="female" else MALE_VOICE_ID
        rr=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key":ELEVEN_API_KEY,"Content-Type":"application/json"}, json={"text":text[:400],"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.5,"similarity_boost":0.8}}, timeout=15)
        if rr.status_code==200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":cid}, files={'voice':('v.mp3',rr.content,'audio/mpeg')}, timeout=20)
            return True
    except Exception as e: print(f"VOICE FAIL {e}")
    return False

def live_search(q):
    try:
        if TAVILY_KEY:
            r=requests.post("https://api.tavily.com/search", json={"api_key":TAVILY_KEY,"query":q,"max_results":2}, timeout=8)
            if r.status_code==200: return " | ".join([x["content"][:200] for x in r.json().get("results",[])])
        # fallback DuckDuckGo
        r=requests.get(f"https://api.duckduckgo.com/?q={q}&format=json", timeout=6).json()
        return r.get("AbstractText","")[:400]
    except: return ""

def transcribe_voice(file_id):
    try:
        fp=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()["result"]["file_path"]
        audio=requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=15).content
        for k in GROQ_KEYS:
            try:
                files={'file':('a.ogg',audio,'audio/ogg')}; data={'model':'whisper-large-v3'}
                rr=requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization": f"Bearer {k}"}, files=files, data=data, timeout=15)
                if rr.status_code==200: return rr.json().get("text","")
            except: continue
    except: pass
    return ""

def upstash(cmd,key,val=None):
    if not UPSTASH_URL or not UPSTASH_TOKEN: return None
    try:
        h={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        if cmd=="get":
            r=requests.get(f"{UPSTASH_URL}/get/{key}", headers=h, timeout=5)
            if r.status_code==200: d=r.json().get("result"); return json.loads(d) if d else None
        else: requests.post(f"{UPSTASH_URL}", headers=h, json=["SET",key,json.dumps(val)], timeout=5)
    except: pass
    return None

def load_persist():
    global MEMORY,PROFILES,OWNER_PREF,CHAT_LOG
    MEMORY=upstash("get","RAKAN_MEM") or {}; PROFILES=upstash("get","RAKAN_PROFILES") or {}; OWNER_PREF=upstash("get","RAKAN_PREF") or {"voice_gender":"ask","offline":False}; CHAT_LOG=upstash("get","RAKAN_LOGS") or []
def save_persist():
    upstash("set","RAKAN_MEM",MEMORY); upstash("set","RAKAN_PROFILES",PROFILES); upstash("set","RAKAN_PREF",OWNER_PREF); upstash("set","RAKAN_LOGS",CHAT_LOG[-500:])
load_persist()

def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<900
def mark_bad(k): BAD_KEYS[k]=time.time()
def detect_lang(t):
    if re.search(r'[\u0900-\u097F]', t): return "hindi"
    return "english" if len(re.findall(r'[a-zA-Z]', t))>len(t)*0.6 else "hinglish"
def clean(t,apology=False):
    if not apology: t=t.replace("🙏","")
    t=re.sub(r"I am (Groq|Gemini|OpenAI).*","I am Rakan, made by Malik",t,flags=re.I)
    return re.sub(r"\s+"," ",t).strip()[:900] or "Ha bolo Malik?"

def ask_groq(sys,user):
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in ["llama-3.3-70b-versatile","llama-3.1-8b-instant"]:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":sys},{"role":"user","content":user}],"temperature":0.4,"max_tokens":400}, timeout=12)
                if r.status_code==200: return r.json()["choices"][0]["message"]["content"]
                if r.status_code in [401,429]: mark_bad(k); break
            except: continue
    return None

def ask_gemini(sys,user):
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        try:
            genai.configure(api_key=k); model=genai.GenerativeModel("gemini-1.5-flash", system_instruction=sys)
            res=model.generate_content(user)
            if res.text: return res.text
        except Exception as e:
            if "429" in str(e): mark_bad(k)
            continue
    return None

def get_weather(city):
    try:
        city=city.title()
        if OPENWEATHER_KEY:
            r=requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric", timeout=6)
            if r.status_code==200: d=r.json(); return f"{d['name']}: {d['weather'][0]['description']}, {d['main']['temp']}C"
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
    total=PROFILES[uid]["total"]
    low=text.lower().strip()
    user_lang=detect_lang(text)
    is_apology="maaf" in low or "sorry" in low or "galti" in low

    if len(text.split())<12: PROFILES[uid]["style"]=text[:120]

    # 20 chats feedback to owner only
    if total%20==0 and is_owner:
        tg_send(OWNER_ID, f"📊 20 Chats Report Malik {get_ist_str()}\nUser {uname} total {total}\nSahi: short reply lang match\nGalat check: extra info, 🙏 misuse, religion bina bole\nStyle: {PROFILES[uid]['style']}")

    # Voice to voice only owner
    if is_owner and any(k in low for k in ["baat suno","voice me bolo","bol ke sunao","awaz me bolo"]):
        if OWNER_PREF.get("voice_gender")=="ask":
            return "Malik puch raha hu - Female ya Male voice me sunau? __ASKVOICE__", False
        gender=OWNER_PREF.get("voice_gender","female")
        last=LAST_BOT_MSG.get(uid,"Ji Malik bolo")
        return f"__VOICE__{gender}__{last}", True

    if any(k in low for k in ["ab se yahi","lock kar de","yahi ka batana"]):
        city=re.sub(r'.*yahi.*|.*lock.*','',low).strip().title() or LAST_CITY.get(uid) or "Varanasi"
        city=city.split()[0] if city else "Varanasi"
        PROFILES[uid]["city"]=city; save_persist()
        ans=f"Done Malik 📍 Lock: {city}"; LAST_BOT_MSG[uid]=ans; return ans, False

    if "location change" in low:
        PROFILES[uid]["city"]=""; save_persist(); ans="Location unlock"; LAST_BOT_MSG[uid]=ans; return ans, False

    if "mausam" in low or "weather" in low:
        city=PROFILES[uid].get("city") or LAST_CITY.get(uid) or "Varanasi"
        LAST_CITY[uid]=city; ans=f"🌤️ {get_weather(city)} | {get_ist_str()}"; LAST_BOT_MSG[uid]=ans; return ans, False

    if "/start" in low:
        if is_owner: ans=f"Welcome Shadow King 👑 Malik {MALIK_NAME}\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} Voice:{OWNER_PREF.get('voice_gender')} {get_ist_str()}"
        elif is_queen: ans=f"Hey Theodore 💜 Malik busy hai, bolo mai pahuncha dungi, sab badhiya? 😊"
        else: ans=f"Hey {uname} or bhai kya haal sab badhiya? bolo? 🔒" if user_lang!="english" else f"Hey {uname} how are you?"
        LAST_BOT_MSG[uid]=ans; return ans, False

    # Spam / Gali for other users
    is_spam = any(w in low for w in ["free money","lottery","xxx","sex chat"])
    is_abuse = any(w in low for w in ["madarchod","bhenchod","chutiya","gandu","bsdk"])
    if is_spam and not is_owner and not is_queen:
        ans="Archived"; return ans, False
    if is_abuse and not is_owner:
        ans="Oye tameez se baat kar, gali dega to double sunega samjha?"; LAST_BOT_MSG[uid]=ans; return ans, False

    # Live search if needed
    search_ctx=""
    if any(w in low for w in ["kya chal raha","price","news","ai","crypto","paisa","latest","duniya","aaj"]):
        search_ctx=live_search(text)[:600]

    if is_owner:
        sys=f"{MONARCH_LORE} OWNER Urdu Hinglish fix respectful. IST {get_ist_str()} Style {PROFILES[uid]['style']} Search {search_ctx} Rule: 1-2 lines short, 🙏 only apology, no religion unless Malik asks, full world knowledge."
    elif is_queen:
        sys=f"{MONARCH_LORE} Queen Theodore {QUEEN_USERNAME} - Malik ki bhabhi/queen, very pyar se Urdu Hinglish. Malik offline/busy bolo pahuncha dungi. Mimic Malik style. Search {search_ctx} Short."
    else:
        sys=f"{MONARCH_LORE} User lang {user_lang} MUST same lang reply, no error. Mimic casual like {PROFILES[uid]['style']} - if user says or bhai kya haal then you also or bhai sab badhiya. Search {search_ctx} Rule: Only as much asked, no extra, extra faults only to owner. Short 1-2 lines, 🙏 only apology."

    prompt=f"Hist {MEMORY[uid]['hist'][-500:]} Msg {text} Voice {is_voice}"
    raw=ask_groq(sys,prompt) or ask_gemini(sys,prompt) or f"Thodi der me bolo G:{len(GROQ_KEYS)}"
    ans=clean(raw, is_apology)
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-1500:]
    CHAT_LOG.append({"uid":uid,"user":text[:200],"bot":ans[:200],"time":get_ist_str()})
    save_persist(); LAST_BOT_MSG[uid]=ans
    if not is_owner and not is_queen: ans+=" 🔒"
    return ans, is_voice and is_owner

def make_btns(): return [[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]]

@app.route("/", methods=["GET"])
def home(): return f"Rakan V28 REAL G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {get_ist_str()} | <a href='/debug'>DEBUG</a>",200

@app.route("/debug", methods=["GET"])
def debug(): return f"BOT {'OK' if BOT_TOKEN else 'MISS'} OWNER {OWNER_ID} G {len(GROQ_KEYS)} GM {len(GEMINI_KEYS)} ELEVEN {'OK' if ELEVEN_API_KEY else 'MISS'} TAVILY {'OK' if TAVILY_KEY else 'MISS'} LAST {LAST_MSG_ID} PREF {OWNER_PREF}",200

@app.route("/webhook", methods=["POST","GET"])
@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method=="GET":
        if "debug" in request.path.lower(): return debug(),200
        return home()
    try:
        data=request.get_json(silent=True) or {}
        if "callback_query" in data:
            cq=data["callback_query"]; cid=cq["message"]["chat"]["id"]; uid=str(cq["from"]["id"])
            cdata=cq["data"]; orig_msg_id=cq["message"]["message_id"]
            last_id=LAST_MSG_ID.get(cid, orig_msg_id)
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]}, timeout=5)
            if cdata=="VOICE_FEMALE": OWNER_PREF["voice_gender"]="female"; save_persist(); tg_send(cid,"Female voice lock 👩"); return "ok",200
            if cdata=="VOICE_MALE": OWNER_PREF["voice_gender"]="male"; save_persist(); tg_send(cid,"Male voice lock 👨"); return "ok",200
            if cdata=="COPY":
                # 100% REAL COPY - copyMessage API
                ok=tg_real_copy(cid, last_id, cid)
                if not ok: tg_send(cid, f"Copy fail, yahi raha: {LAST_BOT_MSG.get(uid,'')[:500]}")
                return "ok",200
            if cdata=="FWD":
                # 100% REAL FORWARD - forwardMessage API
                ok=tg_real_forward(cid, last_id, cid)
                if not ok: tg_send(cid, "Forward fail")
                return "ok",200
            if cdata in ["LIKE","DISLIKE"]:
                tg_send(OWNER_ID, f"{cdata} from {uid} {LAST_BOT_MSG.get(uid,'')[:300]}")
                tg_send(cid, f"Thanks {cdata} Malik"); return "ok",200
            return "ok",200

        msg=data.get("message",{}) or {}; chat_id=msg.get("chat",{}).get("id"); user_id=str(msg.get("from",{}).get("id",0)); uname=msg.get("from",{}).get("first_name","user"); username=msg.get("from",{}).get("username","")
        text=msg.get("text","") or msg.get("caption","") or ""; mid=msg.get("message_id"); is_voice=False
        if "voice" in msg or "audio" in msg:
            is_voice=True
            fid=msg.get("voice",{}).get("file_id") or msg.get("audio",{}).get("file_id")
            text=transcribe_voice(fid) or "[Voice]"
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID)
        is_queen=(username.lower()==QUEEN_USERNAME.lower() or any(n in str(msg.get("contact",{}).get("phone_number","")) for n in QUEEN_NUMBERS))
        if is_owner: uname=MALIK_NAME

        ans, voice_flag = brain(text,user_id,is_owner,is_queen,uname,is_voice)

        if "__ASKVOICE__" in ans:
            tg_send(chat_id, ans.replace("__ASKVOICE__",""), mid, [[{"text":"👩 Female","callback_data":"VOICE_FEMALE"},{"text":"👨 Male","callback_data":"VOICE_MALE"}]])
            return "ok",200
        if ans.startswith("__VOICE__"):
            parts=ans.split("__"); gender=parts[2]; vtext="__".join(parts[3:])
            tg_send(chat_id, vtext, mid, make_btns())
            if is_owner: tg_send_voice(chat_id, vtext, gender)
            return "ok",200

        if ans=="Archived":
            # Spam ko archive samjho - owner ko bhejo
            tg_send(OWNER_ID, f"🚫 Archived spam from {uname} ({user_id}): {text[:200]}")
            return "ok",200

        tg_send(chat_id, ans, mid, make_btns())
        return "ok",200
    except Exception as e:
        print(f"ERR {e} {traceback.format_exc()}"); return "ok",200
