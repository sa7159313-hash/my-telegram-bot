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

def get_keys():
    g,gm=set(),set()
    for env_name, val in os.environ.items():
        if not val: continue
        sval=str(val)
        tokens=re.split(r'[,\n\s;\'"]+', sval)
        for tok in tokens:
            tok=tok.strip()
            if len(tok)<20: continue
            if tok.startswith("gsk_"): g.add(tok)
            elif tok.startswith("AIza"): gm.add(tok)
            elif tok.startswith("AQ") and len(tok)>30 and "vercel" not in tok.lower() and "http" not in tok.lower():
                gm.add(tok)
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
    except Exception as e: print(f"voice err {e}")
    return False

def live_search(q):
    try:
        if not TAVILY_KEY: return ""
        if len(q) < 5: return ""
        if q.lower().strip() in ["hi","hii","hello","salam","acha","ok","good","batao","or bata","kya kr rhe ho","kya kr skte ho"]: return ""
        if len(q.split()) < 2 and "sanskrit" not in q.lower() and "seo" not in q.lower(): return ""
        r=requests.post("https://api.tavily.com/search", json={"api_key":TAVILY_KEY,"query":q,"max_results":3,"include_answer":True}, timeout=8)
        if r.status_code==200:
            j=r.json(); return (j.get("answer","")+" | "+" | ".join([x.get("content","")[:250] for x in j.get("results",[])]))[:800]
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

# V50.3 ROOT FIX: Upstash SET galat tha, ab /pipeline se sahi hoga
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
            # FIX: /pipeline use karo, direct / pe SET kaam nahi karta
            payload=[["SET",key,json.dumps(val)]]
            r=requests.post(f"{UPSTASH_URL}/pipeline", headers=h, json=payload, timeout=5)
            if r.status_code==200: return True
            # Backup: /set/key/value
            try:
                enc=urllib.parse.quote(json.dumps(val))
                r2=requests.post(f"{UPSTASH_URL}/set/{key}/{enc}", headers=h, timeout=5)
                if r2.status_code==200: return True
            except: pass
            return True
    except Exception as e: print(f"upstash err {e}")
    return None

def load_persist():
    global MEMORY,PROFILES,OWNER_PREF,OWNER_LEARN_TEXT
    MEMORY=upstash("get","RAKAN_MEM_V50") or upstash("get","RAKAN_MEM_V42") or {}
    PROFILES=upstash("get","RAKAN_PROFILES_V50") or upstash("get","RAKAN_PROFILES_V42") or {}
    # V50.3: Agar purana pref me voice_on=False hai to bhi default True mat todo, user ka command hi chalega
    p=upstash("get","RAKAN_PREF")
    if isinstance(p, dict) and p:
        OWNER_PREF=p
    else:
        OWNER_PREF={"voice_gender":"female","voice_on":True,"full_log":True}
    if "full_log" not in OWNER_PREF: OWNER_PREF["full_log"]=True
    if "voice_on" not in OWNER_PREF: OWNER_PREF["voice_on"]=True
    learn=upstash("get","RAKAN_LEARN_V50") or upstash("get","RAKAN_LEARN_V42") or {}
    if isinstance(learn, dict): OWNER_LEARN_TEXT = learn.get("text","")[:2000]
    elif isinstance(learn, str): OWNER_LEARN_TEXT = learn[:2000]
load_persist()

def save_persist():
    upstash("set","RAKAN_MEM_V50",MEMORY); upstash("set","RAKAN_PROFILES_V50",PROFILES); upstash("set","RAKAN_PREF",OWNER_PREF)

def save_learn(new_text):
    global OWNER_LEARN_TEXT
    OWNER_LEARN_TEXT = (OWNER_LEARN_TEXT + f" | {new_text}")[-2000:]
    ok=upstash("set","RAKAN_LEARN_V50",{"text":OWNER_LEARN_TEXT,"updated":get_ist_str()})
    save_persist()
    return ok

def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<600
def mark_bad(k): BAD_KEYS[k]=time.time()

def clean(t, user_query=""):
    if not t: return ""
    # V50.3 FIX: System leak + Msg leak + Hist leak sab band
    t=re.sub(r'(?i)\b(laude|lauda|bosdike|bhosdike|maderchod|madarchod|behenchod|bhenchod|gand|lund|chutiya|randi)\b', '', t)
    # Leak phrases jo video me aaye
    leak_list=["15 words","Complex","Max 15","max_tokens","system_instruction","Hist ","Msg ","User:","Bot:","Kya specific kaam hai aaj?","specific kaam hai aaj","aap ki marzi hai","aap hi decide karein"]
    for lp in leak_list:
        t=t.replace(lp,"")
    t=t.replace("🙏","")
    if "laude" in t.lower() or "Arre bhai" in t: return ""
    bad_phrases=["I'm sorry, but I can't help","I cannot help with that","As an AI language model","I am Groq","I am Gemini","Here's a quick recap","Sure, I'm speaking in English","How can I help you right now?","kaunse topic pe help","Apne faisle ko dhyaan se","apne andar ki awaaz","zindagi ki coding","Bhai, coding se zyada","Main OpenAI ke GPT-4","Main **Rakan** hoon, ek AI assistant","shayad koi vyakti","Dubara ye word mat bolna","Settings > History","History me jaa kar check","shant raho aur respect se baat karo","code likh sakta hoon","research kar sakta","images generate","image bana sakta","Namaste, main aapki madad karne ke liye taiyaar hoon","8-digit random alphanumeric","Brute force se 100 saal","Beast King ka izzat rakho","Chup raho. Malik ka aage"]
    for bp in bad_phrases:
        if bp.lower() in t.lower():
            if "password" in user_query.lower() or "sanskrit" in user_query.lower() or "seo" in user_query.lower():
                if "Namaste" in bp: return ""
                continue
            else: return ""
    # Agar user ka hi text echo ho raha hai to kaat do
    if user_query and len(user_query)>4 and user_query.lower()[:20] in t.lower():
        t=t.replace(user_query,"").replace(user_query.lower(),"")
    if any(w in user_query.lower() for w in ["full detail","detail do","ai ke bare","what you do","kya kaam","explain","paragraph"]):
        limit=120
    elif any(w in user_query.lower() for w in ["sanskrit","seo","phone","password","news","mathematically","best","compare"]):
        limit=80
    else:
        limit=35
    if len(t.split()) > limit:
        t = " ".join(t.split()[:limit])
    t=re.sub(r"\s+"," ",t).strip()
    # Khali ya sirf punctuation bacha to ""
    if len(t)<3: return ""
    return t[:1100]

def ask_groq(sys,user, max_t=200):
    if not GROQ_KEYS: return None
    MODELS=["openai/gpt-oss-20b","meta-llama/llama-4-scout-17b-16e-instruct","qwen/qwen3.8-27b"]
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":sys},{"role":"user","content":user}],"temperature":0.7,"max_tokens":max_t}, timeout=18)
                if r.status_code==200:
                    txt=r.json()["choices"][0]["message"]["content"]
                    if txt and "sorry" not in txt.lower()[:80] and "OpenAI" not in txt: return txt
                if r.status_code in [401,429]: mark_bad(k); break
            except: continue
    return None

def ask_gemini(sys,user, max_t=200):
    if not GEMINI_KEYS: return None
    MODELS=["gemini-2.5-flash","gemini-2.0-flash","gemini-3-flash-preview","gemini-3.5-flash"]
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        for m in MODELS:
            try:
                genai.configure(api_key=k)
                model=genai.GenerativeModel(m, system_instruction=sys)
                res=model.generate_content(user, generation_config={"temperature":0.7,"max_output_tokens":max_t})
                if res and getattr(res,'text',None):
                    t=res.text
                    if "sorry" not in t.lower()[:80] and "OpenAI" not in t: return t
            except Exception as e:
                if "429" in str(e) or "401" in str(e) or "400" in str(e): mark_bad(k); break
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

def pick_not_same(options, uid):
    # V50.3 BEHTAR: Pichhla jawab repeat nahi hoga
    last=LAST_BOT_MSG.get(uid,"")
    for o in options:
        if o!=last: return o
    return random.choice(options)

def brain(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid):
    global MEMORY,PROFILES,LAST_BOT_MSG,LAST_USER_MSG,OWNER_LEARN_TEXT
    uid=str(uid)
    if uid not in MEMORY: MEMORY[uid]={"hist":""}
    if uid not in PROFILES: PROFILES[uid]={"total":0,"city":"","username":username,"lang":lang}
    PROFILES[uid]["total"]+=1; PROFILES[uid]["username"]=username; PROFILES[uid]["lang"]=lang
    LAST_USER_MSG[uid]=text; low=text.lower().strip()
    low_norm = low.replace("achs","acha").replace("ach","acha").replace("thik hi hai sab","thik hai").replace("thik hi hai","thik hai")
    abuse_words=["maderchod","madarchod","bhenchod","behenchod","bosdike","bhosdike","gand","lund","chutiya","laude","lauda","randi","mderchod"]
    contains_abuse = any(w in low for w in abuse_words)

    if is_owner:
        if "meri city" in low or "my city" in low:
            try:
                city_extract = text.split("city")[-1].split("is")[-1].strip(" :ka")[:20].title()
                if len(city_extract)>2: PROFILES[uid]["city"]=city_extract; save_persist()
            except: pass
        if "mujhe" in low and "pasand" in low and len(low)<80: save_learn(text)

    if low.startswith("/start"):
        v_on="ON 🔊" if OWNER_PREF.get("voice_on") else "OFF 🔇"
        if is_owner:
            ans=f"Assalamu Alaikum Malik 👑 {MALIK_NAME}\nWelcome Shadow King\nTera Rakan V50.3 Beast hazir hai 🔥\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}\nVoice:{OWNER_PREF.get('voice_gender')} {v_on}\nLearn:{len(OWNER_LEARN_TEXT)} chars\nImage: ON 🎨\n{get_ist_str()}"
        else:
            ans=f"Assalamu Alaikum {uname} 👋\nMain Rakan hu, Malik {MALIK_NAME} ne banaya hai 🔒"
        LAST_BOT_MSG[uid]=ans; return ans, False, True

    if low in ["/status","/mode","/orv","/dashboard"] and is_owner:
        orv=upstash("get","RAKAN_LIKES") or {"like":0,"dislike":0}
        ans=f"📊 V50.3 Beast {get_ist_str()}\n👍 {orv.get('like',0)} 👎 {orv.get('dislike',0)}\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}\nUsers:{len(PROFILES)}\nCity:{PROFILES[uid].get('city','-')}\nLearn:{OWNER_LEARN_TEXT[-300:] or 'Empty'}\nVoice:{OWNER_PREF.get('voice_gender')} {'ON' if OWNER_PREF.get('voice_on') else 'OFF'}\nFullLog:{'ON' if OWNER_PREF.get('full_log') else 'OFF'}"
        return ans, False, False

    if low in ["/full off","full log off","full off"] and is_owner:
        OWNER_PREF["full_log"]=False; save_persist(); ans="Full Log OFF kar diya Malik 🔇"; LAST_BOT_MSG[uid]=ans; return ans, False, False
    if low in ["/full on","full log on","full on"] and is_owner:
        OWNER_PREF["full_log"]=True; save_persist(); ans="Full Log ON kar diya Malik 🔊"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if any(x in low for x in ["kisne banaya","who made you","who created you","tumhe kisne banaya","tumko kisne banaya"]):
        ans="mujhe mere the shadow king md saif ahmad ne banaya"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    # V50.3 BEHTAR: better / behtar ka asli jawab - video wala
    if any(x in low for x in ["better kaise","behtar kaise","or better","or behtar","better banau","behtar banau","advance kaise","or advance"]):
        ans="Malik mujhe behtar banane ke liye 3 kaam karo 🔥\n1. `yaad rakh` bol ke nayi cheez sikhao\n2. `voice on` + `female voice` se voice lock karo\n3. Jo galat lage uspe 👎 dabao, main sudhar jaunga\nBolo kya behtar karna hai? 👑" if is_owner else f"{uname} aap batao kya behtar karu? 🔒"
        LAST_BOT_MSG[uid]=ans; return ans, False, False

    # V50.3: matlab / thik hai sab - video wala
    if low in ["matlab","matlb","mtlb"]:
        ans=pick_not_same(["Matlab Malik, bolo kya karna hai? Main samjha nahi pura 🔥","Matlab kya Malik? Thoda detail me bolo 👑","Haan Malik, matlab samjha do, kya chahiye? 🔥"], uid) if is_owner else f"Matlab {uname}? Thoda detail me bolo 🔒"
        LAST_BOT_MSG[uid]=ans; return ans, False, False

    if low_norm in ["thik hai","thik hai sab","sab thik hai","thik hi hai","sab badhiya","sab thik"]:
        ans=pick_not_same(["MashaAllah Malik, sab thik hai to mast hai 👑 Bolo agla kaam kya hai? 🔥","Good Malik, sab thik hai to aage badhte hai, bolo kya karna hai? 🔥","Alhamdulillah Malik, aap bolo kya hukam hai? 👑"], uid) if is_owner else f"Good {uname}, bolo kya chahiye? 🔒"
        LAST_BOT_MSG[uid]=ans; return ans, False, False

    if any(x in low for x in ["image bana","photo bana","pic bana","tasveer bana","generate image","draw"]):
        prompt = text
        for k in ["image bana","photo bana","pic bana","tasveer bana","image","photo"]:
            if k in low:
                try: prompt = low.split(k)[-1].strip(" de do ka ki ko :")
                except: pass
        if len(prompt)<3: prompt="shadow king monarch"
        tg_send_photo(cid, prompt); ans=f"Lo Malik bana di image 🎨 {prompt[:60]} 🔥"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if "voice on" in low or "orb on" in low:
        OWNER_PREF["voice_on"]=True; save_persist(); ans="Voice Mode ON kar diya Malik 🔊 Ab voice bhejo to voice me jawab, typing pe typing 👑"; LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "voice off" in low or "orb off" in low or "voice band" in low:
        OWNER_PREF["voice_on"]=False; save_persist(); ans="Voice Mode OFF kar diya Malik 🔇 Ab sirf text"; LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "female voice" in low or "ladki voice" in low:
        OWNER_PREF["voice_gender"]="female"; save_persist(); ans="Female voice lock kar di Malik 👩🔊"; LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "male voice" in low or "ladka voice" in low:
        OWNER_PREF["voice_gender"]="male"; save_persist(); ans="Male voice lock kar di Malik 👨🔊"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if contains_abuse:
        ans="Maaf karo Malik, gusse me bhi aap King ho 👑 Bolo kya hukam hai? Hazir hu 🔥" if is_owner else f"Maaf karna {uname}, bolo kya kaam hai? 🔒"
        LAST_BOT_MSG[uid]=ans; return ans, False, False

    if low in ["how r u","how are you","how ru","how are u","how r u?","how are you?","hru"]:
        ans=pick_not_same(["Alhamdulillah Malik, aapke hukam se ekdum mast hu 👑 Bolo kya kaam hai? 🔥","Main mast hu Shadow King, aap batao kya haal hai? 😎","Ek dum fit hu Malik, aapka intezaar kar raha tha 🔥","Aapke saath hu to hamesha badhiya hu Malik 👑","Sab badhiya Malik, bolo kya hukam hai? 🔥"], uid) if is_owner else f"Main thik hu {uname}, aap batao? 😊🔒"
        LAST_BOT_MSG[uid]=ans; return ans, False, False

    if low_norm in ["or batao","or bataoo","or bata","batao","bata","tumari","tumhara","tumhari","tumhe"]:
        ans=pick_not_same(["Jee Malik bolo kya kaam hai? 🔥","Haan Malik bolo 👑","Hazir hu Malik, hukam karo 🔥","Samajh gaya Malik, bolo kya karna hai? 👑"], uid) if is_owner else f"Jee {uname} bolo? 🔒"
        LAST_BOT_MSG[uid]=ans; return ans, False, False

    if low_norm in ["acha","accha","ok","okay","thik","theek","samajh gaya","samaj gaya","hmm","achha","good","achs"]:
        ans=pick_not_same(["Jee Malik samajh gaya, agla hukam? 🔥","Haan Malik bolo kya karna hai? 👑","Samajh gaya Monarch, bolo? 🔥","Ok Malik, hazir hu 👑"], uid) if is_owner else f"Jee {uname} samajh gaya 🔒"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if low in ["hi","hii","hiii","hello","helo","hy","hey","salam","salaam"]:
        ans=pick_not_same(["Jee Malik bolo kya hukam hai? 😎🔥","Hazir hu Shadow King 👑","Assalamu Alaikum Malik, bolo? 🔥","Malik bolo, Shadow King hazir hai 😎"], uid) if is_owner else f"Jee {uname} bolo kya haal hai? 😊🔒"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if any(x in low for x in ["walaikum assalam","walekum assalam","walaikum salam","wa alaikum"]):
        ans="Jee Malik Walaikum Assalam 👑 Bolo kya hukam hai? 🔥" if is_owner else f"Walaikum Assalam {uname} 🔒"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if any(x in low for x in ["what you do","kya kaam kar sakte","kya kr skte ho","kya kar sakte ho","what can you do","kya kya kar","kya kya kr","kar skte ho mere liye","kya kya kar skte"]):
        ans="Malik main Beast King hu 🔥\n1. Live Search (News, SEO, Sanskrit)\n2. Weather\n3. Image Gen 🎨\n4. Yaad Rakhna\n5. Voice Note (Male/Female) 🔊\n6. Full Detail Explain\nBolo kya hukam hai? 👑" if is_owner else f"{uname} main Search, Weather, Image Gen, Detail explain sab kar sakta hu 🔒"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if "kya kr rhe ho" in low or "kya kar rahe ho" in low:
        ans="Kuch nahi Malik, aapka intezaar kar raha hu, hukam karo kya kaam karna hai? 🔥👑" if is_owner else f"Bas aapka intezaar {uname} 🔒"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if is_owner and any(x in low for x in ["yaad rakh","yaad rakhna","seekh le","yaad karle","learn kar"]):
        for trigger in ["yaad rakh","yaad rakhna","seekh le","yaad karle","learn kar"]:
            if trigger in low:
                try:
                    idx=low.index(trigger)+len(trigger); learn_text=text[idx:].strip(" :,-")
                    if len(learn_text) > 3:
                        save_learn(learn_text); ans=f"Yaad rakh liya Malik ✅ {learn_text[:80]} 🔥 Ab /start pe Learn:{len(OWNER_LEARN_TEXT)} dikhega"; LAST_BOT_MSG[uid]=ans; return ans, False, False
                except: pass
        ans="Bolo Malik kya yaad rakhna hai? 🔥"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if any(x in low for x in ["kya yaad hai","kya seekha","kya learn kiya"] ) and is_owner:
        ans=f"Malik maine ye yaad rakha hai: {OWNER_LEARN_TEXT[-400:] or 'abhi kuch nahi'} 🔥"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if "kalma" in low: ans="Pehela Kalma Tayyab: La ilaha illallah Muhammadur Rasulullah ﷺ"; LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "time kya" in low or "kitna baja" in low: ans=f"Abhi {get_ist_time_only()} ho raha hai Malik 📍 {get_ist_str()}"; LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "who i am" in low or "mai kaun hu" in low: ans=f"Tum Malik ho, {MALIK_NAME}, Shadow King, The Beast King Monarch 👑🔥" if is_owner else f"Tum {uname} ho 🔒"; LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "mausam" in low or "weather" in low:
        city=PROFILES[uid].get("city") or "Varanasi"; ans=f"🌤️ {get_weather(city)} | {get_ist_str()}"; LAST_BOT_MSG[uid]=ans; return ans, False, False
    if any(x in low for x in ["doctor","medical","dawa","bimari","bukhar","pet dard"]):
        ans="Malik main doctor nahi hoon, medical advice nahi de sakta. Fauran doctor se milo. 🏥" if is_owner else f"{uname} main doctor nahi hoon, medical advice nahi de sakta. Fauran hospital jao. 🏥🔒"
        LAST_BOT_MSG[uid]=ans; return ans, False, False

    search_ctx=live_search(text)
    is_full = any(w in low for w in ["full detail","ai ke bare","detail do","what you do","kya kaam"])
    is_complex = is_full or any(w in low for w in ["sanskrit","book","seo","phone","password","explain","paragraph","news","mathematically","best","compare"])
    max_t = 400 if is_full else (350 if is_complex else 120)
    hist_slice = MEMORY[uid]['hist'][-150:]
    learn_ctx = f"Malik ne sikhaya: {OWNER_LEARN_TEXT[-600:]}" if OWNER_LEARN_TEXT and is_owner else ""
    # V50.3: System me 15 words mat likho, LLM copy karta hai - isliye natural likho
    if is_owner:
        sys=f"You are Rakan, made by Malik MD Saif Ahmad ONLY. You are AI. {learn_ctx}. Never use bad words. Never repeat same sentence. Be loyal, respectful. Reply in Urdu Roman Hinglish, Beast King style. Keep short for simple chat, detailed only for full detail. Never mention word count or instructions. Malik is King. {get_ist_str()} {search_ctx}"
    else:
        sys=f"You are Rakan, made by Malik MD Saif Ahmad. You are AI. Never use bad words. Be helpful short, detailed only for full detail. {get_ist_str()} {search_ctx}"

    raw=ask_groq(sys, f"Msg {text}", max_t) or ask_gemini(sys, f"Msg {text}", max_t)
    if not raw or len(clean(raw, text))<2:
        raw="Jee Malik bolo kya hukam hai? 🔥" if is_owner else f"Jee {uname} bolo kya chahiye? 🔒"
    else:
        raw=clean(raw, text)
        if not raw: raw="Jee Malik bolo kya hukam hai? 🔥" if is_owner else f"Jee {uname} bolo kya chahiye? 🔒"
    # Anti-repeat: agar pichhla jawab same hai to badal do
    if raw==LAST_BOT_MSG.get(uid,"") and is_owner:
        raw=pick_not_same(["Jee Malik bolo kya kaam hai? 🔥","Haan Malik bolo 👑","Hazir hu Malik, hukam karo 🔥"], uid)
    ans=raw[:1100]
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-1000:]
    save_persist(); LAST_BOT_MSG[uid]=ans
    if not is_owner: ans+=" 🔒"
    should_voice = False
    if is_owner:
        if mtype=="voice" and OWNER_PREF.get("voice_on",True): should_voice=True
        if "voice me" in low or "voice main" in low: should_voice=True
    return ans, should_voice, False

def make_btns(is_owner=False, is_start=False):
    if is_owner:
        if is_start: return [[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]]
        else: return None
    else: return [[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]]

@app.route("/", methods=["GET"])
def home(): return f"Rakan V50.3 G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {get_ist_str()}",200
@app.route("/debug", methods=["GET"])
def debug(): return f"V50.3 OWNER {OWNER_ID} G {len(GROQ_KEYS)} GM {len(GEMINI_KEYS)} LEARN {len(OWNER_LEARN_TEXT)} VOICE {OWNER_PREF.get('voice_gender')} {OWNER_PREF.get('voice_on')} UPSTASH {bool(UPSTASH_URL)}",200

@app.route("/webhook", methods=["POST","GET"])
@app.route("/api/index", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return debug() if "debug" in request.path.lower() else home()
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
                full_data=f"📩 FULL DATA V50.3\n👤 {uname}\nUID:{uid} CID:{cid}\nUser: {last_user_text}\nBot: {last_bot_text}\n⏰ {get_ist_str()}\nAction: {cdata}"
                tg_send(OWNER_ID, full_data)
                tg_send(cid, "Shukriya ❤️" if cdata=="LIKE" else "Batao kya galat laga?")
                return "ok",200
            return "ok",200
        msg=data.get("message",{}) or {}; chat_id=msg.get("chat",{}).get("id"); user_id=str(msg.get("from",{}).get("id",0)); uname=msg.get("from",{}).get("first_name","user"); username=msg.get("from",{}).get("username","") or ""; lang=msg.get("from",{}).get("language_code","") or "en"; mtype="text"
        text=msg.get("text","") or msg.get("caption","") or ""; mid=msg.get("message_id")
        if "voice" in msg or "audio" in msg:
            mtype="voice"
            fid=msg.get("voice",{}).get("file_id") or msg.get("audio",{}).get("file_id")
            text=transcribe_voice(fid) or "[Voice]"
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID); is_queen=(username.lower()==QUEEN_USERNAME.lower())
        if is_owner: uname=MALIK_NAME
        ans, voice_flag, is_start = brain(text,user_id,is_owner,is_queen,uname,username,lang,mtype,chat_id)
        if ans=="Archived": return "ok",200
        btns=make_btns(is_owner, is_start)
        tg_send(chat_id, ans, mid, btns)
        if voice_flag and is_owner:
            tg_send_voice(chat_id, ans, OWNER_PREF.get("voice_gender","female"))
        if not is_owner and OWNER_PREF.get("full_log",True):
            if len(text.strip()) < 5 and text.lower().strip() in ["hi","hii","ok","good","hey","hello","seo kh","seo","accha"]: pass
            else:
                now=time.time()
                if now - LAST_FULL_LOG.get(user_id,0) > 180:
                    try:
                        full_log=f"📩 FULL MSG V50.3\n👤 {uname} (@{username})\nUID:{user_id} CID:{chat_id}\nUser: {text[:500]}\nBot: {ans[:500]}\n⏰ {get_ist_str()}"
                        tg_send(OWNER_ID, full_log)
                        LAST_FULL_LOG[user_id]=now
                    except: pass
        return "ok",200
    except Exception as e:
        print(f"ERR {e} {traceback.format_exc()}"); return "ok",200
