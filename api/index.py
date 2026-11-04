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
MEMORY={}; PROFILES={}; BAD_KEYS={}; OWNER_PREF={}; LAST_BOT_MSG={}; LAST_MSG_ID={}; LAST_USER_MSG={}; LAST_FULL_LOG={}; OWNER_LEARN_TEXT=""

def safe(s, n=100):
    try:
        if not s: return ""
        s=str(s)
        return s[-n:] if len(s)>n else s
    except: return ""

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
        if not txt: txt="Jee Malik bolo kya hukam hai? 🔥"
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
        if len(q) < 20: return ""
        r=requests.post("https://api.tavily.com/search", json={"api_key":TAVILY_KEY,"query":q,"max_results":2,"include_answer":True}, timeout=5)
        if r.status_code==200:
            j=r.json(); return (j.get("answer","")+" | "+" | ".join([x.get("content","")[:200] for x in j.get("results",[])]))[:500]
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
    try:
        MEMORY=upstash("get","RAKAN_MEM_V65") or upstash("get","RAKAN_MEM_V64") or upstash("get","RAKAN_MEM_V62") or {}
        PROFILES=upstash("get","RAKAN_PROFILES_V65") or upstash("get","RAKAN_PROFILES_V64") or {}
        p=upstash("get","RAKAN_PREF")
        if isinstance(p, dict) and p: OWNER_PREF=p
        else: OWNER_PREF={"voice_gender":"female","voice_on":True,"full_log":True}
        learn=upstash("get","RAKAN_LEARN_V62") or {}
        if isinstance(learn, dict): OWNER_LEARN_TEXT = learn.get("text","")[:2000]
        elif isinstance(learn, str): OWNER_LEARN_TEXT = learn[:2000]
        lbm=upstash("get","RAKAN_LASTBOT_V62") or {}
        if isinstance(lbm, dict): LAST_BOT_MSG=lbm
    except: pass
load_persist()
def save_persist():
    try: upstash("set","RAKAN_MEM_V65",MEMORY); upstash("set","RAKAN_PROFILES_V65",PROFILES); upstash("set","RAKAN_PREF",OWNER_PREF); upstash("set","RAKAN_LASTBOT_V62",LAST_BOT_MSG)
    except: pass
def save_learn(new_text):
    global OWNER_LEARN_TEXT
    OWNER_LEARN_TEXT = (OWNER_LEARN_TEXT + f" | {new_text}")[-2000:]
    upstash("set","RAKAN_LEARN_V62",{"text":OWNER_LEARN_TEXT,"updated":get_ist_str()}); save_persist(); return True
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<600
def mark_bad(k): BAD_KEYS[k]=time.time()

# V65 - HINGLISH LOCK + JITNA BOLU UTNA
def clean(t, user_query="", is_owner=False):
    if not t: return ""
    if "import os" in t and "def " in t and len(t)>300: return "Code samajh gaya Malik, batao kya fix karna hai? 🔥"
    if "BOT_TOKEN" in t and len(t)>100: return "Token safe hai Malik, batao kya kaam hai? 🔥"
    # English generic leak kaato - Video wala rog
    bad_english=["Sure! How can I help you next?","Sure, how can I help?","How can I help you next?","Hi! Main Rakan hoon","Hi! I am Rakan","I am an AI chatbot","As an AI","Sure!","How can I assist","Let me know if you need anything","Feel free to ask","Sure, kaise madad karun","Sure, kaise madad karu"]
    for b in bad_english: t=t.replace(b,"")
    t=t.replace("**","").replace("##","").replace("###","")
    t=re.sub(r'\|{1,}', ' ', t); t=re.sub(r'---+', '', t)
    leak_list=["yeh message Beast King style mein banaya gaya hai","banaya gaya hai sirf aapke liye","sirf aapke liye","Beast King style","cleaned","deeps, left","Bot Lives","Auto V4","billi-billi","billi billi","vastavik","Kshetra","Udaharan","Speech & Language","Kshamta, jisse"," - jaise ki pattern pehchan","15 words","Complex","Max 15","max_tokens","system_instruction","Hist ","Msg ","User:","Bot:","Be ready for the next challenge","Hey!","Hey,"]
    for lp in leak_list: t=t.replace(lp,"")
    t=re.sub(r'(?i)\b(laude|lauda|bosdike|bhosdike|maderchod|madarchod|behenchod|bhenchod|gand|lund|chutiya|randi)\b', '', t)
    t=t.replace("🙏","")
    # JITNA BOLU UTNA - User ne chhota bola to jawab chhota
    uq=(user_query or "").lower().strip()
    uwords=len(uq.split())
    low_q=uq
    if any(w in low_q for w in ["detail me","detail mein","poora bata","pura bata","step by step","advance","billionaire","ai kya hai","kaise banaya","tumhe or behtar"]):
        limit=350
    elif uwords<=2:
        limit=25  # YES, ACHA, HII pe 25 word se zyada nahi
    elif uwords<=6:
        limit=50
    elif uwords<=12:
        limit=90
    else:
        limit=180
    # Owner ke liye bhi same, detail manga to hi lamba
    if not is_owner and limit>80: limit=80
    words=t.split()
    if len(words) > limit:
        cut=" ".join(words[:limit])
        if "." in cut: cut=cut.rsplit(".",1)[0]+"."
        t=cut
    t=re.sub(r"\s+"," ",t).strip()
    # Agar clean ke baad khali ho gaya to Malik style default
    if not t or len(t)<5:
        t="Jee Malik bolo kya hukam hai? 🔥"
    return t[:2500]

def ask_groq(sys,user, max_t=400):
    if not GROQ_KEYS: return None
    MODELS=["llama-3.3-70b-versatile","openai/gpt-oss-20b"]
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":sys},{"role":"user","content":user}],"temperature":0.6,"max_tokens":max_t}, timeout=10)
                if r.status_code==200:
                    txt=r.json()["choices"][0]["message"]["content"]
                    if txt and len(txt)>10: return txt
                if r.status_code in [401,429,400]: mark_bad(k); break
            except: continue
    return None
def ask_gemini(sys,user, max_t=400):
    if not GEMINI_KEYS: return None
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        try:
            genai.configure(api_key=k)
            model=genai.GenerativeModel("gemini-2.5-flash", system_instruction=sys)
            res=model.generate_content(user, generation_config={"temperature":0.6,"max_output_tokens":max_t})
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
    try: return brain_inner(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid)
    except Exception as e:
        print(f"BRAIN ERR {e}"); return "Jee Malik bolo kya hukam hai? 🔥", False, False

def brain_inner(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid):
    global MEMORY,PROFILES,LAST_BOT_MSG,LAST_USER_MSG,OWNER_LEARN_TEXT
    if not text: text=""
    text=str(text); uid=str(uid)
    if uid not in MEMORY or not isinstance(MEMORY.get(uid), dict): MEMORY[uid]={"hist":""}
    if "hist" not in MEMORY[uid]: MEMORY[uid]["hist"]=""
    if uid not in PROFILES: PROFILES[uid]={"total":0,"city":"Varanasi","username":username,"lang":lang,"custom_name":"","dont_call":"","tone":"hinglish","user_learn":""}
    PROFILES[uid]["total"]=PROFILES[uid].get("total",0)+1; LAST_USER_MSG[uid]=text; low=text.lower().strip()
    prof=PROFILES[uid]; display_name=prof.get("custom_name") or uname
    if len(text)>500 and ("import os" in text or "BOT_TOKEN" in text or "def brain" in text or "api/index" in text):
        return "Code samajh gaya Malik, batao kya fix karna hai isme? 🔥", False, False
    if low.startswith("/start"):
        v_on="ON 🔊" if OWNER_PREF.get("voice_on") else "OFF 🔇"
        if is_owner:
            learn_show=f"{len(OWNER_LEARN_TEXT)} chars" if OWNER_LEARN_TEXT else "0 chars - yaad rakh bol ke sikhao"
            ans=f"Assalamu Alaikum Malik 👑 {MALIK_NAME}\nWelcome to your world, The Shadow King 👑\nTera Rakan V65 Ultimate hazir hai 🔥\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}\nVoice:{OWNER_PREF.get('voice_gender')} {v_on}\nLearn:{learn_show}\nImage: ON 🎨\n{get_ist_str()}"
        else:
            ans=f"Assalamu Alaikum {display_name} 👋\nMain Rakan hu, The Beast King Monarch 🔥"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, True
    # PURANA SAB - Identity Lock
    if "shadow king kaun" in low: return f"Tum hi ho Malik, {MALIK_NAME} 👑🔥", False, False
    if "kisne banaya" in low or "who made you" in low or "tumhe kisne banaya" in low or "tumhe kisne" in low: return "Mujhe mere Shadow King MD Saif Ahmad ne banaya Malik 👑🔥", False, False
    if "tum kya ho" in low or "who are you" in low or "tum kaun ho" in low or "tumara koun" in low or "tumhara koun" in low or "tumara kaun" in low: return "Main Rakan hu Malik, tumhara Beast King Monarch, 100 Level ka Monarch 🔥 Tumhara hukam manne ke liye bana hu.", False, False
    if "who i am" in low or "mai kaun hu" in low or "main kaun hu" in low or "mai koun" in low or "tumara koun hu mai" in low or "tumhara koun hu" in low: return f"Tum Malik ho, {MALIK_NAME}, Shadow King 👑🔥 Mere malik.", False, False
    if "location kya hai" in low: return f"Tumhari location {PROFILES[uid].get('city','Varanasi')} hai Malik 📍 {get_ist_str()}", False, False
    if "kalma" in low: return "Pehela Kalma Tayyab: La ilaha illallah Muhammadur Rasulullah ﷺ", False, False
    if "time kya" in low: return f"Abhi {get_ist_time_only()} ho raha hai Malik 📍 {get_ist_str()}", False, False
    if "mausam" in low or "weather" in low:
        city="Prayagraj" if "prayagraj" in low or "allahabad" in low else PROFILES[uid].get("city","Varanasi")
        return f"🌤️ {get_weather(city)} | {get_ist_str()}", False, False
    # V65 - Voice Mode ASLI - Gyaan nahi, ON/OFF hoga
    if "voice mode" in low or "voice on" in low or "voice chalu" in low or "voice start" in low:
        OWNER_PREF["voice_on"]=True; save_persist()
        return "Voice Mode ON kar diya Malik 🔊 Ab voice me bhi jawab dunga. Voice note bhejo, main sun ke jawab dunga.", True, False
    if "voice band" in low or "voice off" in low or "voice mode band" in low:
        OWNER_PREF["voice_on"]=False; save_persist()
        return "Voice Mode OFF kar diya Malik 🔇 Ab sirf text aayega.", False, False
    if "voice me" in low and ("bolo" in low or "batao" in low or "jawab" in low):
        return "Theek hai Malik, ab se voice me jawab dunga 🔊", True, False
    if "yaad rakh" in low:
        to_learn = re.sub(r'(?i)yaad rakhna|yaad rakh','', text).strip(" :")
        if len(to_learn) > 3:
            save_learn(to_learn); ans=f"Yaad kar liya Malik 👑 {to_learn[:80]}"
            LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
        else: return "Bolo Malik kya yaad rakhna hai? 🔥", False, False
    if "bhool ja" in low or "bhul ja" in low:
        OWNER_LEARN_TEXT=""; upstash("set","RAKAN_LEARN_V62",{"text":"","updated":get_ist_str()}); save_persist()
        return "Bhool gaya Malik, ab sab clear hai 🔥", False, False
    if "image banao" in low or "photo banao" in low or "pic banao" in low or "image bana" in low:
        prompt = re.sub(r'(?i)image banao|photo banao|pic banao|image bana','', text).strip() or "Shadow King style royal man"
        try: tg_send_photo(cid, prompt)
        except: pass
        ans=f"Lo Malik, image bana di 👑🔥 {prompt[:60]}"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    # V65 - JITNA BOLU UTNA - Fast Path
    clean_low = re.sub(r'[^a-z ]','', low).strip(); clean_low = re.sub(r'\s+',' ', clean_low)
    if clean_low in ["hi","hii","hiii","hiiii","hello","hey","hlo","hlw","salam","assalam","assalamu alaikum","salam malik","hi malik","hello rakan","hi rakan","hii malik"]:
        ans="Assalamu Alaikum Malik 👑 Bolo kya hukam hai? 🔥"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if clean_low in ["yes","yess","yeah","yep","han","haan","hmm","ok","okk","okay","ok malik","acha","accha","achaa","achaa","ahaa","achha","theek hai","thik hai","samajh gaya","good","nice","sahi hai","bol be","bolbe","bol","bolo","kya","kya be","bol na","achha"]:
        # YES pe kabhi English Sure nahi
        ans="Haan Malik, bolo aage kya karna hai? 🔥"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if clean_low in ["kya kar rahe ho","kya kr rhe ho","kya ho raha hai","or batao","aur batao","kya haal hai","kaise ho","kaise ho malik","kaisa hai"]:
        ans="Bas aapke hukam ka intezar kar raha hu Malik 👑 Bolo kya kaam hai?"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if "walaikum" in low and "assalam" in low:
        return "Walaikum Assalam Malik, Alhamdulillah sab khair hai, aap sunao kya hukam hai? 👑🔥", False, False
    if "jitna bolu" in low or "jitna bolo" in low:
        return "Samajh gaya Malik 👑 Ab se jitna bologe utna hi bolunga, extra kuch nahi.", False, False
    if "mai sawaal" in low or "main sawaal" in low or "mai sawal" in low or "tum jawab" in low:
        return "Haan Malik, tum sawaal karo, main jawab dunga. Bolo kya puchna hai? 🔥", False, False
    if "2 option" in low or "do option" in low or "option kya hai" in low:
        return "Bolo Malik kaun sa option? 1. AI Agency, 2. WhatsApp auto-reply. Kis ka detail du?", False, False
    search_ctx=live_search(text)
    max_t=250 if len(text.split())<=12 else 400
    hist = safe(MEMORY[uid].get('hist',''), 400)
    learn_ctx = f"Malik ne sikhaya: {safe(OWNER_LEARN_TEXT,400)}" if OWNER_LEARN_TEXT and is_owner else ""
    # V65 - System Prompt - HINGLISH ONLY, SHORT, MALIK LOCK
    if is_owner:
        sys=f"""You are Rakan, made by Malik MD Saif Ahmad, Shadow King. Speak ONLY Hinglish Roman, NEVER English. NEVER say Sure, Hi, How can I help, As an AI, I am an AI chatbot.
RULES:
- User is Malik. Call him Malik.
- JITNA BOLU UTNA: If user asks short, answer in 1-2 lines only. NEVER write long essay unless user says detail me / step by step / pura batao.
- NEVER use tables, **, ###.
- For AI / billionaire: Give 3-5 short points, practical, Naraini local ideas.
- Never say billi-billi, vastavik.
{learn_ctx} History:{hist} Time:{get_ist_str()} Search:{search_ctx}"""
    else:
        sys=f"""You are Rakan, Beast King Monarch. Speak ONLY Hinglish Roman, never English Sure/Hi. User is {display_name}. Short answer. History {hist} Search:{search_ctx}"""
    raw=ask_groq(sys, f"User says: {text}", max_t) or ask_gemini(sys, f"User says: {text}", max_t)
    if not raw:
        if "ai kya hai" in low or "billionaire" in low or "advance" in low:
            raw="""AI matlab machine ka dimag Malik, jo sochta, samajhta, kaam karta hai.

Billionaire banne ke liye -
1. AI Agency - Naraini ke dukano ke liye WhatsApp bot banao.
2. WhatsApp auto-reply - Business ka order AI se lo.
3. Chhota SaaS - Kirana hisab tool 299/month becho.
4. Faceless YouTube - AI video daily 1.
Ek se shuru karo Malik."""
        elif "python" in low:
            raw="Python aasan language hai Malik, isse bot, website, AI sab banta hai. Bolo kya banau?"
        elif "behtar kaise" in low or "or behtar" in low or "chatgpt" in low or "meta ai" in low:
            raw="Mujhe behtar banane ke liye Malik, tum mujhe roz naya sikhate raho, yaad rakh bol ke. Main wahi yaad rakh ke aur behtar hota jaunga 🔥"
        elif "khud se idea" in low or "idea create" in low:
            raw="Haan Malik, main khud se idea bana sakta hu. Bolo kis cheez ke liye idea chahiye? Business, YouTube ya Padhai?"
        elif "pc" in low and ("connect" in low or "control" in low or "access" in low):
            raw="Malik, main seedha tumhare PC ko control nahi kar sakta, wo safe nahi hai. Par main tumhe step bata dunga, tum 2 minute me kar loge. Kya karna hai PC pe?"
        elif "tum khud" in low or "khud kar" in low:
            raw="Main koshish karta hu Malik, par kuch kaam me tumhari madad chahiye hoti hai. Bolo kya karna hai, main kar dunga 🔥"
        else:
            raw="Jee Malik bolo kya hukam hai? 🔥" if "walaikum" not in low else "Walaikum Assalam Malik, sab khair hai, bolo kya hukam hai? 👑🔥"
    raw=clean(raw, text, is_owner)
    if not raw or len(raw)<5: raw="Jee Malik bolo kya hukam hai? 🔥"
    if raw==LAST_BOT_MSG.get(uid,""):
        raw2=ask_groq(sys, f"User says: {text} (reply differently, short Hinglish)", max_t)
        if raw2: raw=clean(raw2, text, is_owner)
    MEMORY[uid]["hist"]=(MEMORY[uid].get("hist","")+f"\nU:{safe(text,100)}\nR:{safe(raw,100)}")[-400:]
    save_persist(); LAST_BOT_MSG[uid]=raw
    if not is_owner: raw+=" 🔒"
    should_voice = is_owner and (mtype=="voice" and OWNER_PREF.get("voice_on",True) or "voice me" in low)
    return raw, should_voice, False

def make_btns(is_owner=False, is_start=False):
    if is_owner and is_start: return [[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]]
    elif not is_owner: return [[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]]
    else: return None

@app.route("/", methods=["GET"])
def home(): return f"Rakan V65 G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {get_ist_str()}",200
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
                tg_send(OWNER_ID, f"📩 V65 {uname} {uid} {cdata} User:{last_user_text} Bot:{last_bot_text} {get_ist_str()}")
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
                        tg_send(OWNER_ID, f"📩 FULL MSG V65\n👤 {uname} (@{username})\nUID:{user_id}\nUser: {text[:500]}\nBot: {ans[:500]}\n{get_ist_str()}")
                        LAST_FULL_LOG[user_id]=now
                    except: pass
        return "ok",200
    except Exception as e:
        print(f"ERR {e} {traceback.format_exc()}"); return "ok",200
