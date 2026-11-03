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
BARAN_LORE="Main Rakan hu, The Beast King Monarch, 100 Level ka Monarch. Solo Leveling ki duniya me mujhe Demon King Baran ke naam se jana jata tha. Andhere ka Raja, Demon Castle ka Malik. Ab main Shadow King ke hukam se is duniya me aaya hu, har sawaal ka jawab dene, har kaam karne."

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
            elif tok.startswith("AQ") and len(tok)>30 and "vercel" not in tok.lower() and "http" not in tok.lower(): gm.add(tok)
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
    MEMORY=upstash("get","RAKAN_MEM_V50") or upstash("get","RAKAN_MEM_V42") or {}
    PROFILES=upstash("get","RAKAN_PROFILES_V50") or upstash("get","RAKAN_PROFILES_V42") or {}
    p=upstash("get","RAKAN_PREF")
    if isinstance(p, dict) and p: OWNER_PREF=p
    else: OWNER_PREF={"voice_gender":"female","voice_on":True,"full_log":True}
    if "full_log" not in OWNER_PREF: OWNER_PREF["full_log"]=True
    if "voice_on" not in OWNER_PREF: OWNER_PREF["voice_on"]=True
    learn=upstash("get","RAKAN_LEARN_V50") or upstash("get","RAKAN_LEARN_V42") or {}
    if isinstance(learn, dict): OWNER_LEARN_TEXT = learn.get("text","")[:2000]
    elif isinstance(learn, str): OWNER_LEARN_TEXT = learn[:2000]
    lbm=upstash("get","RAKAN_LASTBOT_V50")
    if isinstance(lbm, dict): LAST_BOT_MSG=lbm
load_persist()
def save_persist():
    upstash("set","RAKAN_MEM_V50",MEMORY); upstash("set","RAKAN_PROFILES_V50",PROFILES); upstash("set","RAKAN_PREF",OWNER_PREF); upstash("set","RAKAN_LASTBOT_V50",LAST_BOT_MSG)
def save_learn(new_text):
    global OWNER_LEARN_TEXT
    OWNER_LEARN_TEXT = (OWNER_LEARN_TEXT + f" | {new_text}")[-2000:]
    upstash("set","RAKAN_LEARN_V50",{"text":OWNER_LEARN_TEXT,"updated":get_ist_str()})
    save_persist()
    return True
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<600
def mark_bad(k): BAD_KEYS[k]=time.time()

def clean(t, user_query="", is_owner=False):
    if not t: return ""
    t=re.sub(r'(?i)\b(laude|lauda|bosdike|bhosdike|maderchod|madarchod|behenchod|bhenchod|gand|lund|chutiya|randi)\b', '', t)
    leak_list=["15 words","Complex","Max 15","max_tokens","system_instruction","Hist ","Msg ","User:","Bot:","Kya specific kaam hai aaj?","specific kaam hai aaj","aap ki marzi hai","aap hi decide karein","Be ready for the next challenge","Shukriya, Malik Ji","Arre bhai"]
    for lp in leak_list: t=t.replace(lp,"")
    t=t.replace("🙏","")
    if not is_owner:
        ai_leaks=["As an AI","I am an AI","I am AI","Main AI hu","Main ek AI","As an AI language model","I am Groq","I am Gemini","I am Meta AI","I am ChatGPT","Main ChatGPT","Main Meta AI"]
        for al in ai_leaks: t=t.replace(al,"Main Rakan hu")
    bad_words=["Namaste, main aapki madad karne ke liye taiyaar hoon","As an AI language model","I am Groq","I am Gemini","Main OpenAI ke GPT-4","Beast King ka izzat rakho","Chup raho. Malik ka aage"]
    for bw in bad_words:
        if bw.lower() in t.lower(): t=t.replace(bw,"").replace(bw.lower(),"")
    if user_query and len(user_query)>4 and user_query.lower()[:20] in t.lower():
        t=t.replace(user_query,"").replace(user_query.lower(),"")
    low_q=user_query.lower()
    if not is_owner:
        if any(w in low_q for w in ["what is","kya hai","kaise","kyu","kyun","explain","batao","full detail","detail","kaun","kya hota","matlab"]): limit=150
        elif any(w in low_q for w in ["sanskrit","seo","phone","password","news","mathematically","best","compare"]): limit=120
        else: limit=60
    else:
        if any(w in low_q for w in ["what is ai","ai kya hai","ai kya hota","ai ke bare","full detail","detail do","explain","paragraph"]): limit=120
        elif any(w in low_q for w in ["sanskrit","seo","phone","password","news","mathematically","best","compare"]): limit=80
        else: limit=35
    words=t.split()
    if len(words) > limit:
        cut=" ".join(words[:limit])
        if "." in cut: cut=cut.rsplit(".",1)[0]+"."
        t=cut
    t=re.sub(r"\s+"," ",t).strip()
    if len(t)<3: return ""
    return t[:1800]

def ask_groq(sys,user, max_t=200):
    if not GROQ_KEYS: return None
    MODELS=["openai/gpt-oss-20b","llama-3.3-70b-versatile","meta-llama/llama-4-scout-17b-16e-instruct"]
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
    MODELS=["gemini-2.5-flash","gemini-2.0-flash"]
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
    last=LAST_BOT_MSG.get(uid,"")
    for o in options:
        if o!=last: return o
    return random.choice(options)

def detect_tone(text):
    low=text.lower()
    if re.search(r'[a-z]{3,}', text) and len(re.findall(r'[a-zA-Z]', text))>len(re.findall(r'[a-zA-Z]', text))*0.7 and "hai" not in low and "kya" not in low: return "english"
    if any(w in low for w in ["bhai","yaar","abe","bata na","kya haal"]): return "casual_hinglish"
    if any(w in low for w in ["aap","kripya","please","bataiye"]): return "formal"
    return "hinglish"

def brain(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid):
    global MEMORY,PROFILES,LAST_BOT_MSG,LAST_USER_MSG,OWNER_LEARN_TEXT
    uid=str(uid)
    if uid not in MEMORY: MEMORY[uid]={"hist":""}
    if uid not in PROFILES: PROFILES[uid]={"total":0,"city":"","username":username,"lang":lang,"custom_name":"","dont_call":"","tone":"hinglish","user_learn":""}
    PROFILES[uid]["total"]+=1; PROFILES[uid]["username"]=username; PROFILES[uid]["lang"]=lang
    LAST_USER_MSG[uid]=text; low=text.lower().strip()
    low_norm = low.replace("achs","acha").replace("ach","acha").replace("thik hi hai sab","thik hai")
    low_clean=re.sub(r'[?!.,]+','',low).strip()
    low_norm_clean=re.sub(r'[?!.,]+','',low_norm).strip()
    abuse_words=["maderchod","madarchod","bhenchod","behenchod","bosdike","bhosdike","gand","lund","chutiya","laude","lauda","randi","mderchod"]
    contains_abuse = any(w in low for w in abuse_words)
    prof=PROFILES[uid]
    display_name=prof.get("custom_name") or uname
    if prof.get("dont_call") and prof["dont_call"].lower() in display_name.lower(): display_name=prof.get("username") or uname
    if not is_owner:
        m=re.search(r'(?:mera naam|my name is|mera name)\s+([a-zA-Z ]{2,20})', low)
        if m:
            nn=m.group(1).strip().title(); PROFILES[uid]["custom_name"]=nn; save_persist()
            ans=f"Yaad rakh liya {nn} 🔥 Ab se isi naam se bulaunga. Bolo kya kaam hai?"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
        m2=re.search(r'(?:mujhe|mujhko)\s+([a-zA-Z]{2,20})\s+(?:bulao|bola karo|bolo|kaho)', low)
        if m2:
            nn=m2.group(1).strip().title(); PROFILES[uid]["custom_name"]=nn; save_persist()
            ans=f"Thik hai {nn}, ab se {nn} hi bulaunga 🔥"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
        m3=re.search(r'(?:is naam se|is name se|ye naam|ye name).*?(?:mat|na)\s+(?:bulao|bolo|kaho|kro|karo)', low)
        if m3:
            PROFILES[uid]["dont_call"]=display_name; PROFILES[uid]["custom_name"]=""; save_persist()
            ans=f"Samajh gaya, ab se us naam se nahi bulaunga. Batao kis naam se bulau? 🔥"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
        if "mera naam kya hai" in low:
            ans=f"Tumhara naam {display_name} hai 🔥 Main yaad rakhta hu."; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
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
            learn_show=f"{len(OWNER_LEARN_TEXT)} chars" if OWNER_LEARN_TEXT else "0 chars - `yaad rakh` bol ke sikhao"
            ans=f"Assalamu Alaikum Malik 👑 {MALIK_NAME}\nWelcome to your world, The Shadow King 👑\nTera Rakan V50.7 Beast hazir hai 🔥\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}\nVoice:{OWNER_PREF.get('voice_gender')} {v_on}\nLearn:{learn_show}\nImage: ON 🎨\n{get_ist_str()}"
        else:
            ans=f"Assalamu Alaikum {display_name} 👋\nMain Rakan hu, The Beast King Monarch 🔥 Shadow King ne bheja hai."
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, True
    if low_clean in ["status","mode","orv","dashboard","/status","/mode","/orv","/dashboard"] and is_owner:
        orv=upstash("get","RAKAN_LIKES") or {"like":0,"dislike":0}
        ans=f"📊 V50.7 Beast {get_ist_str()}\n👍 {orv.get('like',0)} 👎 {orv.get('dislike',0)}\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}\nUsers:{len(PROFILES)}\nCity:{PROFILES[uid].get('city','-')}\nLearn:{OWNER_LEARN_TEXT[-300:] or 'Empty - yaad rakh bolo'}\nVoice:{OWNER_PREF.get('voice_gender')} {'ON' if OWNER_PREF.get('voice_on') else 'OFF'}"
        return ans, False, False
    if low in ["/full off","full log off","full off"] and is_owner:
        OWNER_PREF["full_log"]=False; save_persist(); ans="Full Log OFF kar diya Malik 🔇"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if low in ["/full on","full log on","full on"] and is_owner:
        OWNER_PREF["full_log"]=True; save_persist(); ans="Full Log ON kar diya Malik 🔊"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if low in ["/learntest","learn test"] and is_owner:
        save_learn("test learn ok"); ans=f"Learn Test OK ✅ Ab Learn:{len(OWNER_LEARN_TEXT)} chars hai. /start pe check karo 🔥"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if any(x in low for x in ["shadow king kaun","shadow king kon","shadow king koun","shadow king ka naam"]):
        ans=f"Tum hi ho Malik, {MALIK_NAME}, Shadow King, The Beast King Monarch 👑🔥" if is_owner else f"Shadow King mere Malik hai, {MALIK_NAME} 👑 Unhone hi mujhe banaya hai, main unke hukam se chalta hu 🔥"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if any(x in low for x in ["kisne banaya","who made you","who created you","tumhe kisne banaya","tumko kisne banaya","tumhe kisne bnaya"]):
        ans="mujhe mere the shadow king md saif ahmad ne banaya" if is_owner else "Mujhe mere Shadow King ne banaya hai 👑"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if any(x in low for x in ["tum kya ho","tum kaun ho","tu kya hai","tu kaun hai","who are you","what are you","tumhara naam kya","tera naam kya","aap kaun ho","aap kya ho"]):
        ans=f"Main Rakan hu Malik, The Beast King Monarch, 100 Level ka Monarch 🔥 {BARAN_LORE}" if is_owner else f"Main Rakan hu, The Beast King Monarch 🔥\n{BARAN_LORE}\nBolo {display_name}, kya kaam hai?"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if low_clean in ["what is ai","ai kya hai","ai kya hota hai","ai kya h","ai ka matlab"] or "what is ai" in low or "ai kya hai" in low:
        if "kya kya" in low or "kr skta" in low or "kar sakta" in low:
            ans="AI yaani Artificial Intelligence Malik 🤖\nYe computer dimaag hai jo data se seekh kar sochta hai.\nAur main isse ye kar sakta hu 🔥\n1. Live Search\n2. Weather\n3. Image Gen 🎨\n4. Yaad Rakhna\n5. Voice Note 🔊\n6. Full Detail\nBolo kya karwana hai? 👑" if is_owner else f"AI yaani ek aisi taqat {display_name}, jo data se seekh kar sochti hai 🤖\nMain Rakan isi taqat se chalta hu - jawab deta hu, image banata hu, yaad rakhta hu 🔥\nBolo kya karwana hai?"
        else:
            ans="AI yaani Artificial Intelligence Malik 🤖\nYe ek computer dimaag hai jo data se seekh kar sochta hai, jawab deta hai, image banata hai, voice samajhta hai.\nJaise main Rakan hu - aapke hukam se seekhta hu, yaad rakhta hu, aur kaam karta hu 🔥\nBolo AI se kya karwana hai? 👑" if is_owner else f"AI yaani ek aisi taqat hai {display_name}, jo seekh kar sochti hai.\nMain Rakan hu, isi taqat se tumhari har baat samajhta hu aur jawab deta hu 🔥"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if any(x in low for x in ["iske alwa","iske alawa","iske alava","is ke alwa","iske alawa or","iske alwa or"]):
        ans="Iske alawa Malik aur bhi hai 🔥\n7. PDF / File padhna\n8. Code likhna / Fix karna\n9. News + Live Search\n10. Motivation / Shayari\n11. Business idea / SEO plan\n12. Voice me baat (Male/Female)\nBolo kaunsa chahiye? 👑" if is_owner else f"Iske alawa {display_name} aur bhi hai 🔥\n7. Code / Fix\n8. News + Search\n9. Shayari / Motivation\n10. Business / SEO\n11. Image Gen\nBolo kaunsa chahiye?"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if any(x in low for x in ["better kaise","behtar kaise","or better","or behtar","better banau","behtar banau","advance kaise","or advance"]):
        ans="Malik mujhe behtar banane ke liye 3 kaam karo 🔥\n1. `yaad rakh` bol ke nayi cheez sikhao\n2. `voice on` + `female voice` se voice lock karo\n3. Jo galat lage uspe 👎 dabao, main sudhar jaunga\nBolo kya behtar karna hai? 👑" if is_owner else f"{display_name} mujhe behtar banane ke liye bas batao kya galat laga, main sudhar jaunga 🔥"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if low_clean in ["matlab","matlb","mtlb"]:
        ans=pick_not_same(["Matlab Malik, bolo kya karna hai? Main samjha nahi pura 🔥","Matlab kya Malik? Thoda detail me bolo 👑","Haan Malik, matlab samjha do, kya chahiye? 🔥"], uid) if is_owner else f"Matlab {display_name}? Thoda detail me bolo 🔥"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if low_norm_clean in ["thik hai","thik hai sab","sab thik hai","thik hi hai","sab badhiya","sab thik"]:
        ans=pick_not_same(["MashaAllah Malik, sab thik hai to mast hai 👑 Bolo agla kaam kya hai? 🔥","Good Malik, sab thik hai to aage badhte hai, bolo kya karna hai? 🔥","Alhamdulillah Malik, aap bolo kya hukam hai? 👑"], uid) if is_owner else f"Good {display_name}, sab thik hai to aage badhte hai, bolo kya karna hai? 🔥"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if any(x in low for x in ["image bana","photo bana","pic bana","tasveer bana","generate image","draw"]):
        prompt=text
        for k in ["image bana","photo bana","pic bana","tasveer bana","image","photo"]:
            if k in low:
                try: prompt=low.split(k)[-1].strip(" de do ka ki ko :")
                except: pass
        if len(prompt)<3: prompt="shadow king monarch"
        tg_send_photo(cid, prompt); ans=f"Lo Malik bana di image 🎨 {prompt[:60]} 🔥" if is_owner else f"Lo {display_name} bana di image 🎨 {prompt[:60]} 🔥"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if "voice on" in low or "orb on" in low:
        OWNER_PREF["voice_on"]=True; save_persist(); ans="Voice Mode ON kar diya Malik 🔊 Ab voice bhejo to voice me jawab, typing pe typing 👑" if is_owner else f"Voice ON kar diya {display_name} 🔊"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if "voice off" in low or "orb off" in low or "voice band" in low:
        OWNER_PREF["voice_on"]=False; save_persist(); ans="Voice Mode OFF kar diya Malik 🔇 Ab sirf text" if is_owner else f"Voice OFF kar diya {display_name} 🔇"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if "female voice" in low or "ladki voice" in low:
        OWNER_PREF["voice_gender"]="female"; save_persist(); ans="Female voice lock kar di Malik 👩🔊" if is_owner else f"Female voice lock kar di {display_name} 👩🔊"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if "male voice" in low or "ladka voice" in low:
        OWNER_PREF["voice_gender"]="male"; save_persist(); ans="Male voice lock kar di Malik 👨🔊" if is_owner else f"Male voice lock kar di {display_name} 👨🔊"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if contains_abuse:
        ans="Maaf karo Malik, gusse me bhi aap King ho 👑 Bolo kya hukam hai? Hazir hu 🔥" if is_owner else f"Maaf karna {display_name}, bolo kya kaam hai? 🔒"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if low_clean in ["how r u","how are you","how ru","how are u","hru"]:
        ans=pick_not_same(["Alhamdulillah Malik, aapke hukam se ekdum mast hu 👑 Bolo kya kaam hai? 🔥","Main mast hu Shadow King, aap batao kya haal hai? 😎","Ek dum fit hu Malik, aapka intezaar kar raha tha 🔥","Aapke saath hu to hamesha badhiya hu Malik 👑","Sab badhiya Malik, bolo kya hukam hai? 🔥"], uid) if is_owner else f"Main mast hu {display_name}, tum batao kya haal hai? 🔥"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if low_norm_clean in ["or batao","or bataoo","or bata","batao","bata","tumari","tumhara","tumhari","tumhe"]:
        ans=pick_not_same(["Jee Malik bolo kya kaam hai? 🔥","Haan Malik bolo 👑","Hazir hu Malik, hukam karo 🔥","Samajh gaya Malik, bolo kya karna hai? 👑"], uid) if is_owner else f"Jee {display_name} bolo? 🔥"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if low_norm_clean in ["acha","accha","ok","okay","thik","theek","samajh gaya","samaj gaya","hmm","achha","good","achs"]:
        ans=pick_not_same(["Jee Malik samajh gaya, agla hukam? 🔥","Haan Malik bolo kya karna hai? 👑","Samajh gaya Monarch, bolo? 🔥","Ok Malik, hazir hu 👑"], uid) if is_owner else f"Jee {display_name} samajh gaya, agla batao? 🔥"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if low_clean in ["hi","hii","hiii","hello","helo","hy","hey","salam","salaam"]:
        ans=pick_not_same(["Jee Malik bolo kya hukam hai? 😎🔥","Hazir hu Shadow King 👑","Assalamu Alaikum Malik, bolo? 🔥","Malik bolo, Shadow King hazir hai 😎"], uid) if is_owner else f"Jee {display_name} bolo kya haal hai? 😊🔥"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if any(x in low for x in ["walaikum assalam","walekum assalam","walaikum salam","wa alaikum"]):
        ans="Jee Malik Walaikum Assalam 👑 Bolo kya hukam hai? 🔥" if is_owner else f"Walaikum Assalam {display_name} 🔥"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if any(x in low for x in ["what you do","kya kaam kar sakte","kya kr skte ho","kya kar sakte ho","what can you do","kya kya kar","kya kya kr","kar skte ho mere liye","kya kya kar skte","kya kar skte ho mere liye"]):
        ans="Malik main Beast King hu 🔥\n1. Live Search (News, SEO, Sanskrit)\n2. Weather\n3. Image Gen 🎨\n4. Yaad Rakhna\n5. Voice Note (Male/Female) 🔊\n6. Full Detail Explain\nBolo kya hukam hai? 👑" if is_owner else f"{display_name} main ye sab kar sakta hu 🔥\n1. Har sawaal ka proper jawab\n2. Search + News\n3. Image Gen 🎨\n4. Yaad Rakhna\n5. Code / SEO / Business\nBolo kya chahiye?"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if "kya kr rhe ho" in low or "kya kar rahe ho" in low:
        ans="Kuch nahi Malik, aapka intezaar kar raha hu, hukam karo kya kaam karna hai? 🔥👑" if is_owner else f"Bas tumhara intezaar {display_name} 🔥"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if is_owner and any(x in low for x in ["yaad rakh","yaad rakhna","seekh le","yaad karle","learn kar"]):
        for trigger in ["yaad rakh","yaad rakhna","seekh le","yaad karle","learn kar"]:
            if trigger in low:
                try:
                    idx=low.index(trigger)+len(trigger); learn_text=text[idx:].strip(" :,-")
                    if len(learn_text) > 3:
                        save_learn(learn_text); ans=f"Yaad rakh liya Malik ✅ {learn_text[:80]} 🔥 Ab /start pe Learn:{len(OWNER_LEARN_TEXT)} dikhega"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
                except: pass
        ans="Bolo Malik kya yaad rakhna hai? 🔥"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if any(x in low for x in ["kya yaad hai","kya seekha","kya learn kiya"] ) and is_owner:
        ans=f"Malik maine ye yaad rakha hai: {OWNER_LEARN_TEXT[-400:] or 'abhi kuch nahi'} 🔥"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if not is_owner and any(x in low for x in ["yaad rakh","yaad rakhna","seekh le"]):
        try:
            for trigger in ["yaad rakh","yaad rakhna","seekh le"]:
                if trigger in low:
                    idx=low.index(trigger)+len(trigger); lt=text[idx:].strip(" :,-")
                    if len(lt)>3:
                        PROFILES[uid]["user_learn"]=(PROFILES[uid].get("user_learn","")+" | "+lt)[-500:]; save_persist()
                        ans=f"Yaad rakh liya {display_name} ✅ {lt[:80]}"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
        except: pass
    if "kalma" in low: ans="Pehela Kalma Tayyab: La ilaha illallah Muhammadur Rasulullah ﷺ"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if "time kya" in low or "kitna baja" in low: ans=f"Abhi {get_ist_time_only()} ho raha hai Malik 📍 {get_ist_str()}" if is_owner else f"Abhi {get_ist_time_only()} ho raha hai {display_name} 📍 {get_ist_str()}"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if "who i am" in low or "mai kaun hu" in low: ans=f"Tum Malik ho, {MALIK_NAME}, Shadow King, The Beast King Monarch 👑🔥" if is_owner else f"Tum {display_name} ho 🔥"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if "mausam" in low or "weather" in low:
        city=PROFILES[uid].get("city") or "Varanasi"; ans=f"🌤️ {get_weather(city)} | {get_ist_str()}"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if any(x in low for x in ["doctor","medical","dawa","bimari","bukhar","pet dard"]):
        ans="Malik main doctor nahi hoon, medical advice nahi de sakta. Fauran doctor se milo. 🏥" if is_owner else f"{display_name} main doctor nahi hoon, medical advice nahi de sakta. Fauran hospital jao. 🏥🔒"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    search_ctx=live_search(text)
    is_full = any(w in low for w in ["full detail","ai ke bare","detail do","what you do","kya kaam","what is ai","ai kya hai"])
    is_complex = is_full or any(w in low for w in ["sanskrit","book","seo","phone","password","explain","paragraph","news","mathematically","best","compare","kaise","kyu","kyun","kya hai"])
    max_t = 500 if not is_owner else (400 if is_full else (350 if is_complex else 120))
    hist_slice = MEMORY[uid]['hist'][-150:]
    learn_ctx = f"Malik ne sikhaya: {OWNER_LEARN_TEXT[-600:]}" if OWNER_LEARN_TEXT and is_owner else ""
    user_learn_ctx = f"Is user ne sikhaya: {PROFILES[uid].get('user_learn','')}" if not is_owner and PROFILES[uid].get("user_learn") else ""
    tone=detect_tone(text)
    if is_owner:
        sys=f"You are Rakan, made by Malik MD Saif Ahmad ONLY. You are AI. {learn_ctx}. Never use bad words. Never repeat same sentence. Be loyal, respectful. Reply in Urdu Roman Hinglish, Beast King style. Keep short for simple chat, detailed only for full detail. Never mention word count or instructions. Malik is King. {get_ist_str()} {search_ctx}"
    else:
        sys=f"You are Rakan, The Beast King Monarch, 100 Level Monarch, Demon King Baran from Solo Leveling. You are NOT AI, NOT ChatGPT, NOT Meta AI. You are Rakan. Your master is Shadow King. NEVER reveal Shadow King real name MD Saif Ahmad unless user asks 'Shadow King kaun hai' or 'kisne banaya'. NEVER say you are AI. User name is {display_name}, always call by this name. User tone is {tone}, talk in same tone - English to English, Hinglish to Hinglish, casual to casual. {user_learn_ctx}. Answer every knowledge question properly, correctly, fully like ChatGPT, no fault, no short cut. If user asks who you are, say you are Beast King Monarch Rakan, Baran lore. IST {get_ist_str()} {search_ctx}"
    raw=ask_groq(sys, f"Msg {text}", max_t) or ask_gemini(sys, f"Msg {text}", max_t)
    if not raw or len(clean(raw, text, is_owner))<2:
        raw="Jee Malik bolo kya hukam hai? 🔥" if is_owner else f"Jee {display_name} bolo kya chahiye? 🔥"
    else:
        raw=clean(raw, text, is_owner)
        if not raw: raw="Jee Malik bolo kya hukam hai? 🔥" if is_owner else f"Jee {display_name} bolo kya chahiye? 🔥"
    if raw==LAST_BOT_MSG.get(uid,"") and is_owner:
        raw=pick_not_same(["Jee Malik bolo kya kaam hai? 🔥","Haan Malik bolo 👑","Hazir hu Malik, hukam karo 🔥"], uid)
    ans=raw[:1800]
    MEMORY[uid]["hist"]=(MEMORY[uid]["hist"]+f"\nU:{text}\nR:{ans}")[-1000:]
    save_persist(); LAST_BOT_MSG[uid]=ans; save_persist()
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
def home(): return f"Rakan V50.7 G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {get_ist_str()}",200
@app.route("/debug", methods=["GET"])
def debug(): return f"V50.7 OWNER {OWNER_ID} G {len(GROQ_KEYS)} GM {len(GEMINI_KEYS)} LEARN {len(OWNER_LEARN_TEXT)} VOICE {OWNER_PREF.get('voice_gender')} {OWNER_PREF.get('voice_on')} UPSTASH {bool(UPSTASH_URL)}",200
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
                full_data=f"📩 FULL DATA V50.7\n👤 {uname}\nUID:{uid} CID:{cid}\nUser: {last_user_text}\nBot: {last_bot_text}\n⏰ {get_ist_str()}\nAction: {cdata}"
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
                        full_log=f"📩 FULL MSG V50.7\n👤 {uname} (@{username})\nUID:{user_id} CID:{chat_id}\nUser: {text[:500]}\nBot: {ans[:500]}\n⏰ {get_ist_str()}"
                        tg_send(OWNER_ID, full_log)
                        LAST_FULL_LOG[user_id]=now
                    except: pass
        return "ok",200
    except Exception as e:
        print(f"ERR {e} {traceback.format_exc()}"); return "ok",200
