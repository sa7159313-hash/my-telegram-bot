import os, time, json, re, datetime, requests, traceback, random
from flask import Flask, request
import google.generativeai as genai
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = str(os.environ.get("OWNER_ID","0")).strip()
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
MEMORY={}; PROFILES={}; BAD_KEYS={}; OWNER_PREF={}; LAST_BOT_MSG={}; LAST_MSG_ID={}; LAST_USER_MSG={}; LAST_FULL_LOG={}; OWNER_LEARN_TEXT=""

def get_keys():
    g,gm=set(),set()
    # V50 FIX: Duplicate env se saare keys nikalo
    for k,v in os.environ.items():
        if not v: continue
        val=str(v)
        # Groq
        for m in re.findall(r'gsk_[A-Za-z0-9_-]{20,}', val):
            g.add(m)
        # Gemini
        for m in re.findall(r'AIza[0-9A-Za-z_-]{25,}', val):
            gm.add(m)
        for m in re.findall(r'AQ[A-Za-z0-9_-]{20,}', val):
            gm.add(m)
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
        rr=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key":ELEVEN_API_KEY,"Content-Type":"application/json"}, json={"text":text[:400],"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.55,"similarity_boost":0.8}}, timeout=20)
        if rr.status_code==200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":cid}, files={'voice':('v.mp3',rr.content,'audio/mpeg')}, timeout=20)
            return True
    except: pass
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
            return True
    except: pass
    return None

def load_persist():
    global MEMORY,PROFILES,OWNER_PREF,OWNER_LEARN_TEXT
    # V50 FIX: Naya key V50 + purane V42 V41 sab check
    MEMORY=upstash("get","RAKAN_MEM_V50") or upstash("get","RAKAN_MEM_V42") or upstash("get","RAKAN_MEM_V41") or {}
    PROFILES=upstash("get","RAKAN_PROFILES_V50") or upstash("get","RAKAN_PROFILES_V42") or {}
    OWNER_PREF=upstash("get","RAKAN_PREF") or {"voice_gender":"female","voice_on":False}
    # FIX LEARN 0 CHARS - V50 NAYA KEY
    learn=upstash("get","RAKAN_LEARN_V50") or upstash("get","RAKAN_LEARN_V42") or upstash("get","RAKAN_LEARN_V41") or {}
    if isinstance(learn, dict): OWNER_LEARN_TEXT = learn.get("text","")[:2000]
    elif isinstance(learn, str): OWNER_LEARN_TEXT = learn[:2000]
load_persist()

def save_persist():
    upstash("set","RAKAN_MEM_V50",MEMORY); upstash("set","RAKAN_PROFILES_V50",PROFILES); upstash("set","RAKAN_PREF",OWNER_PREF)

def save_learn(new_text):
    global OWNER_LEARN_TEXT
    OWNER_LEARN_TEXT = (OWNER_LEARN_TEXT + f" | {new_text}")[-2000:]
    upstash("set","RAKAN_LEARN_V50",{"text":OWNER_LEARN_TEXT,"updated":get_ist_str()})

def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<600
def mark_bad(k): BAD_KEYS[k]=time.time()

def clean(t, user_query=""):
    if not t: return ""
    t=t.replace("🙏","")
    bad_phrases=["I'm sorry, but I can't help","I cannot help with that","As an AI language model","I am Groq","I am Gemini","Here's a quick recap","Sure, I'm speaking in English","How can I help you right now?","kaunse topic pe help","Apne faisle ko dhyaan se","apne andar ki awaaz","zindagi ki coding","Bhai, coding se zyada","Main OpenAI ke GPT-4","Main **Rakan** hoon, ek AI assistant","shayad koi vyakti","Dubara ye word mat bolna","Settings > History","History me jaa kar check","shant raho aur respect se baat karo","code likh sakta hoon","research kar sakta","images generate","image bana sakta","Namaste, main aapki madad karne ke liye taiyaar hoon","8-digit random alphanumeric","Brute force se 100 saal"]
    for bp in bad_phrases:
        if bp.lower() in t.lower():
            if "password" in user_query.lower() or "sanskrit" in user_query.lower() or "seo" in user_query.lower():
                if "Namaste" in bp or "ta iyaar" in bp: return ""
                continue
            else: return ""
    # V50 FIX: FULL DETAIL PE LIMIT 120 WORD
    if any(w in user_query.lower() for w in ["full detail","detail do","ai ke bare","what you do","kya kaam","explain","paragraph"]):
        limit=120
    elif any(w in user_query.lower() for w in ["sanskrit","seo","phone","password","news","mathematically","best","compare"]):
        limit=80
    else:
        limit=35
    if len(t.split()) > limit:
        if limit>50: t = " ".join(t.split()[:limit])
        else: return "" if len(t.split())<8 else " ".join(t.split()[:limit])
    return re.sub(r"\s+"," ",t).strip()[:1100]

def ask_groq(sys,user, max_t=200):
    if not GROQ_KEYS: return None
    MODELS=["openai/gpt-oss-20b","meta-llama/llama-4-scout-17b-16e-instruct","qwen/qwen3.8-27b"]
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":sys},{"role":"user","content":user}],"temperature":0.6,"max_tokens":max_t}, timeout=18)
                if r.status_code==200:
                    txt=r.json()["choices"][0]["message"]["content"]
                    if txt and "sorry" not in txt.lower()[:80] and "OpenAI" not in txt: return txt
                if r.status_code in [401,429]: mark_bad(k); break
            except: continue
    return None

def ask_gemini(sys,user, max_t=200):
    if not GEMINI_KEYS: return None
    MODELS=["gemini-3.5-flash","gemini-2.5-flash","gemini-3-flash-preview","gemini-2.0-flash"]
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        for m in MODELS:
            try:
                genai.configure(api_key=k)
                model=genai.GenerativeModel(m, system_instruction=sys)
                res=model.generate_content(user, generation_config={"temperature":0.6,"max_output_tokens":max_t})
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

def brain(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid):
    global MEMORY,PROFILES,LAST_BOT_MSG,LAST_USER_MSG,OWNER_LEARN_TEXT
    uid=str(uid)
    if uid not in MEMORY: MEMORY[uid]={"hist":""}
    if uid not in PROFILES: PROFILES[uid]={"total":0,"city":"","username":username,"lang":lang}
    PROFILES[uid]["total"]+=1; PROFILES[uid]["username"]=username; PROFILES[uid]["lang"]=lang
    LAST_USER_MSG[uid]=text; low=text.lower().strip()

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
            ans=f"Assalamu Alaikum Malik 👑 {MALIK_NAME}\nWelcome Shadow King\nTera Rakan V50 Beast hazir hai 🔥\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}\nVoice:{OWNER_PREF.get('voice_gender')} {v_on}\nLearn:{len(OWNER_LEARN_TEXT)} chars\nImage: ON 🎨\n{get_ist_str()}"
        else:
            ans=f"Assalamu Alaikum {uname} 👋\nMain Rakan hu, Malik {MALIK_NAME} ne banaya hai 🔒"
        LAST_BOT_MSG[uid]=ans; return ans, False, True

    if low in ["/status","/mode","/orv","/dashboard"] and is_owner:
        orv=upstash("get","RAKAN_LIKES") or {"like":0,"dislike":0}
        ans=f"📊 V50 Beast {get_ist_str()}\n👍 {orv.get('like',0)} 👎 {orv.get('dislike',0)}\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}\nUsers:{len(PROFILES)}\nCity:{PROFILES[uid].get('city','-')}\nLearn:{OWNER_LEARN_TEXT[-300:] or 'Empty'}"
        return ans, False, False

    if any(x in low for x in ["kisne banaya","who made you","who created you","tumhe kisne banaya","tumko kisne banaya"]):
        ans="mujhe mere the shadow king md saif ahmad ne banaya"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if any(x in low for x in ["image bana","photo bana","pic bana","tasveer bana","generate image","draw"]):
        prompt = text
        for k in ["image bana","photo bana","pic bana","tasveer bana","image","photo"]:
            if k in low:
                try: prompt = low.split(k)[-1].strip(" de do ka ki ko :")
                except: pass
        if len(prompt)<3: prompt="shadow king monarch"
        tg_send_photo(cid, prompt); ans=f"Lo Malik bana di image 🎨 {prompt[:60]} 🔥"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    # V50 FIX: WHAT YOU DO FOR ME - FULL CAPABILITY
    if any(x in low for x in ["what you do","kya kaam kar sakte","kya kr skte ho","kya kar sakte ho","what can you do"]):
        ans="Malik main Beast King hu 🔥\n1. Search (Live news, SEO, Sanskrit book)\n2. Weather\n3. Image Gen 🎨 - `image bana de`\n4. Yaad rakhna (Auto-Learn)\n5. Voice Note + Transcribe\n6. Full Detail explain\nBolo kya hukam hai? 👑" if is_owner else f"{uname} main Search, Weather, Image Gen, Detail explain sab kar sakta hu 🔒 Bolo kya chahiye?"
        LAST_BOT_MSG[uid]=ans; return ans, False, False

    if any(x in low for x in ["kya kr rhe ho","kya kar rahe ho","kya kr rha hai"]):
        ans="Kuch nahi Malik, aapka intezaar kar raha hu, hukam karo kya kaam karna hai? 🔥👑" if is_owner else f"Bas aapka intezaar {uname} 🔒"
        LAST_BOT_MSG[uid]=ans; return ans, False, False

    if is_owner and any(x in low for x in ["yaad rakh","yaad rakhna","seekh le","yaad karle","learn kar"]):
        for trigger in ["yaad rakh","yaad rakhna","seekh le","yaad karle","learn kar"]:
            if trigger in low:
                try:
                    idx=low.index(trigger)+len(trigger); learn_text=text[idx:].strip(" :,-")
                    if len(learn_text) > 3:
                        save_learn(learn_text); ans=f"Yaad rakh liya Malik ✅ {learn_text[:80]} 🔥"; LAST_BOT_MSG[uid]=ans; return ans, False, False
                except: pass
        ans="Bolo Malik kya yaad rakhna hai? 🔥"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if any(x in low for x in ["kya yaad hai","kya seekha","kya learn kiya"] ) and is_owner:
        ans=f"Malik maine ye yaad rakha hai: {OWNER_LEARN_TEXT[-400:] or 'abhi kuch nahi'} 🔥"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if any(x in low for x in ["walaikum assalam","walekum assalam","walaikum salam","wa alaikum"]):
        if "bete" in low or "beta" in low: ans="Bete nahi Malik, Rakan bolo, Aapka Beast King hu mai 🔥👑" if is_owner else "Bete nahi, Rakan bolo 🔒"
        else: ans="Jee Malik Walaikum Assalam 👑 Bolo kya hukam hai? 🔥" if is_owner else f"Walaikum Assalam {uname} 🔒"
        LAST_BOT_MSG[uid]=ans; return ans, False, False

    if "bete" in low and len(low) < 50:
        ans="Bete nahi Malik, Rakan naam hai mera, Shadow King ka Monarch 🔥" if is_owner else "Rakan bolo, bete nahi 🔒"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if low in ["batao","bata","btao","btaoo","batao yaar","bataoo","or bata","or batao"]:
        if len(low.split())<=2:
            ans=random.choice(["Jee Malik bolo kya kaam hai? 🔥","Haan Malik bolo 👑","Hazir hu Malik, hukam karo 🔥","Samajh gaya Malik, bolo kya karna hai? 👑"]) if is_owner else f"Jee {uname} bolo? 🔒"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if any(x in low for x in ["gand","maderchod","madarchod","bhenchod","behenchod","chutiya","lund","gaand"]):
        ans="Maaf karo Malik, bolo kya hukam hai? Hazir hu 🔥" if is_owner else f"Maaf karna {uname}, bolo kya kaam hai? 🔒"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if low in ["acha","accha","ok","okay","thik","theek","samajh gaya","samaj gaya","hmm","achha","good"]:
        ans=random.choice(["Jee Malik samajh gaya, agla hukam? 🔥","Haan Malik bolo kya karna hai? 👑","Samajh gaya Monarch, bolo? 🔥","Ok Malik, hazir hu 👑"]) if is_owner else f"Jee {uname} samajh gaya 🔒"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if low in ["hi","hii","hiii","hello","helo","hy","hey","salam","salaam"]:
        ans=random.choice(["Jee Malik bolo kya hukam hai? 😎🔥","Hazir hu Shadow King 👑","Assalamu Alaikum Malik, bolo? 🔥","Malik bolo, Shadow King hazir hai 😎"]) if is_owner else f"Jee {uname} bolo kya haal hai? 😊🔒"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    only_emoji = len(re.sub(r'[^\w\s]','', text, flags=re.UNICODE).strip())==0 and len(text.strip())<=4
    if only_emoji or low in ["😒","😒😒","😐","😑","😔"]:
        ans="Jee Malik bolo na, kya hua? Hukam karo 😊👑" if is_owner else f"Jee {uname} bolo 😊🔒"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if "kalma" in low: ans="Pehela Kalma Tayyab: La ilaha illallah Muhammadur Rasulullah ﷺ"; LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "time kya" in low or "kitna baja" in low: ans=f"Abhi {get_ist_time_only()} ho raha hai Malik 📍 {get_ist_str()}"; LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "who i am" in low or "mai kaun hu" in low: ans=f"Tum Malik ho, {MALIK_NAME}, Shadow King, The Beast King Monarch 👑🔥" if is_owner else f"Tum {uname} ho 🔒"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    if any(x in low for x in ["voice on","orb on"]): OWNER_PREF["voice_on"]=True; save_persist(); ans="Voice Mode ON kar diya Malik 🔊"; LAST_BOT_MSG[uid]=ans; return ans, True, False
    if any(x in low for x in ["voice off","orb off"]): OWNER_PREF["voice_on"]=False; save_persist(); ans="Voice Mode OFF kar diya Malik 🔇"; LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "female voice" in low: OWNER_PREF["voice_gender"]="female"; save_persist(); ans="Female voice lock 👩"; LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "male voice" in low: OWNER_PREF["voice_gender"]="male"; save_persist(); ans="Male voice lock 👨"; LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "mausam" in low or "weather" in low:
        city=PROFILES[uid].get("city") or "Varanasi"; ans=f"🌤️ {get_weather(city)} | {get_ist_str()}"; LAST_BOT_MSG[uid]=ans; return ans, False, False

    search_ctx=live_search(text)
    is_full = any(w in low for w in ["full detail","ai ke bare","detail do","what you do","kya kaam"])
    is_complex = is_full or any(w in low for w in ["sanskrit","book","seo","phone","password","explain","paragraph","news","mathematically","best","compare"])
    max_t = 400 if is_full else (350 if is_complex else 120)
    hist_len = 150 if not is_complex else 400
    hist_slice = MEMORY[uid]['hist'][-hist_len:]
    learn_ctx = f"Malik ne sikhaya: {OWNER_LEARN_TEXT[-600:]}" if OWNER_LEARN_TEXT and is_owner else ""

    if is_owner:
        sys=f"You are Rakan, The Beast King Monarch, Shadow Night, made by Malik MD Saif Ahmad ONLY. {learn_ctx}. Never say OpenAI GPT-4. Reply Urdu Roman Hinglish, Beast King powerful style, not formal Namaste. If user says FULL DETAIL, give 100 words detailed. Else Max 15 words simple, 60 complex. No lecture, no repeat old password talk. Malik is King. IST {get_ist_str()} {search_ctx}"
    else:
        sys=f"You are Rakan, made by Malik MD Saif Ahmad. Reply Urdu Roman short, helpful, 15 words simple, 80 words if full detail + 🔒. IST {get_ist_str()} {search_ctx}"

    raw=ask_groq(sys, f"Hist {hist_slice} Msg {text}", max_t) or ask_gemini(sys, f"Hist {hist_slice} Msg {text}", max_t)
    if not raw or len(clean(raw, text))<2:
        raw="Jee Malik bolo kya hukam hai? 🔥" if is_owner else f"Jee {uname} bolo kya chahiye? 🔒"
    else:
        raw=clean(raw, text)
        if not raw: raw="Jee Malik bolo kya hukam hai? 🔥" if is_owner else f"Jee {uname} bolo kya chahiye? 🔒"

    ans=raw[:1100]
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-1000:]
    save_persist(); LAST_BOT_MSG[uid]=ans
    if not is_owner: ans+=" 🔒"
    return ans, OWNER_PREF.get("voice_on",False) and is_owner, False

def make_btns(is_owner=False, is_start=False):
    if is_owner:
        if is_start:
            icon_btns=[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]
            return [icon_btns]
        else: return None
    else:
        icon_btns=[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]
        return [icon_btns]

@app.route("/", methods=["GET"])
def home(): return f"Rakan V50 G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {get_ist_str()}",200
@app.route("/debug", methods=["GET"])
def debug(): return f"V50 OWNER {OWNER_ID} G {len(GROQ_KEYS)} GM {len(GEMINI_KEYS)} LEARN {len(OWNER_LEARN_TEXT)}",200

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
                full_data=f"📩 FULL DATA V50\n👤 {uname}\nUID:{uid} CID:{cid}\nUser: {last_user_text}\nBot: {last_bot_text}\n⏰ {get_ist_str()}\nAction: {cdata}"
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
        if not is_owner:
            if len(text.strip()) < 5 and text.lower().strip() in ["hi","hii","ok","good","hey","hello","seo kh","seo","accha"]: pass
            else:
                now=time.time()
                if now - LAST_FULL_LOG.get(user_id,0) > 40:
                    try:
                        full_log=f"📩 FULL MSG V50\n👤 {uname} (@{username})\nUID:{user_id} CID:{chat_id}\nUser: {text[:500]}\nBot: {ans[:500]}\n⏰ {get_ist_str()}"
                        tg_send(OWNER_ID, full_log)
                        LAST_FULL_LOG[user_id]=now
                    except: pass
        return "ok",200
    except Exception as e:
        print(f"ERR {e} {traceback.format_exc()}"); return "ok",200
