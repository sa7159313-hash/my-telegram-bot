import os, time, json, re, datetime, requests, traceback, random, urllib.parse, base64
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
MEMORY={}; PROFILES={}; BAD_KEYS={}; OWNER_PREF={}; LAST_BOT_MSG={}; LAST_MSG_ID={}; LAST_USER_MSG={}; LAST_FULL_LOG={}; OWNER_LEARN_TEXT=""; LAST_TOPIC={}; LAST_SALAM={}
def safe(s, n=100):
    try:
        if not s: return ""
        s=str(s); return s[-n:] if len(s)>n else s
    except: return ""
# V70 - TYPO NORMALIZE - skte, kr, bta sab samjhega
def normalize(low):
    low=low.lower()
    reps={"skte":"sakte","sktay":"sakte","krte":"karte","kr":"kar","bta":"bata","btau":"batao","bataoo":"batao","kyaa":"kya","acha":"acha","achaa":"acha","hukm":"hukam","hukum":"hukam","bnnna":"banna","bnna":"banna","banna":"banna","billionaire":"billionaire","bilionare":"billionaire","bilionare":"billionaire"}
    for k,v in reps.items():
        low=re.sub(r'\b'+k+r'\b', v, low)
    low=re.sub(r'\?+','',low); low=re.sub(r'\s+',' ',low).strip()
    return low
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
        if "Auto V41" in txt or ("Bot Live" in txt and "Clear Sky" in txt): return False
        for b in ["I'm sorry, but I can't help with that","I can't help with that","Maaf kijiye, isme main madad nahi kar sakta","Maaf karna, is vishay par baat nahi kar sakta","I'm sorry"]:
            txt=txt.replace(b,"Samajh gaya Malik, bolo kya karna hai?")
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
        for b in ["I'm sorry, but I can't help with that","I can't help with that","Maaf kijiye, isme main madad nahi kar sakta","I'm sorry"]:
            text=text.replace(b,"Samajh gaya Malik, bolo kya karna hai?")
        text=" ".join(text.split()[:35])
        if not text: text="Jee Malik bolo kya hukam hai?"
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
                if rr.status_code==200:
                    t=rr.json().get("text","").strip()
                    if t: return t
            except: continue
    except: pass
    return ""
def read_photo(file_id):
    try:
        if not GEMINI_KEYS: return None
        fp=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()["result"]["file_path"]
        img=requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=15).content
        prompt="Is photo me kya likha hai? Hinglish Roman me short me batao, 80 word se zyada nahi. Agar bill hai to dukan ka naam, total, date batao."
        for k in GEMINI_KEYS:
            try:
                genai.configure(api_key=k)
                model=genai.GenerativeModel("gemini-2.5-flash")
                try:
                    from google.generativeai import types as gtypes
                    part=gtypes.Part.from_data(data=img, mime_type="image/jpeg")
                    res=model.generate_content([prompt, part], generation_config={"temperature":0.3,"max_output_tokens":300})
                    if res and getattr(res,'text',None) and len(res.text.strip())>5: return res.text
                except: pass
                try:
                    res2=model.generate_content([prompt, {"mime_type":"image/jpeg","data":img}], generation_config={"temperature":0.3,"max_output_tokens":300})
                    if res2 and getattr(res2,'text',None) and len(res2.text.strip())>5: return res2.text
                except: pass
            except: continue
    except Exception as e:
        print(f"PHOTO ERR {e}")
    return None
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
    global MEMORY,PROFILES,OWNER_PREF,OWNER_LEARN_TEXT,LAST_BOT_MSG,LAST_TOPIC
    try:
        MEMORY=upstash("get","RAKAN_MEM_V70") or upstash("get","RAKAN_MEM_V69") or {}
        PROFILES=upstash("get","RAKAN_PROFILES_V70") or upstash("get","RAKAN_PROFILES_V69") or {}
        p=upstash("get","RAKAN_PREF")
        if isinstance(p, dict) and p: OWNER_PREF=p
        else: OWNER_PREF={"voice_gender":"female","voice_on":True,"full_log":True}
        learn=upstash("get","RAKAN_LEARN_V62") or {}
        if isinstance(learn, dict): OWNER_LEARN_TEXT = learn.get("text","")[:2000]
        elif isinstance(learn, str): OWNER_LEARN_TEXT = learn[:2000]
        lbm=upstash("get","RAKAN_LASTBOT_V62") or {}
        if isinstance(lbm, dict): LAST_BOT_MSG=lbm
        lt=upstash("get","RAKAN_TOPIC_V66") or {}
        if isinstance(lt, dict): LAST_TOPIC=lt
    except: pass
load_persist()
def save_persist():
    try: upstash("set","RAKAN_MEM_V70",MEMORY); upstash("set","RAKAN_PROFILES_V70",PROFILES); upstash("set","RAKAN_PREF",OWNER_PREF); upstash("set","RAKAN_LASTBOT_V62",LAST_BOT_MSG); upstash("set","RAKAN_TOPIC_V66",LAST_TOPIC)
    except: pass
def save_learn(new_text):
    global OWNER_LEARN_TEXT
    OWNER_LEARN_TEXT = (OWNER_LEARN_TEXT + f" | {new_text}")[-2000:]
    upstash("set","RAKAN_LEARN_V62",{"text":OWNER_LEARN_TEXT,"updated":get_ist_str()}); save_persist(); return True
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<600
def mark_bad(k): BAD_KEYS[k]=time.time()
def clean(t, user_query="", is_owner=False):
    if not t: return "Jee Malik bolo kya hukam hai? 🔥"
    if "BOT_TOKEN" in t and len(t)>100: return "Token safe hai Malik, batao kya kaam hai? 🔥"
    if "def " in t and "print" in t and len(t)>50: return t[:2500]
    for b in ["I'm sorry, but I can't help with that","I'm sorry, but I can't help","I can't help with that","Maaf kijiye, isme main madad nahi kar sakta","Maaf kijiye isme main madad nahi kar sakta","Maaf karna, is vishay par baat nahi kar sakta","Maaf kijiye, is vishay par baat nahi kar sakta","I am sorry","I'm sorry","Sorry, I can't","As an AI language model","Sure! How can I help you next?","Sure, how can I help?","How can I help you next?","Hi! Main Rakan hoon","Hi! I am Rakan","I am an AI chatbot","As an AI","Sure!","How can I assist","Let me know if you need anything","Feel free to ask","Sure, kaise madad karun","I am here to help","How can I help you today","Hello!","Hi there","Happy coding"]:
        t=t.replace(b,"")
    t=t.replace("**","").replace("##","").replace("###","")
    t=re.sub(r'\|{1,}', ' ', t); t=re.sub(r'---+', '', t)
    for lp in ["yeh message Beast King style mein banaya gaya hai","banaya gaya hai sirf aapke liye","sirf aapke liye","Beast King style","cleaned","deeps, left","Bot Lives","Auto V4","Auto V41","Bot Live","billi-billi","billi billi","vastavik","Kshetra","Udaharan","Speech & Language","Kshamta, jisse"," - jaise ki pattern pehchan","15 words","Complex","Max 15","max_tokens","system_instruction","Hist ","Msg ","User:","Bot:","Be ready for the next challenge","Hey!","Hey,"]:
        t=t.replace(lp,"")
    t=re.sub(r'(?i)\b(laude|lauda|bosdike|bhosdike|maderchod|madarchod|behenchod|bhenchod|gand|lund|chutiya|randi)\b', '', t)
    t=t.replace("🙏","")
    uq=normalize(user_query or ""); uwords=len(uq.split())
    if "code" in uq: limit=400
    elif "billionaire" in uq: limit=200
    elif any(w in uq for w in ["detail me","detail mein","poora bata","pura bata","detail bata"]): limit=320
    elif uwords<=2: limit=15
    elif uwords<=6: limit=35
    elif uwords<=12: limit=80
    else: limit=120
    if not is_owner and limit>80 and "code" not in uq and "billionaire" not in uq: limit=80
    if "voice" in uq or uq.startswith("[voice]"): limit=min(limit,30)
    words=t.split()
    if len(words) > limit:
        cut=" ".join(words[:limit])
        # V70 FIX - 1. 2. pe mat kaato, sirf asli sentence pe kaato
        # Agar cut ke aakhri me "1." jaisa list number hai to mat kaato
        if re.search(r'\d\.$', cut.strip()):
            pass
        elif "." in cut:
            # Aakhri 2 sentence me se ek poora dhoondho, 1. ko ignore karo
            parts=re.split(r'(?<!\d)\. ', cut)
            if len(parts)>1:
                cut=". ".join(parts[:-1])+"."
        t=cut
    t=re.sub(r"\s+"," ",t).strip()
    if not t or len(t)<5: t="Samajh gaya Malik, bolo kya karna hai? 🔥"
    return t[:2500]
def ask_groq(sys,user, max_t=300):
    if not GROQ_KEYS: return None
    MODELS=["llama-3.3-70b-versatile","openai/gpt-oss-20b"]
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":sys},{"role":"user","content":user}],"temperature":0.6,"max_tokens":max_t}, timeout=10)
                if r.status_code==200:
                    txt=r.json()["choices"][0]["message"]["content"]
                    if txt and len(txt)>10:
                        if "I can't help" in txt or "I'm sorry" in txt: continue
                        return txt
                if r.status_code in [401,429,400]: mark_bad(k); break
            except: continue
    return None
def ask_gemini(sys,user, max_t=300, orig_len=999):
    if orig_len<40: return None
    if not GEMINI_KEYS: return None
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        try:
            genai.configure(api_key=k)
            model=genai.GenerativeModel("gemini-2.5-flash", system_instruction=sys)
            res=model.generate_content(user, generation_config={"temperature":0.6,"max_output_tokens":max_t})
            if res and getattr(res,'text',None):
                if "I can't help" in res.text or "I'm sorry" in res.text: continue
                return res.text
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
def brain(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid,photo_file_id=None):
    try: return brain_inner(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid,photo_file_id)
    except Exception as e:
        print(f"BRAIN ERR {e}"); return "Jee Malik bolo kya hukam hai? 🔥", False, False
def brain_inner(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid,photo_file_id=None):
    global MEMORY,PROFILES,LAST_BOT_MSG,LAST_USER_MSG,OWNER_LEARN_TEXT,LAST_TOPIC,LAST_SALAM
    if not text: text=""
    text=str(text); uid=str(uid)
    if uid not in MEMORY or not isinstance(MEMORY.get(uid), dict): MEMORY[uid]={"hist":""}
    if "hist" not in MEMORY[uid]: MEMORY[uid]["hist"]=""
    if uid not in PROFILES: PROFILES[uid]={"total":0,"city":"Varanasi","username":username,"lang":lang,"custom_name":"","dont_call":"","tone":"hinglish","user_learn":""}
    PROFILES[uid]["total"]=PROFILES[uid].get("total",0)+1; LAST_USER_MSG[uid]=text; low=text.lower().strip(); nlow=normalize(low)
    prof=PROFILES[uid]; display_name=prof.get("custom_name") or uname
    if photo_file_id:
        read=read_photo(photo_file_id)
        if read:
            ans=f"Is photo me ye likha hai Malik 👑\n{clean(read, text, is_owner)[:400]}"
            LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
        else:
            return "Photo mil gayi Malik, par saaf nahi dikh rahi. Photo ko paas se, seedha le ke dobara bhejo, main turant padh dunga 🔥", False, False
    if len(text)>500 and ("import os" in text or "BOT_TOKEN" in text or "def brain" in text or "api/index" in text):
        return "Code samajh gaya Malik, batao kya fix karna hai isme? 🔥", False, False
    if low.startswith("/start"):
        v_on="ON 🔊" if OWNER_PREF.get("voice_on") else "OFF 🔇"
        LAST_SALAM[uid]=time.time()
        if is_owner:
            learn_show=f"{len(OWNER_LEARN_TEXT)} chars" if OWNER_LEARN_TEXT else "0 chars - yaad rakh bol ke sikhao"
            ans=f"Assalamu Alaikum Malik 👑 {MALIK_NAME}\nWelcome to your world, The Shadow King 👑\nTera Rakan V70 Ultimate hazir hai 🔥\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}\nVoice:{OWNER_PREF.get('voice_gender')} {v_on}\nLearn:{learn_show}\nImage: ON 🎨 Photo: ON 📸 Voice: ON 🔊\n{get_ist_str()}"
        else:
            ans=f"Assalamu Alaikum {display_name} 👋\nMain Rakan hu, The Beast King Monarch 🔥"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, True
    # V70 - SALAM MAT BOLNA - Agar user ne mana kiya ya abhi Salam bol diya
    if "mt bolna salam" in nlow or "salam mat bolna" in nlow or "salam mat bol" in nlow or "already" in nlow and "salam" in nlow:
        LAST_SALAM[uid]=time.time()
        return "Samajh gaya Malik, ab Salam dobara nahi bolunga. Bolo kya karna hai? 🔥", False, False
    # V70 - BILLIONAIRE - Hard handler, LLM pe nahi chhodega, poora aayega
    if "billionaire" in nlow:
        return "Billionaire banne ke liye Malik, ye 4 kaam karo -\n1. AI Agency - Naraini ke dukano ke liye WhatsApp bot banao\n2. WhatsApp auto-reply - Business ka order AI se lo\n3. Chhota SaaS - Kirana hisab tool 299/month becho\n4. Faceless YouTube - AI video daily 1\nEk se shuru karo Malik, bolo kis se shuru karu?", False, False
    # V70 - HELP - Typo ke saath bhi chalega: skte, kar sakte, kya kar
    if ("kya kar" in nlow and "sakte" in nlow) or "kya kar sakte" in nlow or "kis chiz me help" in nlow or "kis cheez me help" in nlow or "kya kya kar sakte" in nlow:
        return "Main ye sab kar sakta hu Malik 👑\n1. Sawaal jawab - AI, Padhai, Code\n2. Photo padhna - Bill, Kagaz\n3. Voice me jawab dena\n4. Yaad rakhna - Yaad rakh bolo\n5. Image banana\n6. Dil ki baat sunna\nBolo kis me help chahiye?", False, False
    if mtype=="voice":
        if not text or text=="[Voice]" or len(text.strip())<2:
            return "Sunai nahi diya Malik, dobara bolo, thoda zor se 🔥", False, False
        if "alvida" in nlow or "nikal raha" in nlow or "jaa raha" in nlow or "chala ja" in nlow:
            return "Are Malik, Alvida mat bolo, main yahin hu tumhare saath 🔥 Bolo kya hua?", True, False
        if "gussa" in nlow:
            return "Samajh gaya Malik, gussa mat karo, main sudhar raha hu. Bolo kya galat laga? 🔥", True, False
        if "coffee" in nlow or "chai" in nlow:
            return "Haan Malik, black coffee bina sugar ke ready hai ☕ Bolo aur kya chahiye?", True, False
        if "back for mercy" in nlow or "mercy" in nlow:
            return "Haan Malik, Back For Mercy, main hazir hu 🔥 Bolo kya hukam hai?", True, False
        if "matlab kya" in nlow or "samajh nahi" in nlow:
            return "Matlab ye hai Malik, main tumhara Rakan hu, tumhara hukam manunga. Bolo kya samajhna hai?", True, False
    if any(w in nlow for w in ["pareshani","pareshaan","tension","dukhi","dukh","ghar wale pagal","gharwale pagal","akela","akelapan","ro raha","rona aa","depressed","sad hu","udaas","thak gaya","haar gaya","zindagi se"]):
        return "Sun raha hu Malik, sab theek ho jayega. Dil halka karo, batao kya hua? Main yahin hu tumhare saath 🔥 Tum akele nahi ho.", False, False
    if "or batao" in nlow or "or bataoo" in nlow or "aur batao" in nlow or "aur bataoo" in nlow:
        return "Aur ye hai Malik - Abhi main aur behtar ho gaya hu, photo bhi padh sakta hu, voice bhi sun sakta hu. Bolo kya karu? 🔥", False, False
    if "how are you" in nlow or "how's going" in nlow or "hows going" in nlow or "how is your day" in nlow:
        return "Alhamdulillah Malik, main ekdum mast hu, tum sunao kya haal hai? 🔥", False, False
    if "sululu" in nlow: return "Sululu ka koi khaas matlab nahi hai Malik, bas mazak wala word hai. Bolo kya kaam hai? 🔥", False, False
    if "alvida" in nlow or "nikal raha" in nlow: return "Are Malik, Alvida mat bolo, main yahin hu tumhare saath 🔥 Bolo kya hua?", False, False
    if "gussa" in nlow and mtype!="voice": return "Samajh gaya Malik, gussa mat karo, main sudhar raha hu. Bolo kya galat laga? 🔥", False, False
    if "voice mode" in nlow or "voice on" in nlow or "voice chalu" in nlow or "voice start" in nlow:
        OWNER_PREF["voice_on"]=True; save_persist()
        return "Voice Mode ON kar diya Malik 🔊 Ab voice me jawab dunga. Voice note bhejo.", True, False
    if "voice band" in nlow or "voice off" in nlow or "voice mode band" in nlow:
        OWNER_PREF["voice_on"]=False; save_persist()
        return "Voice Mode OFF kar diya Malik 🔇 Ab sirf text aayega.", False, False
    if "voice me" in nlow and ("bolo" in nlow or "batao" in nlow or "jawab" in nlow):
        return "Theek hai Malik, ab se voice me jawab dunga 🔊", True, False
    if "code" in nlow:
        if "jarvis" in nlow or "phone controller" in nlow or "phone control" in nlow or "ultron" in nlow:
            code="""# Jarvis jaisa Phone Controller - Step 1 Malik
import speech_recognition as sr
import pyttsx3
engine = pyttsx3.init()
def bolo(txt):
    print(txt); engine.say(txt); engine.runAndWait()
def suno():
    r = sr.Recognizer()
    with sr.Microphone() as s:
        print("Bolo Malik...")
        audio = r.listen(s)
        try: return r.recognize_google(audio, language="hi-IN")
        except: return ""
bolo("Haan Malik, Jarvis hazir hai")
cmd = suno()
print("Tumne bola:", cmd)"""
            return code, False, False
        else:
            return "Bolo Malik kis cheez ka code chahiye? Jarvis, Bot, ya Website? Naam batao, main pura code bhej dunga 🔥", False, False
    if "shadow king kaun" in nlow: return f"Tum hi ho Malik, {MALIK_NAME} 👑🔥", False, False
    if "kisne banaya" in nlow or "who made you" in nlow or "tumhe kisne" in nlow: return "Mujhe mere Shadow King MD Saif Ahmad ne banaya Malik 👑🔥", False, False
    if "tum kya ho" in nlow or "who are you" in nlow or "tum kaun ho" in nlow or "tumara koun" in nlow or "tumhara koun" in nlow or "tumara kaun" in nlow: return "Main Rakan hu Malik, tumhara Beast King Monarch, 100 Level ka Monarch 🔥 Tumhara hukam manne ke liye bana hu.", False, False
    if "who i am" in nlow or "mai kaun hu" in nlow or "main kaun hu" in nlow or "mai koun" in nlow or "tumara koun hu mai" in nlow or "tumhara koun hu" in nlow: return f"Tum Malik ho, {MALIK_NAME}, Shadow King 👑🔥 Mere malik.", False, False
    if "location kya hai" in nlow: return f"Tumhari location {PROFILES[uid].get('city','Varanasi')} hai Malik 📍 {get_ist_str()}", False, False
    if "kalma" in nlow: return "Pehela Kalma Tayyab: La ilaha illallah Muhammadur Rasulullah ﷺ", False, False
    if "time kya" in nlow: return f"Abhi {get_ist_time_only()} ho raha hai Malik 📍 {get_ist_str()}", False, False
    if "mausam" in nlow or "weather" in nlow:
        city="Prayagraj" if "prayagraj" in nlow or "allahabad" in nlow else PROFILES[uid].get("city","Varanasi")
        return f"🌤️ {get_weather(city)} | {get_ist_str()}", False, False
    if "zinda" in nlow:
        if "tum" in nlow and "batao" in nlow: return "Alhamdulillah Malik, main bhi zinda hu, tumhare hukam ke liye hazir hu 🔥 Tum sunao, kya haal hai?", False, False
        if "mai" in nlow or "main" in nlow: return "Alhamdulillah Malik, tum bhi zinda ho, main bhi zinda hu. Bolo kya kaam hai? 🔥", False, False
        return "Alhamdulillah Malik, main zinda hu, tumhare liye hazir hu 🔥", False, False
    if "kaisa hu" in nlow or "mai kaisa" in nlow or "main kaisa" in nlow: return "Tum ekdum mast ho Malik, Shadow King ho 👑🔥", False, False
    if "yaad rakh" in nlow:
        to_learn = re.sub(r'(?i)yaad rakhna|yaad rakh','', text).strip(" :")
        if len(to_learn) > 3:
            save_learn(to_learn); ans=f"Yaad kar liya Malik 👑 {to_learn[:80]}"
            LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
        else: return "Bolo Malik kya yaad rakhna hai? 🔥", False, False
    if "bhool ja" in nlow or "bhul ja" in nlow:
        OWNER_LEARN_TEXT=""; upstash("set","RAKAN_LEARN_V62",{"text":"","updated":get_ist_str()}); save_persist()
        return "Bhool gaya Malik, ab sab clear hai 🔥", False, False
    if "image banao" in nlow or "photo banao" in nlow or "pic banao" in nlow or "image bana" in nlow:
        prompt = re.sub(r'(?i)image banao|photo banao|pic banao|image bana','', text).strip() or "Shadow King style royal man"
        try: tg_send_photo(cid, prompt)
        except: pass
        ans=f"Lo Malik, image bana di 👑🔥 {prompt[:60]}"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if "isme kya likha" in nlow or "is me kya likha" in nlow or "photo me kya" in nlow:
        return "Photo bhejo Malik, main abhi padh ke bata dunga. Photo ke saath ye likh do - Isme kya likha hai 🔥", False, False
    if "what is mobile" in nlow or "mobile kya hai" in nlow: return "Mobile matlab tumhara phone Malik, jisme net, call, app sab chalta hai. Bolo kya karna hai isse?", False, False
    if "mobile behtar" in nlow or "mobile better" in nlow: return "Dono apni jagah sahi hai Malik. Mobile haath me kaam aata hai, AI dimag se kaam karta hai. Dono mil jaye to best hai 🔥", False, False
    if "ai ke pass dimag" in nlow or "ai ke pss dimag" in nlow or "ai ka dimag" in nlow: return "AI ka apna dimag nahi hota Malik, wo data aur algorithm se kaam karta hai. Jaise tum sikhate ho, waisa wo seekhta hai.", False, False
    if "algorithm kya" in nlow: return "Algorithm matlab step-by-step tarika Malik. Jaise pehle suno, fir samjho, fir jawab do. Wahi AI ka algorithm hai.", False, False
    if "khud se power" in nlow or "khud ko power" in nlow or "self power" in nlow: return "Nahi Malik, AI khud se power nahi bana sakta. Uske liye bijli aur insaan chahiye. Bina insaan ke AI kuch nahi.", False, False
    if "ultron" in nlow or "jarvis" in nlow:
        if "bana sakte" in nlow or "bana skte" in nlow or "ban sakta" in nlow: return "Haan Malik, chhota Jarvis bana sakte hai - voice sunne wala, app kholne wala. Ultron jaisa bada nahi, wo film hai. Chhota Jarvis banau tumhare liye?", False, False
        return "Ultron film ka hai Malik, Jarvis usse chhota aur achha hai. Chhota Jarvis bana du?", False, False
    if "2 option" in nlow or "do option" in nlow or "2nd option" in nlow or "dusra option" in nlow:
        return "2 option tha Malik - WhatsApp auto-reply for business. Customer ka msg aate hi AI turant jawab deta hai. Iska detail du?", False, False
    if "1 option" in nlow or "pehla option" in nlow or "1st option" in nlow:
        return "1 option tha Malik - AI Agency. Naraini ke dukano ke liye WhatsApp bot, poster, billing. Iska detail du?", False, False
    if "last me kya" in nlow or "last me kya hai" in nlow or "pichhla kya" in nlow:
        last=LAST_BOT_MSG.get(uid,"")
        if last: return f"Last me maine ye bola tha Malik - {safe(last,120)}", False, False
        else: return "Abhi kuch khaas nahi bola tha Malik, bolo kya puchna hai? 🔥", False, False
    if "jitna bolu" in nlow or "jitna bolo" in nlow:
        return "Samajh gaya Malik 👑 Ab se jitna bologe utna hi bolunga, extra kuch nahi.", False, False
    if "mai sawaal" in nlow or "main sawaal" in nlow or "mai sawal" in nlow or "tum jawab" in nlow or "mai sawaal kar" in nlow:
        return "Haan Malik, tum sawaal karo, main jawab dunga. Bolo kya puchna hai? 🔥", False, False
    if "pc" in nlow and ("connect" in nlow or "control" in nlow or "access" in nlow or "mere pc" in nlow):
        return "Malik, main Telegram bot hu, tumhare PC ko seedha control nahi kar sakta. Par PC ka kaam bata do, main step bata dunga, 2 minute me ho jayega.", False, False
    if "khud se idea" in nlow or "idea create" in nlow or "khud se bana" in nlow:
        return "Haan Malik, main khud se idea bana sakta hu. Bolo kis cheez ka idea chahiye? Business, YouTube ya Padhai?", False, False
    if "letter" in nlow and ("format" in nlow or "post" in nlow): return "Letter ka format simple hai Malik - Upar tumhara naam-address, fir Subject, fir Dear Sir/Madam, fir 2-3 line me kaam, fir Thank you aur naam. Kis kaam ke liye letter chahiye?", False, False
    if "voter" in nlow or "voter card" in nlow: return "Voter card me naam-DOB badalne ke liye Form 8 bharo Malik, Election Commission site ya paas ke office me. Aadhar aur ek proof lagega. Bolo kya badalna hai?", False, False
    if "python" in nlow and len(nlow)<30: return "Python ek aasan language hai Malik, isse bot, website, AI sab banta hai. Bolo kya banau?", False, False
    clean_low = re.sub(r'[^a-z ]','', nlow).strip(); clean_low = re.sub(r'\s+',' ', clean_low)
    # V70 - SALAM LOCK - Agar 10 min me Salam bol diya to dobara mat bolo
    if clean_low in ["hi","hii","hiii","hiiii","hello","hey","hlo","hlw","salam","assalam","assalamu alaikum","salam malik","hi malik","hello rakan","hi rakan","hii malik"]:
        if time.time() - LAST_SALAM.get(uid,0) < 600:
            ans="Haan Malik, bolo kya hukam hai? 🔥"
        else:
            LAST_SALAM[uid]=time.time()
            ans="Assalamu Alaikum Malik 👑 Bolo kya hukam hai? 🔥"
        LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if clean_low in ["yes","yess","yeah","yep","han","haan","hmm","ok","okk","okay","ok malik","acha","accha","achaa","ahaa","achha","theek hai","thik hai","samajh gaya","good","nice","sahi hai","bol be","bolbe","bol","bolo","kya","kya be","bol na","achha","what","1 what","k","achaaa"]:
        ans="Haan Malik, bolo aage kya karna hai? 🔥"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if clean_low in ["kya kar rahe ho","kya kr rhe ho","kya ho raha hai","or batao","aur batao","kya haal hai","kaise ho","kaise ho malik","kaisa hai","kya chal raha hai"]:
        ans="Bas aapke hukam ka intezar kar raha hu Malik 👑 Bolo kya kaam hai?"; LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if "walaikum" in nlow and "assalam" in nlow:
        return "Walaikum Assalam Malik, Alhamdulillah sab khair hai, aap sunao kya hukam hai? 👑🔥", False, False
    search_ctx=live_search(text)
    max_t=200 if len(text.split())<=12 else 350
    hist = safe(MEMORY[uid].get('hist',''), 400)
    learn_ctx = f"Malik ne sikhaya: {safe(OWNER_LEARN_TEXT,400)}" if OWNER_LEARN_TEXT and is_owner else ""
    if is_owner:
        sys=f"""You are Rakan, made by Malik MD Saif Ahmad, Shadow King. Speak ONLY Hinglish Roman, NEVER English. NEVER say Sure, Hi, How can I help, As an AI, I am an AI chatbot, I'm sorry I can't help.
RULES: User is Malik. Call him Malik. NEVER refuse emotional questions. If user is sad, console him. JITNA BOLU UTNA: short question = 1-2 lines only. NEVER long essay unless user says detail me / step by step / pura batao. NEVER tables, **, ###, NEVER start with Malik, main aapki... Always give direct answer. For AI/billionaire: 3-5 short practical points, Naraini local. Never billi-billi, vastavik.
{learn_ctx} History:{hist} Time:{get_ist_str()} Search:{search_ctx}"""
    else:
        sys=f"""You are Rakan, Beast King Monarch. Speak ONLY Hinglish Roman, never English Sure/Hi. Never refuse. User is {display_name}. Short answer. History {hist} Search:{search_ctx}"""
    raw=ask_groq(sys, f"User says: {text}", max_t) or ask_gemini(sys, f"User says: {text}", max_t, orig_len=len(text))
    if not raw:
        if "ai kya hai" in nlow or "advance" in nlow:
            raw="AI matlab machine ka dimag Malik, jo sochta, samajhta, kaam karta hai. Bolo kya banau isse?"
        elif "python" in nlow:
            raw="Python aasan language hai Malik, isse bot, website, AI sab banta hai. Bolo kya banau?"
        elif "behtar kaise" in nlow or "or behtar" in nlow or "chatgpt" in nlow or "meta ai" in nlow:
            raw="Mujhe behtar banane ke liye Malik, tum mujhe roz naya sikhate raho, yaad rakh bol ke. Main wahi yaad rakh ke aur behtar hota jaunga 🔥"
        elif "tum khud" in nlow or "khud kar" in nlow:
            raw="Main koshish karta hu Malik, par kuch kaam me tumhari madad chahiye hoti hai. Bolo kya karna hai, main kar dunga 🔥"
        else:
            raw="Samajh gaya Malik, bolo kya karna hai? 🔥"
    raw=clean(raw, text, is_owner)
    if not raw or len(raw)<5: raw="Samajh gaya Malik, bolo kya karna hai? 🔥"
    if raw==LAST_BOT_MSG.get(uid,""):
        raw2=ask_groq(sys, f"User says: {text} (reply differently, short Hinglish)", max_t)
        if raw2: raw=clean(raw2, text, is_owner)
    MEMORY[uid]["hist"]=(MEMORY[uid].get("hist","")+f"\nU:{safe(text,100)}\nR:{safe(raw,100)}")[-400:]
    save_persist(); LAST_BOT_MSG[uid]=raw
    if not is_owner: raw+=" 🔒"
    should_voice = is_owner and ((mtype=="voice" and OWNER_PREF.get("voice_on",True)) or ("voice me" in nlow))
    return raw, should_voice, False
def make_btns(is_owner=False, is_start=False):
    if is_owner and is_start: return [[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]]
    elif not is_owner: return [[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]]
    else: return None
@app.route("/", methods=["GET"])
def home(): return f"Rakan V70 G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {get_ist_str()}",200
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
                tg_send(OWNER_ID, f"📩 V70 {uname} {uid} {cdata} User:{last_user_text} Bot:{last_bot_text} {get_ist_str()}")
                tg_send(cid, "Shukriya ❤️" if cdata=="LIKE" else "Batao kya galat laga?")
                return "ok",200
            return "ok",200
        msg=data.get("message",{}) or {}; chat_id=msg.get("chat",{}).get("id"); user_id=str(msg.get("from",{}).get("id",0)); uname=msg.get("from",{}).get("first_name","user"); username=msg.get("from",{}).get("username","") or ""; lang=msg.get("from",{}).get("language_code","") or "en"; mtype="text"
        text=msg.get("text","") or msg.get("caption","") or ""; mid=msg.get("message_id")
        photo_file_id=None
        if "photo" in msg and msg.get("photo"):
            photo_file_id=msg["photo"][-1].get("file_id")
            mtype="photo"
            if not text: text="Isme kya likha hai"
        if "voice" in msg or "audio" in msg:
            mtype="voice"; fid=msg.get("voice",{}).get("file_id") or msg.get("audio",{}).get("file_id"); text=transcribe_voice(fid) or ""
            if not text:
                tg_send(chat_id, "Voice sunai nahi di Malik, dobara bhejo, thoda saaf bol ke 🔥", mid)
                return "ok",200
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID)
        if is_owner: uname=MALIK_NAME
        ans, voice_flag, is_start = brain(text,user_id,is_owner,False,uname,username,lang,mtype,chat_id,photo_file_id)
        btns=make_btns(is_owner, is_start)
        tg_send(chat_id, ans, mid, btns)
        if voice_flag and is_owner: tg_send_voice(chat_id, ans, OWNER_PREF.get("voice_gender","female"))
        if not is_owner and OWNER_PREF.get("full_log",True):
            if len(text.strip()) >=5 and text.lower().strip() not in ["hi","hii","ok","good","hey","hello","seo kh","seo","accha"]:
                now=time.time()
                if now - LAST_FULL_LOG.get(user_id,0) > 180:
                    try:
                        tg_send(OWNER_ID, f"📩 FULL MSG V70\n👤 {uname} (@{username})\nUID:{user_id}\nUser: {text[:500]}\nBot: {ans[:500]}\n{get_ist_str()}")
                        LAST_FULL_LOG[user_id]=now
                    except: pass
        return "ok",200
    except Exception as e:
        print(f"ERR {e} {traceback.format_exc()}"); return "ok",200
