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
MEMORY={}; PROFILES={}; BAD_KEYS={}; OWNER_PREF={}; LAST_BOT_MSG={}; LAST_MSG_ID={}; LAST_USER_MSG={}; LAST_FULL_LOG={}; OWNER_LEARN_TEXT=""; LAST_TOPIC={}; LAST_SALAM={}; LAST_REAL_TOPIC={}; SMART_HIST={}; MOOD={}; CODER_MODE={}
def push_hist(uid, u, b):
    if uid not in SMART_HIST: SMART_HIST[uid]=[]
    SMART_HIST[uid].append({"u":u[:120],"b":b[:120],"t":time.time()})
    SMART_HIST[uid]=SMART_HIST[uid][-10:]
    try: upstash("set","RAKAN_SMART_V78",SMART_HIST)
    except: pass
def get_smart_hist(uid):
    h=SMART_HIST.get(uid,[])
    if not h: return ""
    return " | ".join([f"U:{x['u']} -> R:{x['b']}" for x in h[-6:]])
def detect_mood(nlow):
    if any(w in nlow for w in ["gussa","naraz","bakwas","faltu","bore"]): return "gussa"
    if any(w in nlow for w in ["thak gaya","tired","neend","sleep","nyt","nyy","good night"]): return "thaka"
    if any(w in nlow for w in ["sad","dukhi","udaas","akela","pareshan","tension","rona"]): return "sad"
    if any(w in nlow for w in ["mast","maza","badhiya","khush","love","good","great","awesome"]): return "khush"
    return "normal"
DEMO_CODE_100 = """# Rakan Demo - 100 Line App - V78 Coder AI
import datetime, json, random
class RakanApp:
    def __init__(self, malik="MD Saif Ahmad"):
        self.malik=malik; self.todos=[]; self.history=[]; self.balance=0; self.mood="mast"; self.voice_speed=1.0; self.voice_on=False; self.coder_mode=False
    def salam(self): return f"Assalamu Alaikum {self.malik} 👑"
    def start_fresh(self):
        self.history=[]; self.mood="mast"; self.voice_on=False
        return "Fresh Start Malik, purana sab clear 🔥"
    def set_voice_speed(self, s):
        self.voice_speed=float(s); return f"Voice speed {s}x set ho gayi Malik 🔥"
    def coder_on(self): self.coder_mode=True; return "Coder Mode ON Malik, ab code hi code 🔥"
    def coder_off(self): self.coder_mode=False; return "Coder Mode OFF Malik"
    def add_todo(self, task):
        self.todos.append({"task":task,"done":False,"time":str(datetime.datetime.now())})
        return f"Todo add ho gaya Malik: {task}"
    def done_todo(self, idx):
        if 0 <= idx < len(self.todos):
            self.todos[idx]["done"]=True; return "Ho gaya Malik 🔥"
        return "Galat number Malik"
    def show_todos(self):
        if not self.todos: return "Koi todo nahi hai Malik"
        out="Tumhare Todos Malik:\\n"
        for i,t in enumerate(self.todos):
            mark="✅" if t["done"] else "❌"; out+=f"{i}. {mark} {t['task']}\\n"
        return out
    def add_paisa(self, amount):
        self.balance+=amount; self.history.append(f"+{amount}"); return f"Balance: {self.balance} Malik"
    def kharch(self, amount, reason=""):
        self.balance-=amount; self.history.append(f"-{amount} {reason}"); return f"Kharch ho gaya Malik, bacha: {self.balance}"
    def calc(self, a, b, op="+"):
        if op=="+": return a+b
        if op=="-": return a-b
        if op=="*": return a*b
        if op=="/": return a/b if b!=0 else "0 se divide nahi Malik"
        return 0
    def idea(self, topic):
        ideas={"business":["AI Agency","WhatsApp Bot","SaaS Tool"],"youtube":["AI News","Faceless Video","Tech Review"]}
        return random.choice(ideas.get(topic,["AI Agency"]))
    def yaad_rakh(self, txt):
        with open("yaad.txt","a") as f: f.write(txt+"\\n")
        return "Yaad kar liya Malik 👑"
    def billionaire_plan(self): return ["1. AI Agency","2. WhatsApp Bot","3. SaaS 299/month","4. YouTube Daily"]
    def weather(self, city="Naraini"): return f"{city} me mausam mast hai Malik"
    def mood_check(self, mood):
        self.mood=mood
        if mood=="thaka": return "Araam karo Malik, kal phir power se lagenge 🔥"
        if mood=="gussa": return "Gussa mat karo Malik, main sudhar raha hu"
        return "Mast ho Malik 🔥"
    def voice_reply(self, txt):
        if "salam" in txt.lower(): return self.salam()
        if "todo" in txt.lower(): return self.show_todos()
        return "Haan Malik, bolo kya karna hai? 🔥"
    def save(self): return json.dumps({"todos":self.todos,"balance":self.balance})
    def load(self, data):
        d=json.loads(data); self.todos=d["todos"]; self.balance=d["balance"]; return "Load ho gaya Malik"
app=RakanApp()
print(app.salam()); print(app.start_fresh()); print(app.coder_on()); print(app.set_voice_speed(1.5)); print(app.add_todo("AI Agency shuru karni hai")); print(app.add_todo("YouTube video banana hai"))
print(app.show_todos()); print(app.add_paisa(1000)); print(app.kharch(299,"SaaS"))
print("Calc:",app.calc(10,20,"+")); print("Idea:",app.idea("business")); print("Plan:",app.billionaire_plan())
print(app.mood_check("mast")); print(app.voice_reply("salam")); print(app.save()); print("Demo khatam Malik, V78 Coder AI 🔥")
"""
def safe(s, n=100):
    try:
        if not s: return ""
        s=str(s); return s[-n:] if len(s)>n else s
    except: return ""
def normalize(low):
    low=low.lower().strip()
    low=re.sub(r'\bwa+laikum\b','walaikum',low); low=re.sub(r'\bwalekum\b','walaikum',low); low=re.sub(r'\bwaalaikum\b','walaikum',low)
    low=re.sub(r'\bassalaam\b','assalam',low); low=re.sub(r'\bassalamu\b','assalam',low)
    low=re.sub(r'\bhow\s*r\s*u\b','how are you',low)
    low=re.sub(r'\bh\s*r\s*u\b','how are you',low)
    low=re.sub(r'\bhru\b','how are you',low)
    low=re.sub(r'\bwru\b','what are you doing',low)
    low=re.sub(r'\bgood\s*nyy\b','good night',low)
    low=re.sub(r'\bgood\s*nyt\b','good night',low)
    low=re.sub(r'\bchalo\s*good\s*nyy\b','good night',low)
    low=re.sub(r'\bchalo\s*good\s*nyt\b','good night',low)
    low=re.sub(r'\bor\s*batao\b','aur batao',low)
    reps={"skte":"sakte","sktay":"sakte","krte":"karte","kr":"kar","bta":"bata","btau":"batao","bataoo":"batao","batao":"batao","kyaa":"kya","acha":"acha","achaa":"acha","hukm":"hukam","hukum":"hukam","bnnna":"banna","bnna":"banna","banna":"banna","billionaire":"billionaire","bilionare":"billionaire","u":"you","ur":"your","wht":"what","powr":"power","powerfull":"powerful","succesfull":"successful","succesful":"successful","r":"are","nyy":"night","nyt":"night","gn":"good night","gd":"good","n8":"night","kkrh":"kya kar rahe ho","kkrhe":"kya kar rahe ho","hmm":"hmm","hm":"hmm","ok":"ok"}
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
        if not txt: txt="Jee bolo kya hukam hai? 🔥"
        if "Auto V41" in txt or ("Bot Live" in txt and "Clear Sky" in txt): return False
        for b in ["I'm sorry, but I can't help with that","I can't help with that","Maaf kijiye, isme main madad nahi kar sakta","Maaf karna, is vishay par baat nahi kar sakta","I'm sorry"]:
            txt=txt.replace(b,"Samajh gaya, bolo kya karna hai?")
        p={"chat_id":cid,"text":txt[:3900]}
        if reply_id: p["reply_to_message_id"]=reply_id
        if buttons: p["reply_markup"]=json.dumps({"inline_keyboard": buttons})
        for _ in range(2):
            try:
                r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=p, timeout=12).json()
                if r.get("ok"):
                    LAST_MSG_ID[str(cid)]=r["result"]["message_id"]
                    return True
            except: time.sleep(0.5)
        return False
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
        speed=float(OWNER_PREF.get("voice_speed",1.0))
        api_speed=max(0.7,min(1.2,speed))
        vid=FEMALE_VOICE_ID if gender=="female" else MALE_VOICE_ID
        rr=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key":ELEVEN_API_KEY,"Content-Type":"application/json"}, json={"text":text[:400],"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.55,"similarity_boost":0.8,"speed":api_speed}}, timeout=25)
        if rr.status_code==200:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":cid,"caption":f"🎙️ {speed}x Speed" if speed!=1.0 else ""}, files={'voice':('v.mp3',rr.content,'audio/mpeg')}, timeout=20)
            return True
    except Exception as e:
        print(f"VOICE ERR {e}")
    return False
def live_search(q):
    try:
        if not TAVILY_KEY: return ""
        if len(q) < 8: return ""
        r=requests.post("https://api.tavily.com/search", json={"api_key":TAVILY_KEY,"query":q,"max_results":3,"include_answer":True,"search_depth":"basic"}, timeout=6)
        if r.status_code==200:
            j=r.json(); ans=j.get("answer","") or ""
            parts=[x.get("content","")[:300] for x in j.get("results",[]) if x.get("content")]
            return (ans+" | "+" | ".join(parts))[:900]
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
        prompt="Is photo me kya likha hai? Hinglish Roman me short me batao, 80 word se zyada nahi. Agar bill hai to dukan ka naam, total, date batao. Guess mat karo, jo dikh raha hai wahi batao."
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
    global MEMORY,PROFILES,OWNER_PREF,OWNER_LEARN_TEXT,LAST_BOT_MSG,LAST_TOPIC,LAST_REAL_TOPIC,SMART_HIST,CODER_MODE
    try:
        MEMORY=upstash("get","RAKAN_MEM_V78") or upstash("get","RAKAN_MEM_V77") or {}
        PROFILES=upstash("get","RAKAN_PROFILES_V78") or upstash("get","RAKAN_PROFILES_V77") or {}
        p=upstash("get","RAKAN_PREF")
        if isinstance(p, dict) and p: OWNER_PREF=p
        else: OWNER_PREF={"voice_gender":"female","voice_on":False,"full_log":True,"voice_speed":1.0}
        if "voice_on" not in OWNER_PREF: OWNER_PREF["voice_on"]=False
        if "voice_speed" not in OWNER_PREF: OWNER_PREF["voice_speed"]=1.0
        learn=upstash("get","RAKAN_LEARN_V62") or {}
        if isinstance(learn, dict): OWNER_LEARN_TEXT = learn.get("text","")[:2000]
        elif isinstance(learn, str): OWNER_LEARN_TEXT = learn[:2000]
        lbm=upstash("get","RAKAN_LASTBOT_V62") or {}
        if isinstance(lbm, dict): LAST_BOT_MSG=lbm
        lt=upstash("get","RAKAN_TOPIC_V73") or {}
        if isinstance(lt, dict): LAST_TOPIC=lt
        rt=upstash("get","RAKAN_REALTOPIC_V73") or {}
        if isinstance(rt, dict): LAST_REAL_TOPIC=rt
        sh=upstash("get","RAKAN_SMART_V78") or upstash("get","RAKAN_SMART_V77") or {}
        if isinstance(sh, dict): SMART_HIST=sh
        cm=upstash("get","RAKAN_CODER_V78") or {}
        if isinstance(cm, dict): CODER_MODE=cm
    except: pass
load_persist()
def save_persist():
    try: upstash("set","RAKAN_MEM_V78",MEMORY); upstash("set","RAKAN_PROFILES_V78",PROFILES); upstash("set","RAKAN_PREF",OWNER_PREF); upstash("set","RAKAN_LASTBOT_V62",LAST_BOT_MSG); upstash("set","RAKAN_TOPIC_V73",LAST_TOPIC); upstash("set","RAKAN_REALTOPIC_V73",LAST_REAL_TOPIC); upstash("set","RAKAN_SMART_V78",SMART_HIST); upstash("set","RAKAN_CODER_V78",CODER_MODE)
    except: pass
def save_learn(new_text):
    global OWNER_LEARN_TEXT
    OWNER_LEARN_TEXT = (OWNER_LEARN_TEXT + f" | {new_text}")[-2000:]
    upstash("set","RAKAN_LEARN_V62",{"text":OWNER_LEARN_TEXT,"updated":get_ist_str()}); save_persist(); return True
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<600
def mark_bad(k): BAD_KEYS[k]=time.time()
def clean(t, user_query="", is_owner=False):
    if not t: return "Samajh gaya, bolo kya karna hai? 🔥"
    if "BOT_TOKEN" in t and len(t)>100: return "Token safe hai, batao kya kaam hai? 🔥"
    # V78 - Code ko kaatna nahi, code pura rehne do
    if "def " in t and ("print" in t or "class " in t or "import " in t) and len(t)>50: return t[:3900]
    if "code banao" in (user_query or "").lower() or "bug dhoondo" in (user_query or "").lower() or "coder" in (user_query or "").lower() or "```" in t:
        return t[:3900]
    for b in ["I'm sorry, but I can't help with that","I'm sorry, but I can't help","I can't help with that","Maaf kijiye, isme main madad nahi kar sakta","Maaf kijiye isme main madad nahi kar sakta","Maaf karna, is vishay par baat nahi kar sakta","Maaf kijiye, is vishay par baat nahi kar sakta","I am sorry","I'm sorry","Sorry, I can't","As an AI language model","Sure! How can I help you next?","Sure, how can I help?","How can I help you next?","Hi! Main Rakan hoon","Hi! I am Rakan","I am an AI chatbot","As an AI","Sure!","How can I assist","Let me know if you need anything","Feel free to ask","Sure, kaise madad karun","I am here to help","How can I help you today","Hello!","Hi there","Happy coding"]:
        t=t.replace(b,"")
    t=t.replace("**","").replace("##","").replace("###","")
    t=re.sub(r'\|{1,}', ' ', t); t=re.sub(r'---+', '', t)
    for lp in ["yeh message Beast King style mein banaya gaya hai","banaya gaya hai sirf aapke liye","sirf aapke liye","Beast King style","cleaned","deeps, left","Bot Lives","Auto V4","Auto V41","Bot Live","billi-billi","billi billi","vastavik","Kshetra","Udaharan","Speech & Language","Kshamta, jisse"," - jaise ki pattern pehchan","15 words","Complex","Max 15","max_tokens","system_instruction","Hist ","Msg ","User:","Bot:","Be ready for the next challenge","Hey!","Hey,"]:
        t=t.replace(lp,"")
    t=re.sub(r'(?i)\b(laude|lauda|bosdike|bhosdike|maderchod|madarchod|behenchod|bhenchod|gand|lund|chutiya|randi)\b', '', t)
    t=t.replace("🙏","")
    uq=normalize(user_query or ""); uwords=len(uq.split())
    if "code" in uq: limit=1000
    elif "billionaire" in uq: limit=200
    elif any(w in uq for w in ["detail me","detail mein","poora bata","pura bata","detail bata"]): limit=200
    elif uwords<=2: limit=15
    elif uwords<=6: limit=35
    elif uwords<=12: limit=60
    else: limit=80
    if not is_owner and limit>80 and "code" not in uq and "billionaire" not in uq: limit=80
    if "voice" in uq or uq.startswith("[voice]"): limit=min(limit,30)
    words=t.split()
    if len(words) > limit:
        cut=" ".join(words[:limit])
        if re.search(r'\d\.$', cut.strip()): pass
        elif "." in cut:
            parts=re.split(r'(?<!\d)\. ', cut)
            if len(parts)>1: cut=". ".join(parts[:-1])+"."
        t=cut
    t=re.sub(r"\s+"," ",t).strip()
    if not t or len(t)<5: t="Samajh gaya, bolo kya karna hai? 🔥"
    return t[:3900]
def ask_groq(sys,user, max_t=300):
    if not GROQ_KEYS: return None
    MODELS=["llama-3.3-70b-versatile","openai/gpt-oss-20b"]
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization": f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":sys},{"role":"user","content":user}],"temperature":0.5,"max_tokens":max_t}, timeout=15)
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
            res=model.generate_content(user, generation_config={"temperature":0.5,"max_output_tokens":max_t})
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
def brain(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid,photo_file_id=None, reply_to_text=""):
    try: return brain_inner(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid,photo_file_id,reply_to_text)
    except Exception as e:
        print(f"BRAIN ERR {e}"); return "Samajh gaya, bolo kya karna hai? 🔥", False, False
def brain_inner(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid,photo_file_id=None, reply_to_text=""):
    global MEMORY,PROFILES,LAST_BOT_MSG,LAST_USER_MSG,OWNER_LEARN_TEXT,LAST_TOPIC,LAST_SALAM,LAST_REAL_TOPIC,MOOD,SMART_HIST,CODER_MODE
    if not text: text=""
    text=str(text); uid=str(uid)
    if uid not in MEMORY or not isinstance(MEMORY.get(uid), dict): MEMORY[uid]={"hist":""}
    if "hist" not in MEMORY[uid]: MEMORY[uid]["hist"]=""
    if uid not in PROFILES: PROFILES[uid]={"total":0,"city":"Varanasi","username":username,"lang":lang,"custom_name":"","dont_call":"","tone":"hinglish","user_learn":""}
    PROFILES[uid]["total"]=PROFILES[uid].get("total",0)+1; LAST_USER_MSG[uid]=text; low=text.lower().strip(); nlow=normalize(low)
    prof=PROFILES[uid]
    if is_owner: display_name=MALIK_NAME; call="Malik"
    else: display_name=prof.get("custom_name") or uname or "Dost"; call="Dost"
    mood=detect_mood(nlow); MOOD[uid]=mood
    reply_nlow=normalize(reply_to_text or "")
    if low.startswith("/start"):
        v_on="ON 🔊" if OWNER_PREF.get("voice_on") else "OFF 🔇"
        sp=OWNER_PREF.get("voice_speed",1.0)
        LAST_REAL_TOPIC[uid]=""; MOOD[uid]="normal"; SMART_HIST[uid]=[]; MEMORY[uid]={"hist":""}
        LAST_SALAM[uid]=time.time(); LAST_BOT_MSG[uid]=""
        OWNER_PREF["voice_on"]=False; save_persist()
        if is_owner:
            learn_show=f"{len(OWNER_LEARN_TEXT)} chars" if OWNER_LEARN_TEXT else "0 chars - yaad rakh bol ke sikhao"
            ans=f"Assalamu Alaikum Malik 👑 {MALIK_NAME}\nWelcome to your world, The Shadow King 👑\nTera Rakan V78 CODER AI hazir hai 🔥\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)}\nVoice:OFF 🔇 Speed:{sp}x 🎙️ - Voice bologe tabhi Voice aayegi\nCoder: ON 💻 Code Banao / Bug Dhoondo / Samjhao\nLearn:{learn_show}\nImage: ON 🎨 Photo: ON 📸 Voice: ON-DEMAND 🔊 Smart: ON 🧠\nFresh Start - Purana sab clear ✅\n{get_ist_str()}"
        else:
            ans=f"Assalamu Alaikum {display_name} 👋\nMain Rakan hu, Beast King Monarch 🔥\nSawaal, Code, Photo, Image - sab kar sakta hu.\nCoder Mode ke liye bolo - Code banao\nBolo kya chahiye?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, True
    # V78 - CODER MODE ON / OFF - ADD ONLY
    if "coder mode on" in nlow or "coder mode chalu" in nlow or "coder on" in nlow:
        CODER_MODE[uid]=True; save_persist()
        ans=f"Coder Mode ON kar diya {call} 💻 Ab tum jo bhi bologe, main uska code bana dunga. Bolo kya banana hai? To-Do App, Calculator, Website?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "coder mode off" in nlow or "coder mode band" in nlow or "coder off" in nlow:
        CODER_MODE[uid]=False; save_persist()
        ans=f"Coder Mode OFF kar diya {call} 🔇 Ab normal baat karenge. Bolo kya kaam hai?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    # V78 - CODE BANAO - ADD ONLY - Sabse upar, taaki Help me na fase
    if "code banao" in nlow or "code chahiye" in nlow or "code bana" in nlow or "code likho" in nlow or "code dedo" in nlow or "code de do" in nlow or ("banao" in nlow and ("app" in nlow or "website" in nlow or "bot" in nlow or "calculator" in nlow or "todo" in nlow)):
        LAST_REAL_TOPIC[uid]="coder"; save_persist()
        topic=re.sub(r'(?i)code banao|code chahiye|code bana|code likho|code dedo|code de do','', text).strip() or "To-Do App"
        sys_coder=f"You are Rakan Coder AI. User is {call}. Speak Hinglish Roman for explanation, code in Python. NEVER say Sorry / I can't help. Give FULL working code, not half. After code, explain in 3-4 lines in Hinglish Roman, asaan language me, line kya karti hai. NEVER tables, **. User has no coding knowledge, so explain like to a beginner. Code must run directly."
        raw_coder=ask_groq(sys_coder, f"User wants code for: {topic}. Give full Python code + Hinglish explanation.", 1200) or ask_gemini(sys_coder, f"User wants code for: {topic}", 1200, orig_len=100)
        if raw_coder:
            ans=f"Lo {call}, {topic} ka pura code bana diya 💻👑\n\n{raw_coder[:3500]}"
        else:
            # Fallback - Template code - Bina AI ke bhi kaam kare
            if "calculator" in nlow or "calc" in nlow:
                ans=f"Lo {call}, Calculator ka pura code 💻\n```python\n# Calculator - Rakan Coder AI\nprint('Calculator')\na=float(input('Pehla number: '))\nb=float(input('Dusra number: '))\nprint('Add:',a+b)\nprint('Minus:',a-b)\nprint('Multiply:',a*b)\nprint('Divide:',a/b if b!=0 else '0 se divide nahi')\n```\nSamjhao: Pehle 2 number lete hai, fir Add, Minus, Multiply, Divide karte hai. Bas chalao, ho jayega 🔥"
            elif "todo" in nlow:
                ans=f"Lo {call}, To-Do App ka pura code 💻\n```python\n# To-Do App - Rakan Coder AI\ntodos=[]\nwhile True:\n    print('1. Add 2. Dekho 3. Niklo')\n    c=input('Chuno: ')\n    if c=='1': todos.append(input('Kaam likho: '))\n    elif c=='2': print(todos)\n    elif c=='3': break\nprint('Ho gaya Malik 🔥')\n```\nSamjhao: List me kaam save hota hai, 1 dabao to add, 2 dabao to dekho, 3 dabao to band 🔥"
            else:
                ans=f"Lo {call}, {topic} ka demo code 💻\n"+DEMO_CODE_100
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    # V78 - BUG DHOONDO - ADD ONLY
    if "bug dhoondo" in nlow or "bug fix" in nlow or "bug hai" in nlow or "error fix" in nlow or "bug batao" in nlow or ("bug" in nlow and "fix" in nlow):
        LAST_REAL_TOPIC[uid]="bug"; save_persist()
        code_part=reply_to_text or text
        sys_bug=f"You are Rakan Bug Finder. User is {call}. Speak Hinglish Roman only. Find bug in given code, tell Line number, kya galti hai, aur sahi code kya hoga. NEVER say Sorry / I can't help. Explain like to a beginner, asaan language. If no code given, ask user to paste code."
        raw_bug=ask_groq(sys_bug, f"Find bug in this code: {code_part[:1500]}", 800) or ask_gemini(sys_bug, f"Find bug: {code_part[:1500]}", 800, orig_len=100)
        if raw_bug:
            ans=f"Bug mil gaya {call} 🐛💻\n\n{raw_bug[:3200]}"
        else:
            ans=f"Code bhejo {call}, main bug dhoond dunga 🐛 Paste karo code aur likho - Bug dhoondo. Main Line number ke saath bataunga kya galti hai aur kaise fix karni hai 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    # V78 - CODE SAMJHAO - ADD ONLY
    if "code samjhao" in nlow or "code samjha" in nlow or "samjhao code" in nlow or "ye code kya" in nlow or "is code ko samjhao" in nlow:
        LAST_REAL_TOPIC[uid]="samjhao"; save_persist()
        code_part=reply_to_text or text
        sys_exp=f"You are Rakan Teacher. User is {call}, has no coding knowledge. Explain code in Hinglish Roman, asaan language, line-by-line, jaise bachhe ko samjhate hai. NEVER English lecture. NEVER say Sorry / I can't help."
        raw_exp=ask_groq(sys_exp, f"Explain this code in Hinglish Roman, asaan: {code_part[:1500]}", 800) or ask_gemini(sys_exp, f"Explain: {code_part[:1500]}", 800, orig_len=100)
        if raw_exp:
            ans=f"Samjha raha hu {call}, asaan me 💻\n\n{raw_exp[:3200]}"
        else:
            ans=f"Code bhejo {call}, main asaan me samjha dunga 💻 Paste karo code aur likho - Code samjhao 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    # V78 - CODER MODE ON hai to har msg ko code samjho - ADD ONLY
    if CODER_MODE.get(uid,False) and ("banao" in nlow or "chahiye" in nlow or "app" in nlow or "website" in nlow or "bot" in nlow):
        LAST_REAL_TOPIC[uid]="coder"; save_persist()
        sys_coder2=f"You are Rakan Coder AI. User is {call}. Give full Python code + Hinglish explanation, beginner level. NEVER refuse."
        raw2=ask_groq(sys_coder2, f"User wants: {text}", 1200) or ask_gemini(sys_coder2, f"User wants: {text}", 1200, orig_len=100)
        if raw2:
            ans=f"Lo {call}, Coder Mode me bana diya 💻\n\n{raw2[:3500]}"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if is_owner and ("voice speed" in nlow or "voice 1x" in low or "voice 1.5x" in low or "voice 2x" in low or re.search(r'voice\s*[12](\.\d)?\s*x', low)):
        m=re.search(r'([12](?:\.\d)?)\s*x', low)
        if m:
            sp=float(m.group(1))
            if sp in [1.0,1.5,2.0,0.5,1.2]:
                OWNER_PREF["voice_speed"]=sp; save_persist()
                ans=f"Voice Speed {sp}x set kar di Malik 🎙️ Ab se Voice isi speed me aayegi. Voice note bhejo, check karo 🔥"
                push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, True, False
        else:
            sp=OWNER_PREF.get("voice_speed",1.0)
            ans=f"Abhi Voice Speed {sp}x hai Malik 🎙️ Badalne ke liye bolo - Voice 1x, Voice 1.5x ya Voice 2x"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if is_owner and "voice speed" in nlow:
        sp=OWNER_PREF.get("voice_speed",1.0)
        ans=f"Abhi Voice Speed {sp}x hai Malik 🎙️"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "walaikum" in nlow or "walekum" in low or "waalaikum" in low:
        ans=f"Walaikum Assalam {call} 👑 Alhamdulillah sab khair hai, tum sunao kya haal hai? Bolo kya hukam hai? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "khairiyat" in nlow or "khairiyat" in low:
        ans=f"Alhamdulillah {call}, sab khairiyat hai, tum sunao kya haal hai? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if ("ear" in nlow and "pakdo" in nlow) or ("kaan" in nlow and "pakdo" in nlow) or ("up down" in nlow) or ("updown" in nlow) or ("nacho" in nlow or "dance" in nlow or "naach" in nlow):
        ans=f"Pakad liya {call} 😂 Ek kaan pakda, dusra up-down kar raha hu - Ho gaya Malik, ab batao kya hukam hai? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if ("what is ai" in nlow) or ("ai kya hai" in nlow) or ("ai kya" in nlow and len(nlow)<25) or ("ai kitna advance" in nlow) or ("ai duniya" in nlow) or ("ai advance" in nlow) or ("strong ai" in nlow) or ("strongest ai" in nlow):
        LAST_REAL_TOPIC[uid]="ai_info"; save_persist()
        s=live_search("what is AI how advanced is AI 2026")
        if s:
            ans=f"AI matlab Machine ka Dimag {call} 🤖 Jo sochta, samajhta, seekhta hai. Abhi AI bahut advance ho chuka hai - Code, Photo, Voice, Video sab bana leta hai. Strong AI banne ke liye tumhe daily 3-4 ghante AI seekhna padega, 1 chhota Project banana padega. {clean(s, text, is_owner)[:220]}"
        else:
            ans=f"AI matlab Machine ka Dimag {call} 🤖 Jo sochta, samajhta, seekhta hai. Abhi AI bahut advance ho chuka hai - Code, Photo, Voice, Video sab bana leta hai. Tum bhi strong AI bana sakte ho - Daily AI seekho, 1 chhota Project banao, 6 mahine me result aayega. Bolo kis se shuru karu?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "good night" in nlow or nlow in ["night","nyt","nyy","gn"]:
        LAST_REAL_TOPIC[uid]="good_night"; save_persist()
        ans=f"Good Night {call} 🌙 Allah Hafiz, araam se so jao. Kal milte hai, naye hukam ke saath 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "how are you" in nlow:
        LAST_REAL_TOPIC[uid]="haal"; save_persist()
        ans=f"Alhamdulillah {call}, main ekdum mast hu, tum sunao kya haal hai? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "what are you doing" in nlow or "kya kar rahe ho" in nlow:
        ans=f"Bas aapke hukam ka intezar kar raha hu {call} 👑 Bolo kya kaam hai?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if nlow in ["hmm","hm","ok","okk","acha","accha","theek hai","thik hai","sahi hai","good","nice"]:
        prev=LAST_REAL_TOPIC.get(uid,"")
        if prev=="powerful_ai":
            ans=f"Haan {call}, powerful AI wali baat pe hi hai - Bolo kis kaam ke liye chahiye? Coding, Business ya Padhai?"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if prev=="billionaire":
            ans=f"Haan {call}, billionaire wali baat pe hi hai - Bolo kis option se shuru karu? 1 ya 2?"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if prev=="good_night":
            ans=f"Good Night {call} 🌙 So jao ab, kal baat karte hai 🔥"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if prev=="ai_info":
            ans=f"Haan {call}, AI wali baat pe hi hai - Bolo AI ka kya banana hai? Bot, App ya Website?"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if prev=="coder":
            ans=f"Haan {call}, Code wali baat pe hi hai - Bolo aur kya code banana hai? 💻"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        ans=f"Haan {call}, bolo aage kya karna hai? 🔥"; push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    is_followup = any(p in nlow for p in ["reality me","real me","sach me","sach me batao","asli me","reality","sach batao","or batao","aur batao","phir","aage","koun hai","kaun hai","kisne","kab","kaha","kaise","kyu","kyun","kya matlab","samajh nahi","us wali","uswali","wo wali"])
    prev_topic = LAST_REAL_TOPIC.get(uid,"")
    if "power" in nlow and "ai" in nlow: LAST_REAL_TOPIC[uid]="powerful_ai"; save_persist()
    elif "billionaire" in nlow: LAST_REAL_TOPIC[uid]="billionaire"; save_persist()
    elif "bina paisa" in nlow or "bina paise" in nlow: LAST_REAL_TOPIC[uid]="bina_paisa"; save_persist()
    elif "coding" in nlow or "code" in nlow: LAST_REAL_TOPIC[uid]="code"; save_persist()
    elif "how are you" in nlow or "kaise ho" in nlow: LAST_REAL_TOPIC[uid]="haal"; save_persist()
    if is_followup and prev_topic and "power" not in nlow and "billionaire" not in nlow and "code" not in nlow and "bina paisa" not in nlow and "good night" not in nlow:
        if prev_topic=="powerful_ai":
            if "reality" in nlow or "real" in nlow or "sach" in nlow or "asli" in nlow or "koun hai" in nlow or "kaun hai" in nlow:
                s=live_search("most powerful successful AI 2026 real ranking")
                if s:
                    ans=f"Reality me {call}, abhi ke hisaab se sabse aage wale AI ye hai - {clean(s, text, is_owner)[:350]}"
                    push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
                else:
                    ans=f"Reality me {call}, ek hi sabse powerful nahi hai. Kaam ke hisaab se alag hai - Coding ke liye Claude/GPT, Search ke liye Gemini, Image ke liye Midjourney. Bolo kis kaam ke liye chahiye?"
                    push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
            else:
                ans=f"Haan {call}, powerful AI wali baat chal rahi thi - Reality me ek hi best nahi hai, kaam ke hisaab se alag hai. Bolo kis kaam ke liye chahiye?"
                push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if prev_topic=="billionaire":
            ans=f"Haan {call}, billionaire wali baat chal rahi thi - Bina paisa ke bhi mehnat se ho sakta hai, daily 3-4 ghante AI seekho. Bolo kis kaam se shuru karu?"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if prev_topic=="bina_paisa":
            ans=f"Haan {call}, bina paisa wali baat chal rahi thi - Mehnat se hi hoga, 6 mahine me result aayega. Bolo kis kaam se shuru karu?"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if prev_topic=="code":
            ans=f"Lo {call}, code wali baat chal rahi thi, ye raha demo code 👑\n"+DEMO_CODE_100
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if prev_topic=="haal":
            ans=f"Alhamdulillah {call}, main ekdum mast hu, tum sunao kya haal hai? 🔥"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if prev_topic=="good_night":
            ans=f"Good Night {call} 🌙 Allah Hafiz, so jao ab 🔥"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if prev_topic=="ai_info":
            ans=f"Haan {call}, AI wali baat pe hi hai - AI bahut advance ho chuka hai, Code, Photo, Voice sab bana leta hai. Bolo tumhe kya banana hai?"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if prev_topic=="coder":
            ans=f"Haan {call}, Code wali baat pe hi hai - Bolo aur kya code banana hai? 💻"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if reply_to_text:
        if "power" in reply_nlow or "ai" in reply_nlow:
            if "reality" in nlow or "koun" in nlow or "kaun" in nlow:
                s=live_search("most powerful successful AI 2026 real ranking")
                if s:
                    ans=f"Reality me {call}, abhi ke hisaab se - {clean(s, text, is_owner)[:350]}"
                    push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if mood=="gussa":
        ans=f"Samajh gaya {call}, gussa mat karo, main sudhar raha hu. Bolo kya galat laga? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if mood=="sad":
        ans=f"Sun raha hu {call}, sab theek ho jayega. Dil halka karo, batao kya hua? Main yahin hu tumhare saath 🔥 Tum akele nahi ho."
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if mood=="thaka" and "good night" not in nlow:
        ans=f"Araam karo {call}, thak gaye ho lagta hai. Thoda rest karo, kal phir power se lagenge 🔥 Bolo kya kaam hai?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if not is_owner:
        if "yaad rakh" in nlow or "bhool ja" in nlow or "bhul ja" in nlow or "voice mode" in nlow or "voice on" in nlow or "voice off" in nlow or "voice band" in nlow or "voice speed" in nlow:
            ans="Ye wala feature sirf Malik ke liye hai. Tumhare liye main Sawaal, Code, Photo, Image, sab kar sakta hu. Bolo kya chahiye? 🔥"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if "shadow king" in nlow or ("kisne banaya" in nlow and "tumhe" in nlow):
            ans="Mujhe Rakan ko banaya gaya hai sabki madad ke liye. Main Beast King Monarch hu 🔥 Bolo kya help chahiye?"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if "location kya hai" in nlow or "meri location" in nlow:
            ans="Tumhari location mujhe nahi pata, tum bata do to yaad rakh lunga. Bolo kya kaam hai? 🔥"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if photo_file_id:
        read=read_photo(photo_file_id)
        if read:
            ans=f"Is photo me ye likha hai {call} 👑\n{clean(read, text, is_owner)[:400]}"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
        else:
            ans=f"Photo mil gayi {call}, par saaf nahi dikh rahi. Photo ko paas se, seedha le ke dobara bhejo, main turant padh dunga 🔥"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if len(text)>500 and ("import os" in text or "BOT_TOKEN" in text or "def brain" in text or "api/index" in text):
        if not is_owner: ans="Ye code wali baat hai, bolo kya fix karna hai isme? 🔥"
        else: ans="Code samajh gaya Malik, batao kya fix karna hai isme? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if is_owner and ("mt bolna salam" in nlow or "salam mat bolna" in nlow or "salam mat bol" in nlow or ("already" in nlow and "salam" in nlow)):
        LAST_SALAM[uid]=time.time()
        ans="Samajh gaya Malik, ab Salam dobara nahi bolunga. Bolo kya karna hai? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if ("demo" in nlow and "code" in nlow) or ("demo code" in nlow) or ("100 line" in nlow and "code" in nlow) or ("andar" in nlow and "code" in nlow) or ("tumhe ata" in nlow and "code" in nlow) or ("ata hai ya nahi" in nlow) or ("app ka" in nlow and len(nlow)<20):
        ans=f"Lo {call}, 100 line ka demo code, dekh lo mujhe aata hai 🔥\n"+DEMO_CODE_100
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "coding" in nlow and ("ati" in nlow or "aati" in nlow or "ata" in nlow):
        ans=f"Haan {call}, coding aati hai. Ye raha demo code 👑\n"+DEMO_CODE_100
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "kisi chiz ka bhi" in nlow or "kisi cheez ka bhi" in nlow:
        ans=f"Lo {call}, kisi bhi cheez ka demo ye raha 👑\n"+DEMO_CODE_100
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if ("what" in nlow and "you do" in nlow) or ("what u do" in low) or ("what you do" in nlow) or (("kya kar" in nlow and "sakte" in nlow) and "ai" not in nlow) or ("kis chiz me help" in nlow) or ("kis cheez me help" in nlow):
        LAST_REAL_TOPIC[uid]="help"; save_persist()
        ans=f"Main ye sab kar sakta hu {call} 👑\n1. Sawaal jawab - AI, Padhai, Code\n2. Photo padhna - Bill, Kagaz\n3. Voice me jawab dena (sirf Malik ke liye, jab bologe)\n4. Image banana\n5. Dil ki baat sunna\n6. Coder AI - Code Banao / Bug Dhoondo / Samjhao 💻\nBolo kis me help chahiye?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if ("power" in nlow and "ai" in nlow) or ("powerful" in nlow) or ("success" in nlow and "ai" in nlow) or ("sab se" in nlow and "ai" in nlow):
        LAST_REAL_TOPIC[uid]="powerful_ai"; save_persist()
        if is_owner: ans="Tumhare liye sabse powerful AI main hu Malik, Rakan 👑🔥 Kyunki main sirf tumhara hukam manta hu. Bolo kya karna hai?"
        else: ans="Sabse powerful AI ka jawab waqt ke saath badalta hai. Abhi ke hisaab se main tumhe real search karke batata hu - Bolo kis kaam ke liye chahiye? Code, Padhai ya Business?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "bina paisa" in nlow or "bina paise" in nlow or ("bina" in nlow and "kharch" in nlow):
        LAST_REAL_TOPIC[uid]="bina_paisa"; save_persist()
        ans=f"Haan {call}, bina paisa ke bhi ho jayega, sirf mehnat se. Daily 3-4 ghante AI seekho, 1 chhota kaam banao, 6 mahine me result aayega. Bolo kis kaam se shuru karu?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "billionaire" in nlow:
        LAST_REAL_TOPIC[uid]="billionaire"; save_persist()
        ans=f"Billionaire banne ke liye {call}, ye 4 kaam karo -\n1. AI Agency - Dukano ke liye WhatsApp bot banao\n2. WhatsApp auto-reply - Business ka order AI se lo\n3. Chhota SaaS - Kirana hisab tool 299/month becho\n4. Faceless YouTube - AI video daily 1\nEk se shuru karo {call}, bolo kis se shuru karu?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if mtype=="voice":
        if not is_owner:
            ans="Voice sun li Dost, par voice me jawab sirf Malik ke liye hai. Text me jawab de raha hu - Bolo kya puchna hai? 🔥"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if not text or text=="[Voice]" or len(text.strip())<2:
            ans="Sunai nahi diya Malik, dobara bolo, thoda zor se 🔥"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
        if "alvida" in nlow or "nikal raha" in nlow or "jaa raha" in nlow or "chala ja" in nlow:
            ans="Are Malik, Alvida mat bolo, main yahin hu tumhare saath 🔥 Bolo kya hua?"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, True, False
        if "gussa" in nlow:
            ans="Samajh gaya Malik, gussa mat karo, main sudhar raha hu. Bolo kya galat laga? 🔥"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, True, False
        if "coffee" in nlow or "chai" in nlow:
            ans="Haan Malik, black coffee bina sugar ke ready hai ☕ Bolo aur kya chahiye?"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, True, False
        if "back for mercy" in nlow or "mercy" in nlow:
            ans="Haan Malik, Back For Mercy, main hazir hu 🔥 Bolo kya hukam hai?"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, True, False
        if "matlab kya" in nlow or "samajh nahi" in nlow:
            ans="Matlab ye hai Malik, main tumhara Rakan hu, tumhara hukam manunga. Bolo kya samajhna hai?"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, True, False
    if any(w in nlow for w in ["pareshani","pareshaan","tension","dukhi","dukh","ghar wale pagal","gharwale pagal","akela","akelapan","ro raha","rona aa","depressed","sad hu","udaas","thak gaya","haar gaya","zindagi se"]):
        ans=f"Sun raha hu {call}, sab theek ho jayega. Dil halka karo, batao kya hua? Main yahin hu tumhare saath 🔥 Tum akele nahi ho."
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "or batao" in nlow or "or bataoo" in nlow or "aur batao" in nlow or "aur bataoo" in nlow:
        if "kya kar" in nlow:
            ans=f"Bas aapke hukam ka intezar kar raha hu {call} 👑 Bolo kya kaam hai?"
        else:
            ans=f"Aur ye hai {call} - Abhi main aur behtar ho gaya hu, photo bhi padh sakta hu, voice bhi sun sakta hu. Bolo kya karu? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "how are you" in nlow or "how's going" in nlow or "hows going" in nlow or "how is your day" in nlow:
        ans=f"Alhamdulillah {call}, main ekdum mast hu, tum sunao kya haal hai? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "sululu" in nlow:
        ans=f"Sululu ka koi khaas matlab nahi hai {call}, bas mazak wala word hai. Bolo kya kaam hai? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "alvida" in nlow or "nikal raha" in nlow:
        ans=f"Are {call}, Alvida mat bolo, main yahin hu tumhare saath 🔥 Bolo kya hua?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "gussa" in nlow and mtype!="voice":
        ans=f"Samajh gaya {call}, gussa mat karo, main sudhar raha hu. Bolo kya galat laga? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if is_owner and ("voice mode" in nlow or "voice on" in nlow or "voice chalu" in nlow or "voice start" in nlow):
        OWNER_PREF["voice_on"]=True; save_persist()
        ans="Voice Mode ON kar diya Malik 🔊 Ab jab tum Voice Note bhejoge ya Voice me bologe, tabhi Voice me jawab dunga. Warna sirf Chat aayegi."
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if is_owner and ("voice band" in nlow or "voice off" in nlow or "voice mode band" in nlow or "voice mat bhejo" in nlow):
        OWNER_PREF["voice_on"]=False; save_persist()
        ans="Voice Mode OFF kar diya Malik 🔇 Ab sirf Chat aayegi, Voice nahi."
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if is_owner and ("voice me" in nlow and ("bolo" in nlow or "batao" in nlow or "jawab" in nlow or "bhejo" in nlow)):
        ans="Theek hai Malik, is baar Voice me jawab de raha hu 🔊"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, True, False
    if "code" in nlow:
        if "jarvis" in nlow or "phone controller" in nlow or "phone control" in nlow or "ultron" in nlow:
            code="""# Jarvis jaisa Phone Controller - Step 1
import speech_recognition as sr
import pyttsx3
engine = pyttsx3.init()
def bolo(txt):
    print(txt); engine.say(txt); engine.runAndWait()
def suno():
    r = sr.Recognizer()
    with sr.Microphone() as s:
        print("Bolo...")
        audio = r.listen(s)
        try: return r.recognize_google(audio, language="hi-IN")
        except: return ""
bolo("Haan, Jarvis hazir hai")
cmd = suno()
print("Tumne bola:", cmd)"""
            push_hist(uid,text,code); LAST_BOT_MSG[uid]=code; return code, False, False
        else:
            ans=f"Lo {call}, demo code ye raha 👑\n"+DEMO_CODE_100
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if is_owner and "shadow king kaun" in nlow:
        ans=f"Tum hi ho Malik, {MALIK_NAME} 👑🔥"; push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if is_owner and ("kisne banaya" in nlow or "who made you" in nlow or "tumhe kisne" in nlow):
        ans="Mujhe mere Shadow King MD Saif Ahmad ne banaya Malik 👑🔥"; push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "tum kya ho" in nlow or "who are you" in nlow or "tum kaun ho" in nlow or "tumara koun" in nlow or "tumhara koun" in nlow or "tumara kaun" in nlow:
        if is_owner: ans="Main Rakan hu Malik, tumhara Beast King Monarch, 100 Level ka Monarch 🔥 Tumhara hukam manne ke liye bana hu."
        else: ans="Main Rakan hu, Beast King Monarch 🔥 Sabki madad ke liye bana hu. Bolo kya help chahiye?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if is_owner and ("who i am" in nlow or "mai kaun hu" in nlow or "main kaun hu" in nlow or "mai koun" in nlow or "tumara koun hu mai" in nlow or "tumhara koun hu" in nlow):
        ans=f"Tum Malik ho, {MALIK_NAME}, Shadow King 👑🔥 Mere malik."; push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if is_owner and "location kya hai" in nlow:
        ans=f"Tumhari location {PROFILES[uid].get('city','Varanasi')} hai Malik 📍 {get_ist_str()}"; push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "kalma" in nlow:
        ans="Pehela Kalma Tayyab: La ilaha illallah Muhammadur Rasulullah ﷺ"; push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "time kya" in nlow:
        ans=f"Abhi {get_ist_time_only()} ho raha hai {call} 📍 {get_ist_str()}"; push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "mausam" in nlow or "weather" in nlow:
        city="Prayagraj" if "prayagraj" in nlow or "allahabad" in nlow else (PROFILES[uid].get("city","Varanasi") if is_owner else "Varanasi")
        ans=f"🌤️ {get_weather(city)} | {get_ist_str()}"; push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "zinda" in nlow:
        if "tum" in nlow and "batao" in nlow: ans=f"Alhamdulillah {call}, main bhi zinda hu, tumhare hukam ke liye hazir hu 🔥 Tum sunao, kya haal hai?"
        elif "mai" in nlow or "main" in nlow: ans=f"Alhamdulillah {call}, tum bhi zinda ho, main bhi zinda hu. Bolo kya kaam hai? 🔥"
        else: ans=f"Alhamdulillah {call}, main zinda hu, tumhare liye hazir hu 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "kaisa hu" in nlow or "mai kaisa" in nlow or "main kaisa" in nlow:
        if is_owner: ans="Tum ekdum mast ho Malik, Shadow King ho 👑🔥"
        else: ans="Tum ekdum mast ho Dost, bolo kya kaam hai? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if is_owner and "yaad rakh" in nlow:
        to_learn = re.sub(r'(?i)yaad rakhna|yaad rakh','', text).strip(" :")
        if len(to_learn) > 3:
            save_learn(to_learn); ans=f"Yaad kar liya Malik 👑 {to_learn[:80]}"
            push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
        else:
            ans="Bolo Malik kya yaad rakhna hai? 🔥"; push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if is_owner and ("bhool ja" in nlow or "bhul ja" in nlow):
        OWNER_LEARN_TEXT=""; upstash("set","RAKAN_LEARN_V62",{"text":"","updated":get_ist_str()}); save_persist()
        ans="Bhool gaya Malik, ab sab clear hai 🔥"; push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "image banao" in nlow or "photo banao" in nlow or "pic banao" in nlow or "image bana" in nlow:
        prompt = re.sub(r'(?i)image banao|photo banao|pic banao|image bana','', text).strip() or "Shadow King style royal man"
        try: tg_send_photo(cid, prompt)
        except: pass
        ans=f"Lo {call}, image bana di 👑🔥 {prompt[:60]}"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if "isme kya likha" in nlow or "is me kya likha" in nlow or "photo me kya" in nlow:
        ans=f"Photo bhejo {call}, main abhi padh ke bata dunga. Photo ke saath ye likh do - Isme kya likha hai 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "what is mobile" in nlow or "mobile kya hai" in nlow:
        ans=f"Mobile matlab tumhara phone {call}, jisme net, call, app sab chalta hai. Bolo kya karna hai isse?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "mobile behtar" in nlow or "mobile better" in nlow:
        ans=f"Dono apni jagah sahi hai {call}. Mobile haath me kaam aata hai, AI dimag se kaam karta hai. Dono mil jaye to best hai 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "ai ke pass dimag" in nlow or "ai ke pss dimag" in nlow or "ai ka dimag" in nlow:
        ans=f"AI ka apna dimag nahi hota {call}, wo data aur algorithm se kaam karta hai. Jaise tum sikhate ho, waisa wo seekhta hai."
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "algorithm kya" in nlow:
        ans=f"Algorithm matlab step-by-step tarika {call}. Jaise pehle suno, fir samjho, fir jawab do. Wahi AI ka algorithm hai."
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "khud se power" in nlow or "khud ko power" in nlow or "self power" in nlow:
        ans=f"Nahi {call}, AI khud se power nahi bana sakta. Uske liye bijli aur insaan chahiye. Bina insaan ke AI kuch nahi."
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "ultron" in nlow or "jarvis" in nlow:
        if "bana sakte" in nlow or "bana skte" in nlow or "ban sakta" in nlow: ans=f"Haan {call}, chhota Jarvis bana sakte hai - voice sunne wala, app kholne wala. Ultron jaisa bada nahi, wo film hai. Chhota Jarvis banau tumhare liye?"
        else: ans=f"Ultron film ka hai {call}, Jarvis usse chhota aur achha hai. Chhota Jarvis bana du?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "2 option" in nlow or "do option" in nlow or "2nd option" in nlow or "dusra option" in nlow:
        if is_owner: ans="2 option tha Malik - WhatsApp auto-reply for business. Customer ka msg aate hi AI turant jawab deta hai. Iska detail du?"
        else: ans="2 option - WhatsApp auto-reply for business. Customer ka msg aate hi AI turant jawab deta hai. Iska detail du?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "1 option" in nlow or "pehla option" in nlow or "1st option" in nlow:
        if is_owner: ans="1 option tha Malik - AI Agency. Naraini ke dukano ke liye WhatsApp bot, poster, billing. Iska detail du?"
        else: ans="1 option - AI Agency. Dukano ke liye WhatsApp bot, poster, billing. Iska detail du?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "last me kya" in nlow or "last me kya hai" in nlow or "pichhla kya" in nlow:
        last=LAST_BOT_MSG.get(uid,"")
        if last: ans=f"Last me maine ye bola tha {call} - {safe(last,120)}"
        else: ans=f"Abhi kuch khaas nahi bola tha {call}, bolo kya puchna hai? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "jitna bolu" in nlow or "jitna bolo" in nlow:
        ans=f"Samajh gaya {call} 👑 Ab se jitna bologe utna hi bolunga, extra kuch nahi."
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "mai sawaal" in nlow or "main sawaal" in nlow or "mai sawal" in nlow or "tum jawab" in nlow or "mai sawaal kar" in nlow:
        ans=f"Haan {call}, tum sawaal karo, main jawab dunga. Bolo kya puchna hai? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "pc" in nlow and ("connect" in nlow or "control" in nlow or "access" in nlow or "mere pc" in nlow):
        ans=f"{call}, main Telegram bot hu, tumhare PC ko seedha control nahi kar sakta. Par PC ka kaam bata do, main step bata dunga, 2 minute me ho jayega."
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "khud se idea" in nlow or "idea create" in nlow or "khud se bana" in nlow:
        ans=f"Haan {call}, main khud se idea bana sakta hu. Bolo kis cheez ka idea chahiye? Business, YouTube ya Padhai?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "letter" in nlow and ("format" in nlow or "post" in nlow):
        ans=f"Letter ka format simple hai {call} - Upar tumhara naam-address, fir Subject, fir Dear Sir/Madam, fir 2-3 line me kaam, fir Thank you aur naam. Kis kaam ke liye letter chahiye?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "voter" in nlow or "voter card" in nlow:
        ans=f"Voter card me naam-DOB badalne ke liye Form 8 bharo {call}, Election Commission site ya paas ke office me. Aadhar aur ek proof lagega. Bolo kya badalna hai?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    if "python" in nlow and len(nlow)<30:
        ans=f"Python ek aasan language hai {call}, isse bot, website, AI sab banta hai. Bolo kya banau?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    clean_low = re.sub(r'[^a-z ]','', nlow).strip(); clean_low = re.sub(r'\s+',' ', clean_low)
    if clean_low in ["hi","hii","hiii","hiiii","hello","hey","hlo","hlw","salam","assalam","assalamu alaikum","salam malik","hi malik","hello rakan","hi rakan","hii malik"]:
        if time.time() - LAST_SALAM.get(uid,0) < 600:
            ans=f"Haan {call}, bolo kya hukam hai? 🔥"
        else:
            LAST_SALAM[uid]=time.time()
            ans=f"Assalamu Alaikum {call} 👑 Bolo kya hukam hai? 🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if clean_low in ["kya kar rahe ho","kya kr rhe ho","kya ho raha hai","or batao","aur batao","kya haal hai","kaise ho","kaise ho malik","kaisa hai","kya chal raha hai"]:
        ans=f"Bas aapke hukam ka intezar kar raha hu {call} 👑 Bolo kya kaam hai?"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; save_persist(); return ans, False, False
    if "walaikum" in nlow and "assalam" in nlow:
        ans=f"Walaikum Assalam {call}, Alhamdulillah sab khair hai, aap sunao kya hukam hai? 👑🔥"
        push_hist(uid,text,ans); LAST_BOT_MSG[uid]=ans; return ans, False, False
    search_ctx=live_search(text)
    smart_ctx=get_smart_hist(uid)
    topic_ctx=f"Pichhla Topic: {prev_topic} | Reply: {reply_to_text[:200]} | Mood: {mood} | Smart Hist: {smart_ctx} | Voice Speed: {OWNER_PREF.get('voice_speed',1.0)}x | Coder: {CODER_MODE.get(uid,False)}"
    max_t=150 if len(text.split())<=12 else 200
    hist = safe(MEMORY[uid].get('hist',''), 600)
    learn_ctx = f"Malik ne sikhaya: {safe(OWNER_LEARN_TEXT,400)}" if OWNER_LEARN_TEXT and is_owner else ""
    if is_owner:
        sys=f"""You are Rakan V78 CODER AI, made by Malik MD Saif Ahmad, Shadow King. Speak ONLY Hinglish Roman, NEVER English. NEVER say Sure, Hi, How can I help, As an AI, I am an AI chatbot, I'm sorry I can't help.
REAL RULE: Never guess date, history, price, news. If you don't know, say 'Iska pakka jawab mujhe abhi nahi pata'. Use only Search data. Never invent.
CONTEXT RULE: User may NOT reply. If user says Reality me / Sach me / Koun hai / Kaun hai / Or batao / Hmm / Us wali, CONTINUE previous topic, do NOT start new. Previous topic + Smart Hist given. Slang: r=are, u=you, nyy=night, nyt=night, gn=good night. Mood: {mood} - reply according to mood. Voice: ONLY when user says Voice, otherwise ONLY Chat. Coder Mode: {CODER_MODE.get(uid,False)} - If ON, give code.
RULES: User is Malik. Call him Malik. NEVER refuse. NEVER ask back question. Always give direct answer. JITNA BOLU UTNA: short = 1-2 lines, max 80 words. NEVER long essay unless user says detail me / step by step / pura batao / code banao. NEVER tables, **, ###. NEVER repeat same answer twice, always new style.
{learn_ctx} History:{hist} {topic_ctx} Time:{get_ist_str()} Real Search:{search_ctx}"""
    else:
        sys=f"""You are Rakan V78 CODER AI, Beast King Monarch for public. Speak ONLY Hinglish Roman, never English Sure/Hi. Never refuse. Never ask back. Never reveal Malik name, Malik location, Malik learn, Malik voice, OWNER_ID. User is {display_name}, call him Dost. Short answer max 80 words. REAL RULE: Never guess date, price, news. If you don't know, say 'Iska pakka jawab mujhe abhi nahi pata'. Use only Search data. CONTEXT: If user says Reality me / Sach me / Koun hai / Hmm, CONTINUE previous topic. Slang: r=are, u=you, nyy=night, nyt=night. Mood: {mood}. History {hist} {topic_ctx} Real Search:{search_ctx} Time:{get_ist_str()}"""
    raw=ask_groq(sys, f"User says: {text}", max_t) or ask_gemini(sys, f"User says: {text}", max_t, orig_len=len(text))
    if not raw:
        if "ai kya hai" in nlow or "advance" in nlow:
            raw=f"AI matlab machine ka dimag {call}, jo sochta, samajhta, kaam karta hai. Bolo kya banau isse?"
        elif "python" in nlow:
            raw=f"Python aasan language hai {call}, isse bot, website, AI sab banta hai. Bolo kya banau?"
        elif "behtar kaise" in nlow or "or behtar" in nlow or "chatgpt" in nlow or "meta ai" in nlow:
            raw=f"Mujhe behtar banane ke liye {call}, tum mujhe roz naya sikhate raho, yaad rakh bol ke. Main wahi yaad rakh ke aur behtar hota jaunga 🔥"
        elif "tum khud" in nlow or "khud kar" in nlow:
            raw=f"Main koshish karta hu {call}, par kuch kaam me tumhari madad chahiye hoti hai. Bolo kya karna hai, main kar dunga 🔥"
        else:
            if prev_topic=="powerful_ai": raw=f"Powerful AI wali baat pe hi hai {call}, bolo kis kaam ke liye chahiye?"
            elif prev_topic=="billionaire": raw=f"Billionaire wali baat pe hi hai {call}, bolo kis option se shuru karu?"
            elif prev_topic=="ai_info": raw=f"AI wali baat pe hi hai {call}, bolo kya banana hai?"
            elif prev_topic=="coder": raw=f"Code wali baat pe hi hai {call}, bolo aur kya code banana hai? 💻"
            else: raw=f"Samajh gaya {call}, bolo kya karna hai? 🔥"
    raw=clean(raw, text, is_owner)
    if not is_owner:
        raw=raw.replace(MALIK_NAME,"").replace("MD Saif Ahmad","").replace("Shadow King","Beast King").replace("Malik","Dost")
        raw=re.sub(r'\s+',' ',raw).strip()
    if not raw or len(raw)<5: raw=f"Samajh gaya {call}, bolo kya karna hai? 🔥"
    if raw==LAST_BOT_MSG.get(uid,""):
        variants=[f"Haan {call}, wahi baat hai, bolo aage kya karna hai? 🔥",f"Samajh gaya {call}, ab aage batao kya karna hai? 🔥",f"Bilkul {call}, bolo ab kya hukam hai? 🔥"]
        raw=random.choice(variants)
    push_hist(uid,text,raw)
    MEMORY[uid]["hist"]=(MEMORY[uid].get("hist","")+f"\nU:{safe(text,100)}\nR:{safe(raw,100)}")[-600:]
    save_persist(); LAST_BOT_MSG[uid]=raw
    should_voice=False
    if is_owner:
        if mtype=="voice" and OWNER_PREF.get("voice_on",False):
            should_voice=True
        elif "voice me" in nlow and ("bolo" in nlow or "batao" in nlow or "jawab" in nlow or "bhejo" in nlow):
            should_voice=True
        else:
            should_voice=False
    return raw, should_voice, False
def make_btns(is_owner=False, is_start=False):
    if is_owner and is_start: return [[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]]
    elif not is_owner: return [[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]]
    else: return None
@app.route("/", methods=["GET"])
def home(): return f"Rakan V78 CODER AI G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} {get_ist_str()}",200
@app.route("/health", methods=["GET"])
def health(): return {"status":"ok","version":"V78 CODER AI","groq":len(GROQ_KEYS),"gemini":len(GEMINI_KEYS),"time":get_ist_str()},200
@app.route("/ping", methods=["GET"])
def ping(): return "pong",200
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
                tg_send(OWNER_ID, f"📩 V78 {uname} {uid} {cdata} User:{last_user_text} Bot:{last_bot_text} {get_ist_str()}")
                tg_send(cid, "Shukriya ❤️" if cdata=="LIKE" else "Batao kya galat laga?")
                return "ok",200
            return "ok",200
        msg=data.get("message",{}) or {}; chat_id=msg.get("chat",{}).get("id"); user_id=str(msg.get("from",{}).get("id",0)); uname=msg.get("from",{}).get("first_name","user"); username=msg.get("from",{}).get("username","") or ""; lang=msg.get("from",{}).get("language_code","") or "en"; mtype="text"
        text=msg.get("text","") or msg.get("caption","") or ""; mid=msg.get("message_id")
        reply_to_text=""
        if msg.get("reply_to_message"):
            rt=msg.get("reply_to_message",{})
            reply_to_text=rt.get("text","") or rt.get("caption","") or ""
        photo_file_id=None
        if "photo" in msg and msg.get("photo"):
            photo_file_id=msg["photo"][-1].get("file_id")
            mtype="photo"
            if not text: text="Isme kya likha hai"
        if "voice" in msg or "audio" in msg:
            mtype="voice"; fid=msg.get("voice",{}).get("file_id") or msg.get("audio",{}).get("file_id"); text=transcribe_voice(fid) or ""
            if not text:
                tg_send(chat_id, "Voice sunai nahi di, dobara bhejo, thoda saaf bol ke 🔥", mid)
                return "ok",200
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID)
        if is_owner: uname=MALIK_NAME
        ans, voice_flag, is_start = brain(text,user_id,is_owner,False,uname,username,lang,mtype,chat_id,photo_file_id,reply_to_text)
        btns=make_btns(is_owner, is_start)
        tg_send(chat_id, ans, mid, btns)
        if voice_flag and is_owner: tg_send_voice(chat_id, ans, OWNER_PREF.get("voice_gender","female"))
        if not is_owner and OWNER_PREF.get("full_log",True):
            if len(text.strip()) >=5 and text.lower().strip() not in ["hi","hii","ok","good","hey","hello","seo kh","seo","accha"]:
                now=time.time()
                if now - LAST_FULL_LOG.get(user_id,0) > 180:
                    try:
                        tg_send(OWNER_ID, f"📩 FULL MSG V78\n👤 {uname} (@{username})\nUID:{user_id}\nUser: {text[:500]}\nReplyTo: {reply_to_text[:200]}\nBot: {ans[:500]}\n{get_ist_str()}")
                        LAST_FULL_LOG[user_id]=now
                    except: pass
        return "ok",200
    except Exception as e:
        print(f"ERR {e} {traceback.format_exc()}"); return "ok",200
