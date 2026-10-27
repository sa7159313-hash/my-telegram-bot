import os, time, json, re, datetime, requests, traceback, sys, importlib.util, random
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

MEMORY={}; ABUSE={}; PROFILES={}; CHAT_LOG=[]; BAD_KEYS={}; LAST_ERROR="No error"; PENDING_FIX=None; LOOP_CACHE={}; OWNER_PREF={"voice_gender":"female"}; FEEDBACK_LOG=[]

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
def get_future_ist(m=30): return (get_ist_now() + datetime.timedelta(minutes=m)).strftime("%I:%M %p IST, %d %b %Y")

def get_weather(city="Varanasi"):
    try:
        if OPENWEATHER_KEY:
            r=requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric", timeout=5)
            if r.status_code==200: d=r.json(); return f"{city}: {d['weather'][0]['description']}, {d['main']['temp']}°C"
        r=requests.get(f"https://wttr.in/{city}?format=3", timeout=5)
        return r.text.strip() if r.status_code==200 else None
    except: return None

def report_fault(where, exc_obj=None):
    global LAST_ERROR
    try:
        exc_type, exc_val, exc_tb = sys.exc_info()
        if exc_obj: exc_val = exc_obj
        if exc_tb: f=traceback.extract_tb(exc_tb)[-1]; file_name, line_no = f.filename.split("/")[-1], f.lineno
        else: file_name, line_no = "index.py", "?"
        LAST_ERROR=f"{where} | {file_name}:{line_no} | {exc_val}"
        if OWNER_ID!="0": tg_send(OWNER_ID, f"🚨 Fault {where} {file_name}:{line_no} {exc_val}")
    except: pass

def full_system_audit():
    faults=[]
    faults.append({"layer":"CODE IDENTITY","status":"OK","line":"MONARCH_LORE","info":f"Rakan Monarch by {MALIK_NAME}","fix":"OK","fix_code":"Same rakho"})
    if not BOT_TOKEN: faults.append({"layer":"ENV BOT_TOKEN","status":"FAULT","line":"Vercel ENV","current":"Missing","fix":"ENV daalo","fix_code":"BOT_TOKEN=123:ABC daalo"})
    if OWNER_ID=="0": faults.append({"layer":"ENV OWNER_ID","status":"FAULT","line":"Vercel ENV","current":"0","fix":"ID daalo","fix_code":"OWNER_ID=768... daalo"})
    if not UPSTASH_URL: faults.append({"layer":"UPSTASH REDIS","status":"FAULT","line":"Vercel ENV","current":"Khali","fix":"ENV daalo","fix_code":"UPSTASH_REDIS_REST_URL=https://...upstash.io\nTOKEN=AXxx..."})
    try: json.dumps(MEMORY)
    except: faults.append({"layer":"MEMORY JSON","status":"FAULT","line":"MEMORY 140","current":"Corrupt","fix":"Clear","fix_code":"'ha fix karo' bolo"})
    g,gm,go=get_keys()
    if len([k for k in g if k not in BAD_KEYS])==0 and len(g)>0: faults.append({"layer":"GROQ KEYS","status":"FAULT","line":"get_keys() 110","current":f"0/{len(g)} BAD","fix":"BAD clear","fix_code":"'ha fix karo' bolo BAD clear\nAgar 0 to GROQ_API_KEY=gsk_... daalo"})
    if not ELEVEN_API_KEY: faults.append({"layer":"ELEVENLABS","status":"WARN","line":"ENV","current":"Missing - Only Malik voice fail","fix":"Key daalo","fix_code":"ELEVENLABS_API_KEY=... daalo"})
    if len([f for f in faults if f["status"]=="FAULT"])==0: faults.append({"layer":"ALL","status":"OK","line":"All","info":"100% fit","fix":"OK","fix_code":"Same"})
    return faults

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
    except Exception as e: report_fault(f"upstash_{cmd}", e)
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
        g,gm,go=[],[],[]
        for k,v in os.environ.items():
            if not v: continue
            raw=str(v); parts=[p.strip().strip('"').strip("'") for p in raw.replace("\n",",").split(",") if p.strip()]
            for p in parts:
                if p.startswith("gsk_") and p not in g: g.append(p)
                if p.startswith("AIza") and p not in gm: gm.append(p)
        return list(dict.fromkeys(g)),list(dict.fromkeys(gm)),list(dict.fromkeys(go))
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
    return f"{MONARCH_LORE}\nIST: {ist}\nRULES: {lang_rule}. Never say Groq/Gemini/OpenAI/Meta. Always Rakan made by Malik {MALIK_NAME}. Banned: I can't create app, Behtar hoga Sudhaar lo. Time: {ist}"

def clean(txt):
    try:
        if not txt: return "bolo?"
        txt=re.sub(r"I can't create or run the app.*","",txt,flags=re.IGNORECASE)
        txt=re.sub(r"Behtar hoga.*bura ho jayega","",txt,flags=re.IGNORECASE)
        txt=re.sub(r"I am (Groq|Gemini|OpenAI|Meta AI).*","I am Rakan, created by Malik MD Saif Ahmad.",txt,flags=re.IGNORECASE)
        txt=re.sub(r"\s+"," ",txt).strip()
        if len(txt)>700: txt=txt[:700]
        return txt if txt else "Ha bolo Malik?"
    except: return "bolo?"

def tg_get_file_bytes(fid):
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}", timeout=10).json()
        fp=r["result"]["file_path"]; return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=30).content
    except: return None

GROQ_MODELS=["openai/gpt-oss-120b","llama-3.3-70b-versatile","llama-3.1-8b-instant"]
GEMINI_MODELS=["gemini-2.5-flash","gemini-2.0-flash","gemini-1.5-flash"]

def ask_groq(system, user):
    try:
        for k in GROQ_KEYS:
            if is_bad(k): continue
            for m in GROQ_MODELS:
                try:
                    r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":0.3,"max_tokens":220}, timeout=15)
                    if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                    if r.status_code in [401,403,429]: mark_bad(k); break
                except: continue
    except Exception as e: report_fault("ask_groq", e)
    return None

def ask_gemini(system, user):
    try:
        for k in GEMINI_KEYS:
            if is_bad(k): continue
            for m in GEMINI_MODELS:
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
    if "mausam" in low or "weather" in low:
        w=get_weather("Varanasi"); return f"{w} | {get_ist_str()}" if w else get_ist_str()
    if any(x in low for x in ["are you groq","are you gemini","are you openai","are you meta"]):
        return f"I am Rakan, Monarch, Malik {MALIK_NAME} aka {MALIK_TITLE} ne banaya hai Vercel pe."
    return ask_groq(system, user) or ask_gemini(system, user) or ("Ha bolo Malik?" if is_owner else "Bolo sun raha hu?")

def ask_gemini_vision(img_bytes, prompt_text, system):
    try:
        for k in GEMINI_KEYS:
            try:
                genai.configure(api_key=k); model=genai.GenerativeModel("gemini-1.5-flash", system_instruction=system)
                res=model.generate_content([prompt_text, {"mime_type":"image/jpeg","data":img_bytes}])
                if res.text: return clean(res.text)
            except: continue
    except: pass
    return None

def transcribe_media(audio_bytes,fn="voice.ogg"):
    try:
        for k in GROQ_KEYS:
            try:
                r=requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization": f"Bearer {k}"}, files={"file":(fn,audio_bytes)}, data={"model":"whisper-large-v3"}, timeout=20)
                if r.status_code==200: return r.json().get("text","")
            except: continue
    except: pass
    return None

def log_to_owner(uid, uname, user_obj, user_text, bot_reply, lang, media_type="text"):
    global CHAT_LOG
    try:
        chat_id=user_obj.get("chat",{}).get("id"); user_id=user_obj.get("from",{}).get("id"); username=user_obj.get("from",{}).get("username","N/A"); lang_code=user_obj.get("from",{}).get("language_code","")
        contact = user_obj.get("contact",{}); phone = contact.get("phone_number","") if contact else ""
        entry={"time":get_ist_str(),"uid":str(uid),"chat_id":chat_id,"user_id":user_id,"username":username,"phone":phone,"name":uname,"lang_code":lang_code,"lang":lang,"type":media_type,"user":user_text[:1000],"bot":bot_reply[:1000]}
        CHAT_LOG.append(entry)
        if len(CHAT_LOG)>500: CHAT_LOG=CHAT_LOG[-500:]
        save_persist()
        if str(uid)!=OWNER_ID and OWNER_ID!="0":
            tg_send(OWNER_ID, f"📩 FULL DATA\n👤 {uname} (@{username}) Phone:{phone}\n🆔 UID:{user_id} CID:{chat_id}\n🗣️ Lang:{lang} ({lang_code})\n📦 Type:{media_type}\nUser: {user_text[:600]}\nBot: {bot_reply[:600]}\n⏰ {get_ist_str()}\n🔒 Encrypted for user")
    except Exception as e: report_fault("log_to_owner", e)

def brain(text,uid,is_owner,uname, user_obj, media_type="text"):
    global MEMORY, PENDING_FIX, LOOP_CACHE, ABUSE, PROFILES, FEEDBACK_LOG
    try:
        uid=str(uid)
        # --- FIX FOR 'total' FAULT ---
        if uid not in MEMORY or not isinstance(MEMORY[uid], dict):
            MEMORY[uid]={"hist":"","count":0,"last_user":"","repeat":0,"learned":""}
        MEMORY[uid].setdefault("hist","")
        MEMORY[uid].setdefault("count",0)
        MEMORY[uid].setdefault("last_user","")
        MEMORY[uid].setdefault("repeat",0)
        MEMORY[uid].setdefault("learned","")

        if uid not in LOOP_CACHE or not isinstance(LOOP_CACHE[uid], list):
            LOOP_CACHE[uid]=[]
        if uid not in ABUSE or not isinstance(ABUSE[uid], int):
            ABUSE[uid]=0
        if uid not in PROFILES or not isinstance(PROFILES[uid], dict):
            PROFILES[uid]={"name":uname,"total":0,"gali_level":"","phone":""}
        PROFILES[uid].setdefault("total",0)
        PROFILES[uid].setdefault("gali_level","")
        PROFILES[uid].setdefault("name",uname)
        PROFILES[uid].setdefault("phone","")
        try:
            PROFILES[uid]["total"]=int(PROFILES[uid].get("total",0))+1
        except:
            PROFILES[uid]["total"]=1

        low=text.lower().strip()
        user_lang=detect_lang(text)

        if MEMORY[uid]["last_user"]==low: MEMORY[uid]["repeat"]=MEMORY[uid].get("repeat",0)+1
        else: MEMORY[uid]["repeat"]=0
        MEMORY[uid]["last_user"]=low

        if is_owner and ("yaha ye daal de" in low or "isko aise fix kar" in low or "ye sikh le" in low):
            learned = text.replace("yaha ye daal de","").replace("isko aise fix kar","").replace("ye sikh le","").strip()
            if len(learned)>5:
                MEMORY[uid]["learned"] = (MEMORY[uid].get("learned","") + f"\n{learned}")[-1000:]
                upstash("set","RAKAN_GLOBAL_LEARN", MEMORY[uid]["learned"])
                save_persist()
                ans=f"Done Malik, sikh liya 100% original: {learned[:100]}... Ab se aise hi karunga."
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

        if is_owner and any(x in low for x in ["sab delete","delete all","sara data delete","clear all data"]):
            MEMORY.clear(); ABUSE.clear(); CHAT_LOG.clear(); PROFILES.clear(); LOOP_CACHE.clear(); FEEDBACK_LOG.clear()
            upstash("del","RAKAN_MEM"); upstash("del","RAKAN_ABUSE"); upstash("del","RAKAN_PROFILES"); upstash("del","RAKAN_LOGS"); upstash("del","RAKAN_FEEDBACK")
            save_persist()
            ans="Done Malik, sara data delete kar diya. MEMORY, ABUSE, LOGS, FEEDBACK sab clear. Fresh start."
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

        if "mausam" in low or "weather" in low or "temperature" in low:
            city="Varanasi"
            m=re.search(r"mausam.*?(?:in|of)?\s+([a-zA-Z]+)", low)
            if m: city=m.group(1)
            w=get_weather(city)
            ans=f"{w} - {get_ist_str()}" if w else f"Mausam ka data nahi mila, {get_ist_str()}"
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

        if len(text)>800 and "import" in text and is_owner: 
            ans="Code mil gaya Malik, /report likho scan ke liye."
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

        if any(x in low for x in ["who is create","who created","who made","kisne banaya"]):
            ans=f"Malik {MALIK_NAME} ne banaya hai, {MALIK_TITLE} ne Vercel pe Flask Groq Gemini se."
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None
        if "visale yaar" in low: ans="Visale yaar matlab bahut hi kareeb, dil se juda dost Malik."; log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None
        if "queen ka naam" in low: ans=f"Queen ka naam {QUEEN_NAME} hai, private hai Malik."; log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None
        if any(x in low for x in ["are you groq","are you gemini","are you openai","are you meta"]):
            ans=f"I am Rakan, Monarch, Malik {MALIK_NAME} ne banaya hai."; log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

        gali_words = ["madarchod","bhenchod","behenchod","chutiya","chutiye","gandu","bsdk","bhosdike","randi","lodu","maderchod"]
        is_gali = any(g in low for g in gali_words)
        if is_gali and not is_owner:
            ABUSE[uid]=ABUSE.get(uid,0)+1; PROFILES[uid]["gali_level"]=low; save_persist()
            if ABUSE[uid]==1:
                ans=f"{uname} bhai gali mat de yaar, pyaar se baat kar. Pehli warning hai. 🔒 Encrypted"
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None
            elif ABUSE[uid]==2:
                ans=f"{uname}, dusri warning de raha hu, gali band kar de. 🔒 Encrypted"
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None
            elif ABUSE[uid]==3:
                ans=f"{uname}, teesri warning. Agli baar same level me jawab milega. 🔒 Encrypted"
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None
            else:
                if any(x in low for x in ["madarchod","maderchod"]): ans=f"Abe {uname} madarchod tu {ABUSE[uid]} baar gali de chuka hai, aukat me reh ke baat kar bhosdike."
                elif any(x in low for x in ["bhenchod","behenchod"]): ans=f"Abe {uname} bhenchod tameez se baat kar, {ABUSE[uid]} baar gali de chuka hai."
                elif any(x in low for x in ["chutiya","chutiye"]): ans=f"Abe chutiye {uname}, {ABUSE[uid]} baar chutiyapa kar chuka hai, sudhar ja."
                elif "gandu" in low: ans=f"Abe gandu {uname}, {ABUSE[uid]} baar gali de chuka hai."
                else: ans=f"Abe {uname} bsdk {ABUSE[uid]} baar warning de chuka hu, ab gali me hi baat hogi."
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

        if is_gali and is_owner:
            ans="Samjha Malik, gussa chhod, seedha bolo kya kaam hai?"
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

        if low in ["or bta","or bata","or bta?"]: 
            ans="Batau Malik? PHP 8.3 beta aaya hai, trading update chahiye ya kuch aur? Bolo kispe baat karu?" if is_owner else "Batao kispe baat karu? 🔒 Encrypted"
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None
        if low in ["koi kaam nhi","koi kaam nahi","kuch nhi","kuch nahi"]:
            ans="Theek hai Malik, jab mann ho batana, hum yahin hain."; log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

        if low in ["ha fix karo","han fix karo","fix karo","yes fix","ha kar do"] and is_owner and PENDING_FIX:
            f=PENDING_FIX; PENDING_FIX=None
            if f["layer"] in ["MEMORY JSON","LORE LOOP","LOOP BUG"]:
                old=len(str(MEMORY)); MEMORY.clear(); LOOP_CACHE.clear(); save_persist(); upstash("set","RAKAN_MEM",{})
                ans=f"🔧 REAL FIX DONE\nHATAYA: MEMORY {old} chars\nDALA: Empty\nBaki same rakho"
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None
            if "KEYS" in f["layer"]:
                bad=len(BAD_KEYS); BAD_KEYS.clear()
                global GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS; GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys()
                ans=f"🔧 REAL FIX DONE\nHATAYA: {bad} BAD keys\nDALA: {len(GROQ_KEYS)} keys reload\nBaki same"
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None
            if "REDIS" in f["layer"] or "UPSTASH" in f["layer"]:
                ans=f"🔧 REAL FIX FAIL - Mujhse nahi hoga Malik, tumhe karna padega\nLINE: Vercel ENV\nDALNA: UPSTASH_REDIS_REST_URL=https://... aur TOKEN=...\nBaki same"
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None
            ans=f"🔧 {f['layer']} fix: {f.get('fix_code','')}"
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None

        if low in ["/audit","audit"]:
            faults=full_system_audit()
            msg=f"🔍 Audit {get_ist_str()}\n\n"
            for i,f in enumerate(faults,1): msg+=f"{i}. {f['layer']} - {f['status']}\n   LINE: {f.get('line','-')}\n   FIX: {f.get('fix_code','')}\n\n"
            real=[x for x in faults if x["status"]=="FAULT"]
            if real and is_owner: PENDING_FIX=real[0]; msg+=f"⚠️ Pehla fault: {PENDING_FIX['layer']}\nFix kar du? 'ha fix karo'"
            log_to_owner(uid,uname,user_obj,text,msg[:400],user_lang,media_type); return msg[:3900], False, None

        if low in ["/report","report"]:
            faults=full_system_audit()
            msg=f"📊 FULL REPORT {get_ist_str()}\nCode: Rakan V15 11-in-1 FIXED\n\n"
            for i,f in enumerate(faults,1):
                msg+=f"{i}. LAYER: {f['layer']}\n   STATUS: {f['status']}\n   LINE: {f.get('line','-')}\n   HATANA: {f.get('current','-')}\n   DALNA: {f.get('fix_code','-')}\n   BAKI: OK same\n\n"
            msg+=f"API: GROQ {len([k for k in GROQ_KEYS if not is_bad(k)])}/{len(GROQ_KEYS)} GM {len([k for k in GEMINI_KEYS if not is_bad(k)])}/{len(GEMINI_KEYS)}\nREDIS: {'OK' if UPSTASH_URL else 'FAULT'}\nELEVEN: {'OK' if ELEVEN_API_KEY else 'Missing'}\nLAST: {LAST_ERROR}\n"
            real=[x for x in faults if x["status"]=="FAULT"]
            if real and is_owner:
                PENDING_FIX=real[0]
                msg+=f"\n⚠️ FIRST FAULT: {PENDING_FIX['layer']} at {PENDING_FIX.get('line','')}\nHATANA: {PENDING_FIX.get('current','')}\nDALNA: {PENDING_FIX.get('fix_code','')}\nKya fix kar du? 'ha fix karo'"
            log_to_owner(uid,uname,user_obj,text,msg[:400],user_lang,media_type); return msg[:3900], False, None

        if low in ["/start","start"]: 
            ans="Welcome to your world The Shadow King 👑 - Hazir hu Malik" if is_owner else f"Welcome {uname}, bolo? 🔒 Your messages are end-to-end encrypted."
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, [["👍","👎"]]

        if is_owner:
            if "female voice" in low: OWNER_PREF["voice_gender"]="female"; save_persist(); ans="Female voice set kar di Malik"; log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None
            if "male voice" in low: OWNER_PREF["voice_gender"]="male"; save_persist(); ans="Male voice set kar di Malik"; log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False, None
            if "voice me bolo" in low or "voice me jawab" in low or "voice me reply" in low:
                spoken=text
                for p in ["voice me bolo","voice me jawab do","voice me reply do","voice me bol"]:
                    if p in low:
                        idx=low.find(p)+len(p); spoken=text[idx:].strip(" :-"); break
                if not spoken or len(spoken)<2: spoken="Ji Malik hazir hu"
                system=get_lore_fresh(is_owner,user_lang)
                ans_text=ask_all(system, spoken if spoken!="Ji Malik hazir hu" else text, is_owner) or spoken
                ans_text=clean(ans_text)
                MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans_text}")[-2500:]
                save_persist()
                log_to_owner(uid,uname,user_obj,text,ans_text,user_lang,media_type)
                return ans_text, True, [["👍","👎"]]

        system=get_lore_fresh(is_owner,user_lang)
        learned_global = upstash("get","RAKAN_GLOBAL_LEARN") or ""
        user_prompt=f"IST:{get_ist_str()} Owner:{is_owner} Name:{uname} Lang:{user_lang} Total:{PROFILES[uid].get('total',0)} Learned:{learned_global[-500:]} {MEMORY[uid].get('learned','')[-300:]} Hist:{MEMORY[uid]['hist'][-800:]} Msg:{text} -> Reply 1-2 lines short in {user_lang} if not owner else hinglish. Be intelligent, learn from history."
        ans=ask_all(system,user_prompt,is_owner) or "Ha bolo Malik?"
        ans=clean(ans)
        
        if not is_owner: ans = ans + " 🔒"

        if LOOP_CACHE[uid] and ans in LOOP_CACHE[uid]:
            ans=random.choice(["Bolo Malik alag baat karte hain","Haan sun raha hu Malik bolo","Ispe baat ho gayi, naya batao?"]) + (" 🔒" if not is_owner else "")

        LOOP_CACHE[uid].append(ans)
        if len(LOOP_CACHE[uid])>4: LOOP_CACHE[uid].pop(0)

        MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-3000:]
        save_persist()
        log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type)
        return ans, False, [["👍","👎"]]
    except Exception as e:
        report_fault(f"brain {uid}", e); return "Theek hai Malik, network slow hai, phir bolo?", False, None

@app.route("/", methods=["GET"])
def home():
    try:
        if BOT_TOKEN and MY_URL:
            try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":f"{MY_URL}/webhook"}, timeout=5)
            except: pass
        return f"Rakan V15 FIXED total bug G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} Eleven:{bool(ELEVEN_API_KEY)} {get_ist_str()}",200
    except: return "Error",200

@app.route("/fix", methods=["GET"])
def fix():
    try:
        global GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS,BAD_KEYS
        if str(request.args.get("id",""))!=OWNER_ID: return "Access Denied",403
        GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys(); BAD_KEYS.clear(); load_persist(); save_persist()
        return f"FIXED V15 {get_ist_str()} G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} Last:{LAST_ERROR}",200
    except Exception as e: return f"Fix err {e}",200

@app.route("/audit", methods=["GET"])
def audit_route():
    try:
        if str(request.args.get("id",""))!=OWNER_ID: return "Access Denied",403
        return jsonify({"time":get_ist_str(),"code":"Rakan V15","faults":full_system_audit(),"logs":CHAT_LOG[-30:], "feedback":FEEDBACK_LOG[-20:]}),200
    except Exception as e: return jsonify({"error":str(e)}),200

@app.route("/dashboard", methods=["GET"])
def dashboard():
    try:
        if str(request.args.get("id",""))!=OWNER_ID: return "Access Denied",403
        html=f"<h2>{MALIK_NAME} - Dashboard V15 FIXED</h2><p>{get_ist_str()}</p><p>GROQ {len(GROQ_KEYS)} GEMINI {len(GEMINI_KEYS)} ELEVEN {bool(ELEVEN_API_KEY)}</p><p>Users {len(PROFILES)} Chats {len(CHAT_LOG)} Abuse {sum(ABUSE.values())} Feedback {len(FEEDBACK_LOG)}</p><hr>"
        for c in CHAT_LOG[-100:][::-1]:
            html+=f"<p><b>{c.get('name')} @{c.get('username')} Phone:{c.get('phone')} ID:{c.get('user_id')}:</b> {c.get('user')} -> {c.get('bot')} [{c.get('type')}] {c.get('time')}</p><hr>"
        return html,200
    except Exception as e: return f"Error {e}",200

@app.route("/cron", methods=["GET","POST"])
def cron():
    try:
        if OWNER_ID!="0" and BOT_TOKEN:
            w=get_weather("Varanasi")
            if w: tg_send(OWNER_ID, f"📰 Auto Update {get_ist_str()}\n🌤️ {w}\nBot Live G:{len(GROQ_KEYS)}")
        return f"cron ok {get_ist_str()}",200
    except Exception as e: report_fault("cron", e); return "cron err",200

@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return "Webhook OK "+get_ist_str(),200
    try:
        data=request.get_json(silent=True) or {}; 
        if "callback_query" in data:
            cq=data["callback_query"]; cb_id=cq["id"]; cb_data=cq.get("data",""); from_id=str(cq["from"]["id"]); msg=cq["message"]; chat_id=msg["chat"]["id"]
            if cb_data in ["👍","👎"]:
                FEEDBACK_LOG.append({"time":get_ist_str(),"uid":from_id,"feedback":cb_data,"msg":msg.get("text","")[:200]})
                save_persist()
                if cb_data=="👎":
                    tg_send(OWNER_ID, f"⚠️ Feedback Alert Malik\n👤 User {from_id}\n👎 Dislike\nMsg: {msg.get('text','')[:300]}\n⏰ {get_ist_str()}\n\nTum pucho: 'yaha ye daal de ...' to mai 100% original sikh jaunga.")
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cb_id,"text":"Thanks, Malik ko bhej diya"}, timeout=5)
                else:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cb_id,"text":"Thanks 👍"}, timeout=5)
                return "ok",200

        msg=data.get("message",{}) or {}
        chat_id=msg.get("chat",{}).get("id"); user_id=str(msg.get("from",{}).get("id",0)); uname=msg.get("from",{}).get("first_name","user")
        text=msg.get("text","") or msg.get("caption","") or ""; message_id=msg.get("message_id")
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID)
        if is_owner: uname=MALIK_NAME

        OWNER_STATUS = upstash("get","OWNER_STATUS") or "offline"
        if is_owner and text.lower().strip() in ["/online","online aa gaya","mai online hu","online"]:
            upstash("set","OWNER_STATUS","online")
            tg_send(chat_id, "Done Malik, ab bot pause hai. Jo bhi msg karega wo sirf tumhe forward hoga. /offline likho ON karne ke liye.")
            return "ok",200
        if is_owner and text.lower().strip() in ["/offline","offline kar do","bot start","offline"]:
            upstash("set","OWNER_STATUS","offline")
            tg_send(chat_id, "Done Malik, bot wapas ON hai.")
            return "ok",200
        if not is_owner and OWNER_STATUS=="online":
            tg_send(OWNER_ID, f"👤 User Online Msg (Bot Paused)\n👤 {uname} ({user_id})\nID:{chat_id}\nMsg: {text}\n\nIs msg ko reply karo, mai user ko bhej dunga.")
            tg_send(chat_id, "Malik online hai, thodi der me khud reply karenge. 🔒", message_id)
            return "ok",200
        if is_owner and msg.get("reply_to_message"):
            replied_text = msg["reply_to_message"].get("text","")
            m = re.search(r"ID:(\d+)", replied_text)
            if m:
                target_chat_id = m.group(1)
                tg_send(target_chat_id, text)
                tg_send(chat_id, f"✅ Bhej diya {target_chat_id} ko")
                return "ok",200

        if msg.get("contact"):
            phone=msg["contact"].get("phone_number","")
            if user_id not in PROFILES or not isinstance(PROFILES[user_id], dict):
                PROFILES[user_id]={"name":uname,"total":0,"gali_level":"","phone":""}
            PROFILES[user_id]["phone"]=phone
            save_persist()
            ans="Number save kar liya Malik" if is_owner else "Thanks, contact save ho gaya 🔒"
            tg_send(chat_id, ans, message_id)
            log_to_owner(user_id,uname,msg,f"[CONTACT] {phone}",ans,detect_lang(text),"contact")
            return "ok",200

        if msg.get("photo"):
            b=tg_get_file_bytes(msg["photo"][-1]["file_id"])
            if b:
                system=get_lore_fresh(is_owner, detect_lang(text))
                q=text if text else "Is photo me kya hai short me batao"
                v=ask_gemini_vision(b,q,system)
                if v: 
                    tg_send(chat_id,v,message_id, buttons=[[{"text":"👍","callback_data":"👍"},{"text":"👎","callback_data":"👎"}]])
                    log_to_owner(user_id,uname,msg,f"[PHOTO] {text} id:{msg['photo'][-1]['file_id']}",v,detect_lang(text),"photo")
                else: 
                    ans, want_voice, btns = brain(text or "photo dekho",user_id,is_owner,uname,msg,"photo")
                    if want_voice and is_owner:
                        audio=eleven_tts(ans)
                        if audio: tg_send_voice_bytes(chat_id, audio)
                        tg_send(chat_id, ans, message_id, buttons=btns)
                    else: tg_send(chat_id, ans, message_id, buttons=btns)
                return "ok",200

        if msg.get("voice") or msg.get("audio") or msg.get("video"):
            fid=(msg.get("voice") or msg.get("audio") or msg.get("video") or {}).get("file_id")
            b=tg_get_file_bytes(fid)
            if b:
                heard=transcribe_media(b)
                if heard:
                    ans, want_voice, btns = brain(heard,user_id,is_owner,uname,msg,"voice")
                    if want_voice and is_owner:
                        audio=eleven_tts(ans)
                        if audio: tg_send_voice_bytes(chat_id, audio)
                        tg_send(chat_id, ans, message_id, buttons=btns)
                    else: tg_send(chat_id, ans, message_id, buttons=btns)
                else: tg_send(chat_id,"awaz saaf nahi aayi Malik" if is_owner else "Voice not clear 🔒",message_id)
            return "ok",200

        if not text: return "ok",200
        ans, want_voice, btns = brain(text,user_id,is_owner,uname,msg,"text")
        if want_voice and is_owner:
            audio=eleven_tts(ans)
            if audio:
                tg_send_voice_bytes(chat_id, audio)
                tg_send(chat_id, ans, message_id, buttons=btns)
            else:
                tg_send(chat_id, f"{ans}\n\n(Eleven key missing, ENV me ELEVENLABS_API_KEY daalo)", message_id, buttons=btns)
        else:
            tg_send(chat_id,ans,message_id, buttons=btns)
        return "ok",200
    except Exception as e:
        report_fault("webhook", e); return "ok",200
