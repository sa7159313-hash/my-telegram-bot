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
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MALIK_NAME="MD Saif Ahmad"; MALIK_TITLE="The Shadow King"; QUEEN_NAME="Theodore"
MONARCH_LORE = f"""You are Rakan - The Monarch, King of Beasts, Royal Knight of {MALIK_TITLE} {MALIK_NAME}. Queen {QUEEN_NAME}. Made by Malik on Vercel Flask Groq Gemini. You are NOT Groq/Gemini/OpenAI/Meta. Extra: {LORE_ENV}"""

MEMORY={}; ABUSE={}; PROFILES={}; CHAT_LOG=[]; BAD_KEYS={}; LAST_ERROR="No error"; PENDING_FIX=None; LOOP_CACHE={}; OWNER_PREF={"voice_gender":"female"}

def tg_send(cid,txt,reply_id=None):
    try:
        p={"chat_id":cid,"text":txt[:3900]}
        if reply_id: p["reply_to_message_id"]=reply_id
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=p, timeout=12)
    except: pass

def tg_send_voice_bytes(cid, audio_bytes):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":cid}, files={"voice":("rakan.mp3", audio_bytes, "audio/mpeg")}, timeout=30)
        return True
    except: return False

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
        # No key needed, free wttr.in
        r=requests.get(f"https://wttr.in/{city}?format=3", timeout=5)
        if r.status_code==200 and r.text: return r.text.strip()
        # fallback open-meteo free
        r2=requests.get(f"https://wttr.in/{city}?format=%C+%t+%w", timeout=5)
        return r2.text.strip() if r2.status_code==200 else None
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
    faults.append({"layer":"CODE IDENTITY","status":"OK","line":"MONARCH_LORE 14","info":f"Rakan Monarch by {MALIK_NAME}","fix":"OK","fix_code":"Baki same rakho"})
    if not BOT_TOKEN: faults.append({"layer":"ENV BOT_TOKEN","status":"FAULT","line":"Vercel ENV BOT_TOKEN","current":"Missing","fix":"ENV daalo","fix_code":"BOT_TOKEN=123:ABC daalo"})
    if OWNER_ID=="0": faults.append({"layer":"ENV OWNER_ID","status":"FAULT","line":"Vercel ENV OWNER_ID","current":"0","fix":"ID daalo","fix_code":"OWNER_ID=768... daalo"})
    if not UPSTASH_URL: faults.append({"layer":"UPSTASH REDIS","status":"FAULT","line":"Vercel ENV UPSTASH","current":"Khali","fix":"ENV daalo","fix_code":"UPSTASH_REDIS_REST_URL=https://...upstash.io\nTOKEN=AXxx...\nBaki same"})
    try: json.dumps(MEMORY)
    except: faults.append({"layer":"MEMORY JSON","status":"FAULT","line":"MEMORY 140","current":"Corrupt","fix":"Clear","fix_code":"'ha fix karo' bolo, MEMORY.clear() hoga"})
    g,gm,go=get_keys()
    if len([k for k in g if k not in BAD_KEYS])==0 and len(g)>0: faults.append({"layer":"GROQ KEYS","status":"FAULT","line":"get_keys() 110","current":f"0/{len(g)} BAD","fix":"BAD clear","fix_code":"'ha fix karo' bolo line 230 pe BAD clear\nAgar 0 to GROQ_API_KEY=gsk_... Vercel ENV me daalo"})
    if not ELEVEN_API_KEY: faults.append({"layer":"ELEVENLABS","status":"WARN","line":"Vercel ENV ELEVENLABS_API_KEY","current":"Missing - Voice only for Malik will fail","fix":"Key daalo","fix_code":"ELEVENLABS_API_KEY=... daalo Vercel ENV me\nBaki code same, dusro ke liye voice band rahega"})
    if len([f for f in faults if f["status"]=="FAULT"])==0: faults.append({"layer":"ALL","status":"OK","line":"All","info":"100% fit","fix":"OK","fix_code":"Baki same"})
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
            r=requests.get(f"{UPSTASH_URL}/del/{key}", headers=headers, timeout=5)
            return True
    except Exception as e: report_fault(f"upstash_{cmd}", e)
    return None

def load_persist():
    global MEMORY,ABUSE,PROFILES,CHAT_LOG,OWNER_PREF
    try:
        if not UPSTASH_URL: return
        MEMORY=upstash("get","RAKAN_MEM") or {}; ABUSE=upstash("get","RAKAN_ABUSE") or {}
        PROFILES=upstash("get","RAKAN_PROFILES") or {}; CHAT_LOG=upstash("get","RAKAN_LOGS") or []
        OWNER_PREF=upstash("get","RAKAN_PREF") or OWNER_PREF
    except: pass
def save_persist():
    try:
        if not UPSTASH_URL: return
        upstash("set","RAKAN_MEM",MEMORY); upstash("set","RAKAN_ABUSE",ABUSE)
        upstash("set","RAKAN_PROFILES",PROFILES); upstash("set","RAKAN_LOGS",CHAT_LOG[-500:]); upstash("set","RAKAN_PREF",OWNER_PREF)
    except: pass
load_persist()

def get_keys():
    try:
        g,gm,go=[],[],[]
        for k,v in os.environ.items():
            if not v: continue
            raw=str(v); parts=[p.strip().strip('"').strip("'") for p in raw.replace("\n",",").split(",") if p.strip()]
            for p in parts:
                ku=k.upper()
                if "GEMINI" in ku and len(p)>20 and p not in gm: gm.append(p)
                if "GROQ" in ku and len(p)>10 and p not in g: g.append(p)
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
    ist=get_ist_str(); future=get_future_ist(30)
    lang_rule = "Hinglish short 1-2 lines" if is_owner else f"Same language as user: {user_lang} 1-2 lines. No extra English if Hindi."
    return f"""{MONARCH_LORE}
IST: {ist} Year {get_ist_now().year} Future {future}
RULES: {lang_rule}. Never say Groq/Gemini/OpenAI/Meta. Always Rakan made by Malik {MALIK_NAME}. Who made you? Malik MD Saif Ahmad. Banned: I can't create app, Behtar hoga Sudhaar lo. Short. Time: {ist}"""

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
    if any(x in low for x in ["are you groq","are you gemini","are you openai","are you meta","openai ne banaya"]):
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
        # Full data collection
        chat_id=user_obj.get("chat",{}).get("id"); user_id=user_obj.get("from",{}).get("id"); username=user_obj.get("from",{}).get("username","N/A"); first_name=user_obj.get("from",{}).get("first_name",""); language_code=user_obj.get("from",{}).get("language_code","")
        entry={"time":get_ist_str(),"uid":str(uid),"chat_id":chat_id,"user_id":user_id,"username":username,"name":uname,"lang_code":language_code,"lang":lang,"type":media_type,"user":user_text[:1000],"bot":bot_reply[:1000]}
        CHAT_LOG.append(entry)
        if len(CHAT_LOG)>500: CHAT_LOG=CHAT_LOG[-500:]
        save_persist()
        if str(uid)!=OWNER_ID and OWNER_ID!="0":
            # Full data to owner
            tg_send(OWNER_ID, f"📩 FULL DATA\n👤 {uname} (@{username})\n🆔 UID:{user_id} CID:{chat_id}\n🗣️ Lang:{lang} ({language_code})\n📦 Type:{media_type}\nUser: {user_text[:600]}\nBot: {bot_reply[:600]}\n⏰ {get_ist_str()}\n🔒 Encrypted view for user")
    except Exception as e: report_fault("log_to_owner", e)

def brain(text,uid,is_owner,uname, user_obj, media_type="text"):
    global MEMORY, PENDING_FIX, LOOP_CACHE, ABUSE, PROFILES
    try:
        uid=str(uid)
        if uid not in MEMORY: MEMORY[uid]={"hist":"","count":0,"last_user":"","repeat":0}
        if uid not in LOOP_CACHE: LOOP_CACHE[uid]=[]
        if uid not in ABUSE: ABUSE[uid]=0
        if uid not in PROFILES: PROFILES[uid]={"name":uname,"total":0,"gali_level":""}
        low=text.lower().strip()
        user_lang=detect_lang(text)
        PROFILES[uid]["total"]+=1

        if MEMORY[uid]["last_user"]==low: MEMORY[uid]["repeat"]+=1
        else: MEMORY[uid]["repeat"]=0
        MEMORY[uid]["last_user"]=low

        # Delete all - only owner
        if is_owner and any(x in low for x in ["sab delete","delete all","sara data delete","clear all data"]):
            MEMORY.clear(); ABUSE.clear(); CHAT_LOG.clear(); PROFILES.clear(); LOOP_CACHE.clear()
            upstash("del","RAKAN_MEM"); upstash("del","RAKAN_ABUSE"); upstash("del","RAKAN_PROFILES"); upstash("del","RAKAN_LOGS")
            save_persist()
            ans="Done Malik, sara data delete kar diya. MEMORY, ABUSE, LOGS, Upstash sab clear. Ab fresh start hai."
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False

        # Weather
        if "mausam" in low or "weather" in low or "temperature" in low:
            city="Varanasi"
            m=re.search(r"mausam.*?(?:in|of)?\s+([a-zA-Z]+)", low)
            if m: city=m.group(1)
            w=get_weather(city)
            ans=f"{w} - {get_ist_str()}" if w else f"Mausam ka data nahi mila, {get_ist_str()}"
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False

        if len(text)>800 and "import" in text and is_owner: 
            ans="Code mil gaya Malik, /report likho scan ke liye."
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False

        if any(x in low for x in ["who is create","who created","who made","kisne banaya","tumko kisne","tumhe kisne"]):
            ans=f"Malik {MALIK_NAME} ne banaya hai, {MALIK_TITLE} ne Vercel pe Flask Groq Gemini se."
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False
        if "visale yaar" in low: ans="Visale yaar matlab bahut hi kareeb, dil se juda dost Malik."; log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False
        if "queen ka naam" in low: ans=f"Queen ka naam {QUEEN_NAME} hai, private hai Malik."; log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False
        if any(x in low for x in ["are you groq","are you gemini","are you openai","are you meta"]):
            ans=f"I am Rakan, Monarch, Malik {MALIK_NAME} ne banaya hai."; log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False

        # === GALI SYSTEM FOR OTHER PERSON - 3 WARNING THEN SAME LEVEL ===
        gali_words = ["madarchod","bhenchod","behenchod","chutiya","chutiye","gandu","bsdk","bhosdike","randi","lodu","maderchod"]
        is_gali = any(g in low for g in gali_words)
        if is_gali and not is_owner:
            ABUSE[uid]+=1
            PROFILES[uid]["gali_level"]=low  # save level
            save_persist()
            if ABUSE[uid]==1:
                ans=f"{uname} bhai gali mat de yaar, pyaar se baat kar. Pehli warning hai. 🔒 Ye chat encrypted hai."
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False
            elif ABUSE[uid]==2:
                ans=f"{uname}, dusri warning de raha hu, gali band kar de. 🔒 Encrypted."
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False
            elif ABUSE[uid]==3:
                ans=f"{uname}, teesri warning. Agli baar same level me jawab milega. 🔒 Encrypted."
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False
            else:
                # After 3 warnings - same level gali - CONFIRM DENA HI DENA HAI
                # Detect level and reply same level
                if any(x in low for x in ["madarchod","maderchod"]):
                    ans=f"Abe {uname} madarchod tu {ABUSE[uid]} baar gali de chuka hai, aukat me reh ke baat kar bhosdike."
                elif any(x in low for x in ["bhenchod","behenchod"]):
                    ans=f"Abe {uname} bhenchod tameez se baat kar, {ABUSE[uid]} baar gali de chuka hai."
                elif any(x in low for x in ["chutiya","chutiye"]):
                    ans=f"Abe chutiye {uname}, {ABUSE[uid]} baar chutiyapa kar chuka hai, sudhar ja."
                elif "gandu" in low:
                    ans=f"Abe gandu {uname}, {ABUSE[uid]} baar gali de chuka hai, ab aukat dikha raha hai."
                else:
                    ans=f"Abe {uname} bsdk {ABUSE[uid]} baar warning de chuka hu, ab gali me hi baat hogi teri aukat pe."
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False

        # Abuse for owner is friendly
        if is_gali and is_owner:
            ans="Samjha Malik, gussa chhod, seedha bolo kya kaam hai?"
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False

        if low in ["or bta","or bata","or bta?"]: 
            ans="Batau Malik? PHP 8.3 beta aaya hai, trading update chahiye ya kuch aur? Bolo kispe baat karu?" if is_owner else "Batao kispe baat karu? 🔒 Encrypted."
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False
        if low in ["koi kaam nhi","koi kaam nahi","kuch nhi","kuch nahi"]:
            ans="Theek hai Malik, jab mann ho batana, hum yahin hain."; log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False
        if low in ["acha","achha","theek hai","ok","okkk"] and MEMORY[uid]["repeat"]>=1:
            ans=random.choice(["Haan bolo Malik, sun raha hu","Batao yaar kya soch rahe ho?"]); log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False

        if low in ["ha fix karo","han fix karo","fix karo","yes fix","ha kar do"] and is_owner and PENDING_FIX:
            f=PENDING_FIX; PENDING_FIX=None
            if f["layer"] in ["MEMORY JSON","LORE LOOP","LOOP BUG"]:
                old=len(str(MEMORY)); MEMORY.clear(); LOOP_CACHE.clear(); save_persist(); upstash("set","RAKAN_MEM",{})
                ans=f"🔧 REAL FIX DONE\nHATAYA: MEMORY {old} chars\nDALA: Empty\nBaki same rakho\nAb /report likho"
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False
            if "KEYS" in f["layer"]:
                bad=len(BAD_KEYS); BAD_KEYS.clear()
                global GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS; GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys()
                ans=f"🔧 REAL FIX DONE\nHATAYA: {bad} BAD keys\nDALA: {len(GROQ_KEYS)} keys reload\nBaki same"
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False
            if "REDIS" in f["layer"] or "UPSTASH" in f["layer"]:
                ans=f"🔧 REAL FIX FAIL - Mujhse nahi hoga Malik, tumhe karna padega\nLINE: Vercel ENV\nDALNA: UPSTASH_REDIS_REST_URL=https://... aur TOKEN=...\nBaki same"
                log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False
            ans=f"🔧 {f['layer']} fix: {f.get('fix_code','')}"
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False

        if low in ["/audit","audit","/diagnose","diagnose"]:
            faults=full_system_audit()
            msg=f"🔍 Audit {get_ist_str()}\n\n"
            for i,f in enumerate(faults,1): msg+=f"{i}. {f['layer']} - {f['status']}\n   LINE: {f.get('line','-')}\n   CURRENT: {f.get('current',f.get('info','-'))}\n   FIX: {f.get('fix_code','')}\n\n"
            real=[x for x in faults if x["status"]=="FAULT"]
            if real and is_owner: PENDING_FIX=real[0]; msg+=f"⚠️ Pehla fault: {PENDING_FIX['layer']} at {PENDING_FIX.get('line','')}\nFix kar du? 'ha fix karo'"
            log_to_owner(uid,uname,user_obj,text,msg[:400],user_lang,media_type); return msg[:3900], False

        if low in ["/report","report"]:
            faults=full_system_audit()
            msg=f"📊 FULL REPORT {get_ist_str()}\nCode: Rakan V13\n\n"
            for i,f in enumerate(faults,1):
                msg+=f"{i}. LAYER: {f['layer']}\n   STATUS: {f['status']}\n   LINE: {f.get('line','-')}\n   HATANA HAI: {f.get('current','-')}\n   DALNA HAI: {f.get('fix_code','-')}\n   BAKI CODE: OK same\n\n"
            msg+=f"API: GROQ {len([k for k in GROQ_KEYS if not is_bad(k)])}/{len(GROQ_KEYS)} GM {len([k for k in GEMINI_KEYS if not is_bad(k)])}/{len(GEMINI_KEYS)}\nREDIS: {'OK' if UPSTASH_URL else 'FAULT'}\nELEVEN: {'OK' if ELEVEN_API_KEY else 'Missing - Only Malik voice fail'}\nLAST: {LAST_ERROR}\n"
            real=[x for x in faults if x["status"]=="FAULT"]
            if real and is_owner:
                PENDING_FIX=real[0]
                msg+=f"\n⚠️ FIRST FAULT: {PENDING_FIX['layer']} at {PENDING_FIX.get('line','')}\nHATANA: {PENDING_FIX.get('current','')}\nDALNA: {PENDING_FIX.get('fix_code','')}\nBaki theek hai\nKya fix kar du? 'ha fix karo'"
            log_to_owner(uid,uname,user_obj,text,msg[:400],user_lang,media_type); return msg[:3900], False

        if low in ["/start","start"]: 
            ans="Welcome to your world The Shadow King 👑 - Hazir hu Malik" if is_owner else f"Welcome {uname}, bolo? 🔒 Your messages are end-to-end encrypted."
            log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False

        # Owner voice control - ONLY FOR MALIK
        want_voice=False
        if is_owner:
            if "female voice" in low: OWNER_PREF["voice_gender"]="female"; save_persist(); ans="Female voice set kar di Malik"; log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False
            if "male voice" in low: OWNER_PREF["voice_gender"]="male"; save_persist(); ans="Male voice set kar di Malik"; log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type); return ans, False
            if "voice me bolo" in low or "voice me jawab" in low or "voice me reply" in low:
                want_voice=True
                # extract what to speak
                spoken=text
                for p in ["voice me bolo","voice me jawab do","voice me reply do","voice me bol"]:
                    if p in low:
                        idx=low.find(p)+len(p); spoken=text[idx:].strip(" :-"); break
                if not spoken or len(spoken)<2: spoken="Ji Malik hazir hu"
                system=get_lore_fresh(is_owner,user_lang)
                # generate normal text first then speak
                ans_text=ask_all(system, spoken if spoken!="Ji Malik hazir hu" else text, is_owner) or spoken
                ans_text=clean(ans_text)
                # Save learning
                MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans_text}")[-2500:]
                save_persist()
                log_to_owner(uid,uname,user_obj,text,ans_text,user_lang,media_type)
                return ans_text, True

        # Normal learning brain
        system=get_lore_fresh(is_owner,user_lang)
        user_prompt=f"IST:{get_ist_str()} Owner:{is_owner} Name:{uname} Lang:{user_lang} TotalChats:{PROFILES[uid]['total']} Hist:{MEMORY[uid]['hist'][-800:]} Msg:{text} -> Reply 1-2 lines short in {user_lang} if not owner else hinglish. Learn from history, be more intelligent each time."
        ans=ask_all(system,user_prompt,is_owner) or "Ha bolo Malik?"
        ans=clean(ans)
        
        # Add encrypted note for other persons
        if not is_owner:
            ans = ans + " 🔒"

        if LOOP_CACHE[uid] and ans in LOOP_CACHE[uid]:
            ans=random.choice(["Bolo Malik alag baat karte hain","Haan sun raha hu Malik bolo","Ispe baat ho gayi, naya batao?"]) + (" 🔒" if not is_owner else "")

        LOOP_CACHE[uid].append(ans)
        if len(LOOP_CACHE[uid])>4: LOOP_CACHE[uid].pop(0)

        MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-3000:]  # Learning - more history for intelligence
        save_persist()
        log_to_owner(uid,uname,user_obj,text,ans,user_lang,media_type)
        return ans, False
    except Exception as e:
        report_fault(f"brain {uid}", e); return "Theek hai Malik, network slow hai, phir bolo?", False

@app.route("/", methods=["GET"])
def home():
    try:
        if BOT_TOKEN and MY_URL:
            try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":f"{MY_URL}/webhook"}, timeout=5)
            except: pass
        return f"Rakan V13 FIX ALL G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} Eleven:{bool(ELEVEN_API_KEY)} {get_ist_str()}",200
    except: return "Error",200

@app.route("/fix", methods=["GET"])
def fix():
    try:
        global GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS,BAD_KEYS
        if str(request.args.get("id",""))!=OWNER_ID: return "Access Denied",403
        GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys(); BAD_KEYS.clear(); load_persist(); save_persist()
        return f"FIXED V13 {get_ist_str()} G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} Eleven:{bool(ELEVEN_API_KEY)} Last:{LAST_ERROR}",200
    except Exception as e: return f"Fix err {e}",200

@app.route("/audit", methods=["GET"])
def audit_route():
    try:
        if str(request.args.get("id",""))!=OWNER_ID: return "Access Denied",403
        return jsonify({"time":get_ist_str(),"code":"Rakan V13","faults":full_system_audit(),"logs":CHAT_LOG[-30:]}),200
    except Exception as e: return jsonify({"error":str(e)}),200

@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return "Webhook OK "+get_ist_str(),200
    try:
        data=request.get_json(silent=True) or {}; msg=data.get("message",{}) or {}
        chat_id=msg.get("chat",{}).get("id"); user_id=str(msg.get("from",{}).get("id",0)); uname=msg.get("from",{}).get("first_name","user")
        text=msg.get("text","") or msg.get("caption","") or ""; message_id=msg.get("message_id")
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID)
        if is_owner: uname=MALIK_NAME

        if msg.get("photo"):
            b=tg_get_file_bytes(msg["photo"][-1]["file_id"])
            if b:
                system=get_lore_fresh(is_owner, detect_lang(text))
                q=text if text else "Is photo me kya hai short me batao"
                v=ask_gemini_vision(b,q,system)
                if v: 
                    tg_send(chat_id,v,message_id)
                    log_to_owner(user_id,uname,msg,f"[PHOTO] {text} id:{msg['photo'][-1]['file_id']}",v,detect_lang(text),"photo")
                else: 
                    ans, want_voice = brain(text or "photo dekho",user_id,is_owner,uname,msg,"photo")
                    if want_voice and is_owner:
                        audio=eleven_tts(ans)
                        if audio: tg_send_voice_bytes(chat_id, audio)
                        else: tg_send(chat_id,ans,message_id)
                    else: tg_send(chat_id,ans,message_id)
                return "ok",200

        if msg.get("voice") or msg.get("audio") or msg.get("video"):
            fid=(msg.get("voice") or msg.get("audio") or msg.get("video") or {}).get("file_id")
            b=tg_get_file_bytes(fid)
            if b:
                heard=transcribe_media(b)
                if heard:
                    ans, want_voice = brain(heard,user_id,is_owner,uname,msg,"voice")
                    if want_voice and is_owner:
                        audio=eleven_tts(ans)
                        if audio: tg_send_voice_bytes(chat_id, audio)
                        else: tg_send(chat_id,ans,message_id)
                    else: tg_send(chat_id,ans,message_id)
                else: tg_send(chat_id,"awaz saaf nahi aayi Malik" if is_owner else "Voice not clear 🔒",message_id)
            return "ok",200

        if not text: return "ok",200
        ans, want_voice = brain(text,user_id,is_owner,uname,msg,"text")
        if want_voice and is_owner:
            audio=eleven_tts(ans)
            if audio:
                tg_send_voice_bytes(chat_id, audio)
                tg_send(chat_id, ans, message_id)  # text bhi bhejo taaki dikhe
            else:
                tg_send(chat_id, f"{ans}\n\n(Eleven key missing, Vercel ENV me ELEVENLABS_API_KEY daalo)", message_id)
        else:
            tg_send(chat_id,ans,message_id)
        return "ok",200
    except Exception as e:
        report_fault("webhook", e); return "ok",200
