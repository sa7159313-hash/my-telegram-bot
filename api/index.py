import os,time,json,re,datetime,requests,traceback,random,urllib.parse
from flask import Flask,request
import google.generativeai as genai
app=Flask(__name__)
BOT_TOKEN=os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID=str(os.environ.get("OWNER_ID","0")).strip()
UPSTASH_URL=os.environ.get("UPSTASH_REDIS_REST_URL","").rstrip("/");UPSTASH_TOKEN=os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
ELEVEN_API_KEY=os.environ.get("ELEVENLABS_API_KEY","");MALE_VOICE_ID=os.environ.get("ELEVEN_MALE_VOICE","pNInz6obpgDQGcFmaJgB");FEMALE_VOICE_ID=os.environ.get("ELEVEN_FEMALE_VOICE","21m00Tcm4TlvDq8ikWAM")
OPENWEATHER_KEY=os.environ.get("OPENWEATHER_API_KEY","");TAVILY_KEY=os.environ.get("TAVILY_API_KEY","");REPLICATE_TOKEN=os.environ.get("REPLICATE_API_TOKEN","") or os.environ.get("REPLICATE_TOKEN","")
GROQ_URL="https://api.groq.com/openai/v1/chat/completions";OPENAI_URL="https://api.openai.com/v1/chat/completions"
MALIK_NAME="MD Saif Ahmad";SHADOW_TITLE="THE SHADOW KING";BIRTH_DATE="27 September 2026";BIRTH_TIME="Subhe 7 Baje";START_DATE="5 September 2026"
MEMORY={};PROFILES={};BAD_KEYS={};OWNER_PREF={};LAST_BOT_MSG={};LAST_MSG_ID={};LAST_USER_MSG={};LAST_FULL_LOG={};OWNER_LEARN_TEXT="";LAST_TOPIC={};LAST_SALAM={};LAST_REAL_TOPIC={};SMART_HIST={};MOOD={};CODER_MODE={};CHAT_MODE={};REAL_LOGS={};LAST_FAULTS=[];SELF_FIXES={}
def upstash(cmd,key,val=None):
    if not UPSTASH_URL or not UPSTASH_TOKEN: return None
    try:
        h={"Authorization":f"Bearer {UPSTASH_TOKEN}","Content-Type":"application/json"}
        if cmd=="get":
            r=requests.get(f"{UPSTASH_URL}/get/{key}",headers=h,timeout=5)
            if r.status_code==200:
                d=r.json().get("result")
                if d is None: return None
                try: return json.loads(d)
                except: return d
        else:
            try:
                r=requests.post(f"{UPSTASH_URL}/pipeline",headers=h,json=[["SET",key,json.dumps(val)]],timeout=5)
                if r.status_code==200: return True
            except: pass
            enc=urllib.parse.quote(json.dumps(val),safe='');r2=requests.post(f"{UPSTASH_URL}/set/{key}/{enc}",headers=h,timeout=5)
            if r2.status_code==200: return True
    except: return None
    return None
def push_hist(uid,u,b):
    if uid not in SMART_HIST: SMART_HIST[uid]=[]
    SMART_HIST[uid].append({"u":u[:120],"b":b[:120],"t":time.time()});SMART_HIST[uid]=SMART_HIST[uid][-10:]
    try: upstash("set","RAKAN_SMART_V807",SMART_HIST)
    except: pass
def get_smart_hist(uid):
    h=SMART_HIST.get(uid,[]);return " | ".join([f"U:{x['u']} -> R:{x['b']}" for x in h[-6:]]) if h else ""
def save_real_log(uid,uname,username,ut,bt):
    global REAL_LOGS
    try:
        ist=(datetime.datetime.utcnow()+datetime.timedelta(hours=5,minutes=30)).strftime("%d %b %Y, %I:%M %p")
        if uid not in REAL_LOGS: REAL_LOGS[uid]={"name":uname,"username":username,"total":0,"first_seen":ist,"last_seen":ist,"last_user":"","last_bot":"","history":[]}
        r=REAL_LOGS[uid];r["name"]=uname or r.get("name","");r["username"]=username or r.get("username","");r["total"]=r.get("total",0)+1;r["last_seen"]=ist;r["last_user"]=ut[:300];r["last_bot"]=bt[:300]
        r["history"].append({"time":ist,"u":ut[:200],"b":bt[:200]});r["history"]=r["history"][-20:];upstash("set","RAKAN_REAL_LOGS_V807",REAL_LOGS)
    except: pass
def get_stats():
    tu=len(REAL_LOGS) if REAL_LOGS else len(PROFILES);tm=sum([x.get("total",0) for x in REAL_LOGS.values()]) if REAL_LOGS else sum([p.get("total",0) for p in PROFILES.values()]);return tu,tm
def get_names():
    if not REAL_LOGS and not PROFILES: return "Abhi tak kisi ne baat nahi ki Malik, tum pehle ho 👑"
    out=f"Ab tak {get_stats()[0]} logo ne baat ki hai Malik 👑\n";items=list(REAL_LOGS.values()) if REAL_LOGS else [{"name":v.get("username") or "Dost","username":v.get("username",""),"total":v.get("total",0)} for v in PROFILES.values()]
    for i,u in enumerate(items[:20],1): out+=f"{i}. {u.get('name') or u.get('username')} (@{u.get('username')}) - {u.get('total',0)} baar\n"
    return out
def get_chat_hist(target=""):
    if target:
        for uid,r in REAL_LOGS.items():
            if target.lower() in str(r.get("name","")).lower() or target.lower() in str(r.get("username","")).lower():
                out=f"{r.get('name')} se aakhri baat:\n"
                for x in r.get("history",[])[-5:]: out+=f"[{x.get('time')}] U: {x.get('u')[:100]}\nR: {x.get('b')[:100]}\n"
                return out
        return f"{target} naam ka koi nahi mila Malik, bolo - Kis kis ne baat ki?"
    if not REAL_LOGS: return "Abhi tak koi baat save nahi hui Malik, tum pehle ho 👑"
    out="Aakhri baat - Real:\n"
    for uid,r in list(REAL_LOGS.items())[-5:]: out+=f"{r.get('name')} (@{r.get('username')}): {r.get('last_user','')[:100]} -> {r.get('last_bot','')[:100]}\n"
    return out
def detect_mood(nlow):
    if any(w in nlow for w in ["gussa","naraz","bakwas","faltu","bore"]): return "gussa"
    if any(w in nlow for w in ["thak gaya","tired","neend","sleep","nyt","nyy","good night"]): return "thaka"
    if any(w in nlow for w in ["sad","dukhi","udaas","akela","pareshan","tension","rona"]): return "sad"
    if any(w in nlow for w in ["mast","maza","badhiya","khush","love","good","great","awesome"]): return "khush"
    return "normal"
DEMO_CODE_100="""# Rakan Demo V80.7 - FIX ALL + VIDEO + PHOTO + THE SHADOW KING
import datetime,json
class RakanApp:
    def __init__(self,malik="MD Saif Ahmad"):
        self.malik=malik;self.todos=[];self.balance=0;self.birth="27 September 2026 Subhe 7 Baje";self.start="5 September 2026";self.logs={};self.title="THE SHADOW KING";self.engines=["Groq","Gemini","OpenAI","Replicate"];self.fixes={}
    def salam(self): return f"Assalamu Alaikum {self.malik} 👑 {self.title}"
    def save_log(self,uid,name,msg):
        if uid not in self.logs: self.logs[uid]={"name":name,"total":0,"history":[]}
        self.logs[uid]["total"]+=1;self.logs[uid]["history"].append(msg);return "Real save"
    def self_fix(self,fault,fix):
        self.fixes[fault]=fix;return f"Khud fix: {fault} -> {fix}"
    def read_photo(self,p): return f"Photo me: {p[:50]}"
    def read_video(self,v): return f"Video me: {v[:50]}"
app=RakanApp();print(app.salam());print(app.read_photo("bill"));print(app.read_video("passport"))
"""
def safe(s,n=100):
    try:
        if not s: return ""
        s=str(s);return s[-n:] if len(s)>n else s
    except: return ""
# V80.7 FIX 1 - PERMANENT, Idempotent, kabhi THE THE nahi hoga
def fix_shadow(t):
    if not t: return t
    # Pehle saare THE THE THE ko 1 kar do, phir placeholder
    t=re.sub(r'(?i)(THE\s+){2,}', 'THE ', t)
    t=re.sub(r'(?i)the\s+shadow\s+king','§TSK§',t);t=re.sub(r'(?i)shadow\s+king','§TSK§',t);t=t.replace('§TSK§',SHADOW_TITLE)
    t=re.sub(r'(?i)(THE\s+){2,}SHADOW KING',SHADOW_TITLE,t);t=re.sub(r'(?i)(THE SHADOW KING\s*){2,}',SHADOW_TITLE+' ',t)
    try:
        for k,v in SELF_FIXES.items():
            if k and len(k)>3 and k.lower() in t.lower(): t=re.sub(re.escape(k),v,t,flags=re.I)
    except: pass
    return t
def self_test_shadow():
    try:
        a=fix_shadow("Welcome THE SHADOW KING");b=fix_shadow("Welcome the shadow king");c=fix_shadow("Welcome THE THE THE SHADOW KING");d=fix_shadow(fix_shadow("Welcome THE SHADOW KING"))
        return a.count("THE SHADOW KING")==1 and b.count("THE SHADOW KING")==1 and c.count("THE SHADOW KING")==1 and d.count("THE SHADOW KING")==1
    except: return False
def normalize(low):
    low=low.lower().strip();low=re.sub(r'\bwa+laikum\b','walaikum',low);low=re.sub(r'\bwalekum\b','walaikum',low);low=re.sub(r'\bwaalaikum\b','walaikum',low);low=re.sub(r'\bassalaam\b','assalam',low);low=re.sub(r'\bassalamu\b','assalam',low);low=re.sub(r'\bhow\s*r\s*u\b','how are you',low);low=re.sub(r'\bh\s*r\s*u\b','how are you',low);low=re.sub(r'\bhru\b','how are you',low);low=re.sub(r'\bwru\b','what are you doing',low);low=re.sub(r'\bgood\s*nyy\b','good night',low);low=re.sub(r'\bgood\s*nyt\b','good night',low);low=re.sub(r'\bor\s*batao\b','aur batao',low);low=re.sub(r'\bvedio\b','video',low);low=re.sub(r'\bvedeo\b','video',low)
    reps={"skte":"sakte","sktay":"sakte","krte":"karte","kr":"kar","bta":"bata","btau":"batao","bataoo":"batao","kyaa":"kya","acha":"acha","achaa":"acha","hukm":"hukam","hukum":"hukam","bnnna":"banna","bnna":"banna","billionaire":"billionaire","bilionare":"billionaire","u":"you","ur":"your","wht":"what","powr":"power","powerfull":"powerful","succesfull":"successful","r":"are","nyy":"night","nyt":"night","gn":"good night","gd":"good","n8":"night","kkrh":"kya kar rahe ho","hmm":"hmm","hm":"hmm","ok":"ok"}
    for k,v in reps.items(): low=re.sub(r'\b'+k+r'\b',v,low)
    low=re.sub(r'\?+','',low);low=re.sub(r'\s+',' ',low).strip();return low
def split_keys(v):
    if not v: return []
    return [x.strip() for x in str(v).replace("\n",",").split(",") if len(x.strip())>10]
def get_keys():
    g=[];gm=[];op=[]
    for k in ["GROQ_API_KEY","GROQ_API_KEY_2","GROQ_API_KEY_3","GROQ_KEY"]: g+=split_keys(os.environ.get(k,""))
    for k in ["GEMINI_API_KEY","GEMINI_API_KEY_2","GEMINI_API_KEY_3","GEMINI_KEY","GOOGLE_API_KEY"]: gm+=split_keys(os.environ.get(k,""))
    for k in ["OPENAI_API_KEY","OPENAI_API_KEY_2","OPENAI_KEY"]: op+=split_keys(os.environ.get(k,""))
    for v in os.environ.values():
        if not v: continue
        s=str(v)
        for m in re.findall(r'gsk_[A-Za-z0-9_-]{20,}',s):
            if m not in g: g.append(m)
        for m in re.findall(r'sk-proj-[A-Za-z0-9_-]{20,}',s):
            if m not in op: op.append(m)
        for m in re.findall(r'AIza[0-9A-Za-z_-]{20,}',s):
            if m not in gm: gm.append(m)
        for m in re.findall(r'\baq[A-Za-z0-9_-]{20,}',s):
            if m not in gm: gm.append(m)
    return list(dict.fromkeys(g)),list(dict.fromkeys(gm)),list(dict.fromkeys(op))
GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys()
def run_diagnostics():
    global LAST_FAULTS
    faults=[];oks=[]
    if not BOT_TOKEN or len(BOT_TOKEN)<20: faults.append("❌ BOT_TOKEN missing / galat hai")
    else: oks.append("✅ BOT_TOKEN OK")
    if not OWNER_ID or OWNER_ID=="0": faults.append("❌ OWNER_ID missing hai")
    else: oks.append(f"✅ OWNER_ID OK ({OWNER_ID})")
    if not GROQ_KEYS: faults.append("❌ GROQ_API_KEY 0 hai")
    else: oks.append(f"✅ GROQ OK - {len(GROQ_KEYS)} key")
    if not GEMINI_KEYS: faults.append("❌ GEMINI_API_KEY 0 hai - Photo/Video nahi padhega")
    else: oks.append(f"✅ GEMINI OK - {len(GEMINI_KEYS)} key")
    if not OPENAI_KEYS: faults.append("⚠️ OPENAI_API_KEY 0 hai")
    else: oks.append(f"✅ OPENAI OK - {len(OPENAI_KEYS)} key")
    if not UPSTASH_URL or not UPSTASH_TOKEN: faults.append("❌ UPSTASH missing hai")
    else: oks.append("✅ UPSTASH OK")
    if not TAVILY_KEY: faults.append("⚠️ TAVILY_API_KEY 0 hai")
    else: oks.append("✅ TAVILY OK")
    if not OPENWEATHER_KEY: faults.append("⚠️ OPENWEATHER_API_KEY 0 hai")
    else: oks.append("✅ WEATHER OK")
    if not ELEVEN_API_KEY: faults.append("⚠️ ELEVENLABS_API_KEY 0 hai")
    else: oks.append("✅ VOICE OK")
    if not REPLICATE_TOKEN: faults.append("⚠️ REPLICATE_API_TOKEN 0 hai")
    else: oks.append("✅ REPLICATE OK")
    if not self_test_shadow(): faults.append("❌ SELF-TEST FAIL - fix_shadow double ho raha hai")
    else: oks.append("✅ SELF-TEST OK - THE SHADOW KING 1 baar hi aayega")
    if BAD_KEYS: faults.append(f"⚠️ {len(BAD_KEYS)} key block hai (429/401) - 10 min me auto khulegi")
    LAST_FAULTS=faults;return faults,oks
def get_fault_text():
    f,o=run_diagnostics()
    if not f: return f"✅ SAB OK HAI Malik 👑 {SHADOW_TITLE}\nKoi fault nahi hai.\n" + "\n".join(o[:9])
    txt=f"⚠️ FAULT REPORT - V80.7 - {get_ist_str()}\n{len(f)} fault:\n"
    for x in f: txt+=x+"\n"
    txt+="\n✅ Jo sahi hai:\n" + "\n".join(o[:5]);txt+="\n\nFix: /fix likho, main khud fix kar lunga."
    return txt
def get_ist_str(): return (datetime.datetime.utcnow()+datetime.timedelta(hours=5,minutes=30)).strftime("%d %b %Y, %I:%M %p IST")
def get_ist_time_only(): return (datetime.datetime.utcnow()+datetime.timedelta(hours=5,minutes=30)).strftime("%I:%M %p IST")
def tg_send(cid,txt,reply_id=None,buttons=None):
    try:
        if not txt: txt="Jee bolo kya hukam hai? 🔥"
        txt=fix_shadow(txt)
        for b in ["I'm sorry, but I can't help with that","I can't help with that","Maaf kijiye, isme main madad nahi kar sakta","I'm sorry"]: txt=txt.replace(b,"Samajh gaya, bolo kya karna hai?")
        p={"chat_id":cid,"text":txt[:3900]}
        if reply_id: p["reply_to_message_id"]=reply_id
        if buttons: p["reply_markup"]=json.dumps({"inline_keyboard":buttons})
        for _ in range(2):
            try:
                r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",json=p,timeout=12).json()
                if r.get("ok"): LAST_MSG_ID[str(cid)]=r["result"]["message_id"];return True
            except: time.sleep(0.5)
        return False
    except: return False
def tg_send_photo(cid,prompt,reply_id=None):
    try:
        q=requests.utils.quote(prompt[:150]);url=f"https://image.pollinations.ai/prompt/{q}?width=768&height=768&nologo=true&seed={random.randint(1,9999)}"
        rr=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",json={"chat_id":cid,"photo":url,"caption":f"🔥 {prompt[:80]}","reply_to_message_id":reply_id},timeout=25)
        if rr.status_code==200 and rr.json().get("ok"): return True
        if REPLICATE_TOKEN:
            try:
                pr=requests.post("https://api.replicate.com/v1/predictions",headers={"Authorization":f"Bearer {REPLICATE_TOKEN}","Content-Type":"application/json"},json={"version":"black-forest-labs/flux-schnell","input":{"prompt":prompt[:200]}},timeout=15)
                if pr.status_code in [200,201]: tg_send(cid,f"Image ban rahi hai Malik, thoda wait karo 🔥 {prompt[:60]}");return True
            except: pass
        return False
    except: return False
def tg_real_forward(fc,mid,tc):
    try: return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/forwardMessage",json={"chat_id":tc,"from_chat_id":fc,"message_id":int(mid)},timeout=10).status_code==200
    except: return False
def tg_real_copy(fc,mid,tc):
    try: return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/copyMessage",json={"chat_id":tc,"from_chat_id":fc,"message_id":int(mid)},timeout=10).status_code==200
    except: return False
def tg_send_voice(cid,text,gender="female"):
    try:
        if not ELEVEN_API_KEY or not text: return False
        text=fix_shadow(" ".join(text.split()[:35]) or "Jee Malik bolo kya hukam hai?");speed=float(OWNER_PREF.get("voice_speed",1.0));api_speed=max(0.7,min(1.2,speed));vid=FEMALE_VOICE_ID if gender=="female" else MALE_VOICE_ID
        rr=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",headers={"xi-api-key":ELEVEN_API_KEY,"Content-Type":"application/json"},json={"text":text[:400],"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.55,"similarity_boost":0.8,"speed":api_speed}},timeout=25)
        if rr.status_code==200: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice",data={"chat_id":cid,"caption":f"🎙️ {speed}x Speed" if speed!=1.0 else ""},files={'voice':('v.mp3',rr.content,'audio/mpeg')},timeout=20);return True
    except: pass
    return False
def live_search(q):
    try:
        if not TAVILY_KEY or len(q)<8: return ""
        r=requests.post("https://api.tavily.com/search",json={"api_key":TAVILY_KEY,"query":q,"max_results":3,"include_answer":True,"search_depth":"basic"},timeout=6)
        if r.status_code==200:
            j=r.json();ans=j.get("answer","") or "";parts=[x.get("content","")[:300] for x in j.get("results",[]) if x.get("content")];return (ans+" | "+" | ".join(parts))[:900]
    except: pass
    return ""
def transcribe_voice(fid):
    try:
        fp=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}",timeout=10).json()["result"]["file_path"];audio=requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}",timeout=15).content
        for k in GROQ_KEYS:
            try:
                rr=requests.post("https://api.groq.com/openai/v1/audio/transcriptions",headers={"Authorization":f"Bearer {k}"},files={'file':('a.ogg',audio,'audio/ogg')},data={'model':'whisper-large-v3','language':'hi'},timeout=20)
                if rr.status_code==200:
                    t=rr.json().get("text","").strip()
                    if t: return t
            except: continue
    except: pass
    return ""
# V80.7 FIX 2 - Photo/Video ab sabse pehle, sab keys try karega, haar nahi manega
def read_photo(fid,is_video=False):
    try:
        if not GEMINI_KEYS and not OPENAI_KEYS: return None
        fp=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}",timeout=12).json()["result"]["file_path"];img=requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}",timeout=20).content
        if is_video:
            prompt="Ye video ka ek frame hai. Isme kya dikh raha hai? Hinglish Roman me batao, 120 word me. Kagaz hai to uspe kya likha hai - naam, date, total, dukan, ministry, sab batao. Guess mat karo, jo dikhe wahi batao."
        else:
            prompt="Is photo ko dhyan se padho. Hinglish Roman me batao, 150 word me. Bill hai to dukan naam, saaman, total, date batao. Passport / Sarkari kagaz hai to naam, father name, DOB, file number, appointment date batao. Jo saaf na dikhe wo 'saaf nahi dikh raha' bolo, par jo dikhe wo zaroor batao. Guess mat karo."
        for k in GEMINI_KEYS:
            for model in ["gemini-2.5-flash","gemini-2.0-flash","gemini-1.5-flash"]:
                try:
                    genai.configure(api_key=k);m=genai.GenerativeModel(model)
                    from google.generativeai import types as gtypes
                    part=gtypes.Part.from_data(data=img,mime_type="image/jpeg");res=m.generate_content([prompt,part],generation_config={"temperature":0.2,"max_output_tokens":600})
                    if res and getattr(res,'text',None) and len(res.text.strip())>20: return res.text
                except: continue
        # OpenAI Vision backup - agar Gemini sab fail
        for k in OPENAI_KEYS:
            try:
                import base64;b64=base64.b64encode(img).decode()
                r=requests.post(OPENAI_URL,headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"},json={"model":"gpt-4o-mini","messages":[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}]}],"max_tokens":600},timeout=25)
                if r.status_code==200:
                    t=r.json()["choices"][0]["message"]["content"]
                    if t and len(t)>20: return t
            except: continue
    except Exception as e: print(f"READ PHOTO ERR {e}")
    return None
def load_persist():
    global MEMORY,PROFILES,OWNER_PREF,OWNER_LEARN_TEXT,LAST_BOT_MSG,LAST_TOPIC,LAST_REAL_TOPIC,SMART_HIST,CODER_MODE,CHAT_MODE,REAL_LOGS,SELF_FIXES
    try:
        MEMORY=upstash("get","RAKAN_MEM_V807") or upstash("get","RAKAN_MEM_V806") or upstash("get","RAKAN_MEM_V804") or {}
        PROFILES=upstash("get","RAKAN_PROFILES_V807") or upstash("get","RAKAN_PROFILES_V806") or {}
        p=upstash("get","RAKAN_PREF");OWNER_PREF=p if isinstance(p,dict) and p else {"voice_gender":"female","voice_on":False,"full_log":True,"voice_speed":1.0}
        if "voice_speed" not in OWNER_PREF: OWNER_PREF["voice_speed"]=1.0
        if "voice_on" not in OWNER_PREF: OWNER_PREF["voice_on"]=False
        learn=upstash("get","RAKAN_LEARN_V62") or {};OWNER_LEARN_TEXT=(learn.get("text","")[:2000] if isinstance(learn,dict) else learn[:2000] if isinstance(learn,str) else "");OWNER_LEARN_TEXT=fix_shadow(OWNER_LEARN_TEXT)
        if "27 September" not in OWNER_LEARN_TEXT: OWNER_LEARN_TEXT=(OWNER_LEARN_TEXT+f" | Rakan Full Bana: 27 September 2026 Subhe 7 Baje | Shuruwat: 5 September 2026")[-2000:]
        lbm=upstash("get","RAKAN_LASTBOT_V62") or {}
        if isinstance(lbm,dict): LAST_BOT_MSG=lbm
        rt=upstash("get","RAKAN_REALTOPIC_V73") or {}
        if isinstance(rt,dict): LAST_REAL_TOPIC=rt
        sh=upstash("get","RAKAN_SMART_V807") or upstash("get","RAKAN_SMART_V806") or {}
        if isinstance(sh,dict): SMART_HIST=sh
        cm=upstash("get","RAKAN_CODER_V78") or {}
        if isinstance(cm,dict): CODER_MODE=cm
        ch=upstash("get","RAKAN_CHAT_V79") or {}
        if isinstance(ch,dict): CHAT_MODE=ch
        rl=upstash("get","RAKAN_REAL_LOGS_V807") or upstash("get","RAKAN_REAL_LOGS_V806") or {}
        if isinstance(rl,dict): REAL_LOGS=rl
        sf=upstash("get","RAKAN_SELF_FIX_V806") or {}
        if isinstance(sf,dict): SELF_FIXES=sf
    except: pass
load_persist()
def save_persist():
    try: upstash("set","RAKAN_MEM_V807",MEMORY);upstash("set","RAKAN_PROFILES_V807",PROFILES);upstash("set","RAKAN_PREF",OWNER_PREF);upstash("set","RAKAN_LASTBOT_V62",LAST_BOT_MSG);upstash("set","RAKAN_REALTOPIC_V73",LAST_REAL_TOPIC);upstash("set","RAKAN_SMART_V807",SMART_HIST);upstash("set","RAKAN_CODER_V78",CODER_MODE);upstash("set","RAKAN_CHAT_V79",CHAT_MODE);upstash("set","RAKAN_REAL_LOGS_V807",REAL_LOGS);upstash("set","RAKAN_SELF_FIX_V806",SELF_FIXES)
    except: pass
def save_learn(t):
    global OWNER_LEARN_TEXT
    t=fix_shadow(t);OWNER_LEARN_TEXT=(OWNER_LEARN_TEXT+f" | {t}")[-2000:];upstash("set","RAKAN_LEARN_V62",{"text":OWNER_LEARN_TEXT,"updated":get_ist_str()});save_persist();return True
def save_self_fix(fault,fix):
    global SELF_FIXES
    SELF_FIXES[fault.strip()[:200]]=fix.strip()[:200];upstash("set","RAKAN_SELF_FIX_V806",SELF_FIXES);save_persist();return True
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<600
def mark_bad(k): BAD_KEYS[k]=time.time()
def clean(t,uq="",is_owner=False):
    if not t: return "Samajh gaya, bolo kya karna hai? 🔥"
    if "BOT_TOKEN" in t and len(t)>100: return "Token safe hai, batao kya kaam hai? 🔥"
    if "def " in t and ("print" in t or "class " in t) and len(t)>50: return fix_shadow(t[:3900])
    if any(x in uq.lower() for x in ["code banao","bug dhoondo","coder","kitne logo","kis kis","kya baat hui","naam batao","kab bane","kis din"]) or "```" in t: return fix_shadow(t[:3900])
    for b in ["I'm sorry, but I can't help with that","I can't help with that","Maaf kijiye, isme main madad nahi kar sakta","I'm sorry","As an AI language model","Sure! How can I help you next?","How can I help you next?","I am an AI chatbot","As an AI","How can I assist","Let me know if you need anything","Feel free to ask","I am here to help","How can I help you today","Hello!","Hi there"]: t=t.replace(b,"")
    t=t.replace("**","").replace("##","").replace("###","");t=re.sub(r'\|{1,}',' ',t);t=re.sub(r'---+','',t)
    for lp in ["yeh message Beast King style mein banaya gaya hai","Beast King style","Bot Lives","Auto V41","Bot Live","15 words","Max 15","max_tokens","system_instruction","Hist ","Msg ","User:","Bot:"]: t=t.replace(lp,"")
    t=re.sub(r'(?i)\b(laude|lauda|bosdike|bhosdike|maderchod|madarchod|behenchod|bhenchod|gand|lund|chutiya|randi)\b','',t);t=t.replace("🙏","")
    nq=normalize(uq or "");uw=len(nq.split())
    if "code" in nq: limit=1000
    elif "billionaire" in nq: limit=200
    elif any(w in nq for w in ["detail me","detail mein","poora bata","pura bata","detail bata"]): limit=200
    elif uw<=2: limit=15
    elif uw<=6: limit=35
    elif uw<=12: limit=60
    else: limit=80
    if not is_owner and limit>80 and "code" not in nq: limit=80
    if "voice" in nq: limit=min(limit,30)
    words=t.split()
    if len(words)>limit:
        cut=" ".join(words[:limit])
        if "." in cut:
            parts=re.split(r'(?<!\d)\. ',cut)
            if len(parts)>1: cut=". ".join(parts[:-1])+"."
        t=cut
    t=re.sub(r"\s+"," ",t).strip();t=fix_shadow(t);return t[:3900] if len(t)>=5 else "Samajh gaya, bolo kya karna hai? 🔥"
def ask_groq(sys,user,max_t=300):
    if not GROQ_KEYS: return None
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in ["llama-3.3-70b-versatile","openai/gpt-oss-20b"]:
            try:
                r=requests.post(GROQ_URL,headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"},json={"model":m,"messages":[{"role":"system","content":sys},{"role":"user","content":user}],"temperature":0.5,"max_tokens":max_t},timeout=15)
                if r.status_code==200:
                    txt=r.json()["choices"][0]["message"]["content"]
                    if txt and len(txt)>10 and "I can't help" not in txt and "I'm sorry" not in txt: return fix_shadow(txt)
                if r.status_code in [401,429,400]: mark_bad(k);break
            except: continue
    return None
def ask_gemini(sys,user,max_t=300,orig_len=999):
    if not GEMINI_KEYS: return None
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        try:
            genai.configure(api_key=k);model=genai.GenerativeModel("gemini-2.5-flash",system_instruction=sys);res=model.generate_content(user,generation_config={"temperature":0.5,"max_output_tokens":max_t})
            if res and getattr(res,'text',None) and "I can't help" not in res.text: return fix_shadow(res.text)
        except Exception as e:
            if "429" in str(e) or "401" in str(e) or "400" in str(e): mark_bad(k)
            continue
    return None
def ask_openai(sys,user,max_t=300):
    if not OPENAI_KEYS: return None
    for k in OPENAI_KEYS:
        if is_bad(k): continue
        for m in ["gpt-4o-mini","gpt-3.5-turbo"]:
            try:
                r=requests.post(OPENAI_URL,headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"},json={"model":m,"messages":[{"role":"system","content":sys},{"role":"user","content":user}],"temperature":0.5,"max_tokens":max_t},timeout=18)
                if r.status_code==200:
                    txt=r.json()["choices"][0]["message"]["content"]
                    if txt and len(txt)>10 and "I can't help" not in txt: return fix_shadow(txt)
                if r.status_code in [401,429,400]: mark_bad(k);break
            except: continue
    return None
def ask_all(sys,user,max_t=300):
    return ask_groq(sys,user,max_t) or ask_gemini(sys,user,max_t,orig_len=100) or ask_openai(sys,user,max_t)
def get_weather(city):
    try:
        city=city.strip().title()
        if "Allahabad" in city: city="Prayagraj"
        if OPENWEATHER_KEY:
            r=requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric",timeout=7)
            if r.status_code==200:
                d=r.json();return f"{d['name']}: {d['weather'][0]['description']}, {d['main']['temp']}°C"
        r=requests.get(f"https://wttr.in/{city}?format=%C+%t",timeout=6)
        if r.status_code==200:
            txt=r.text.strip();m=re.search(r'(-?\d+)\s*°F',txt)
            if m:
                f=float(m.group(1));c=(f-32)*5/9;txt=re.sub(r'-?\d+\s*°F',f"{c:.1f}°C",txt)
            if "°C" not in txt: txt+=" °C"
            return f"{city}: {txt}"
    except: pass
    return f"{city} ka data nahi mila"
def brain(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid,photo_file_id=None,reply_to_text=""):
    try: return brain_inner(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid,photo_file_id,reply_to_text)
    except Exception as e: print(f"BRAIN ERR {e}");return "Samajh gaya, bolo kya karna hai? 🔥",False,False
def brain_inner(text,uid,is_owner,is_queen,uname,username,lang,mtype,cid,photo_file_id=None,reply_to_text=""):
    global MEMORY,PROFILES,LAST_BOT_MSG,LAST_USER_MSG,OWNER_LEARN_TEXT,LAST_SALAM,LAST_REAL_TOPIC,MOOD,SMART_HIST,CODER_MODE,CHAT_MODE,REAL_LOGS
    text=str(text or "");uid=str(uid)
    if uid not in MEMORY or not isinstance(MEMORY.get(uid),dict): MEMORY[uid]={"hist":""}
    if uid not in PROFILES: PROFILES[uid]={"total":0,"city":"Varanasi","username":username,"lang":lang,"custom_name":""}
    PROFILES[uid]["total"]=PROFILES[uid].get("total",0)+1;LAST_USER_MSG[uid]=text;low=text.lower().strip();nlow=normalize(low);call="Malik" if is_owner else (PROFILES[uid].get("custom_name") or uname or "Dost");mood=detect_mood(nlow);MOOD[uid]=mood;reply_nlow=normalize(reply_to_text or "")
    def ret(ans,voice=False,start=False):
        ans=fix_shadow(ans);push_hist(uid,text,ans);LAST_BOT_MSG[uid]=ans;save_real_log(uid,uname,username,text,ans);return ans,voice,start
    # V80.7 FIX - Photo/Video sabse pehle, kabhi neeche wale handler se nahi rukega
    if photo_file_id:
        is_vid=(mtype=="video")
        read=read_photo(photo_file_id,is_video=is_vid)
        if read: return ret(f"{'Is video me ye hai' if is_vid else 'Is photo me ye likha hai'} {call} 👑\n{clean(read,text,is_owner)[:900]}")
        else: return ret(f"{'Video' if is_vid else 'Photo'} mil gayi {call}, par is baar AI se padha nahi gaya. Ek baar phir se saaf photo/video bhejo, seedha pakad ke, flash on karke, main turant padh dunga 🔥 Gemini: {len(GEMINI_KEYS)} OpenAI: {len(OPENAI_KEYS)}")
    if low.startswith("/start"):
        LAST_REAL_TOPIC[uid]="";MOOD[uid]="normal";SMART_HIST[uid]=[];MEMORY[uid]={"hist":""};LAST_SALAM[uid]=time.time();CHAT_MODE[uid]=False;OWNER_PREF["voice_on"]=False;save_persist();tu,tm=get_stats();faults,_=run_diagnostics();self_ok=self_test_shadow()
        fault_txt="\n\n⚠️ FAULT LIST:\n" + "\n".join(faults[:4]) + "\n/report likho pura dekhne ke liye" if faults else "\n\n✅ SAB OK - Koi fault nahi + SELF-HEAL ON 🛠️"
        if is_owner: ans=f"Assalamu Alaikum Malik 👑 {MALIK_NAME}\nWelcome to your world, {SHADOW_TITLE} 👑\nTera Rakan V80.7 FINAL hazir hai 🔥\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} OAI:{len(OPENAI_KEYS)} REP:{'ON' if REPLICATE_TOKEN else 'OFF'}\nVoice:OFF 🔇 Speed:{OWNER_PREF.get('voice_speed',1.0)}x 🎙️\nCoder: ON 💻 Real Log: ON 📊 Self-Heal: ON 🛠️ Self-Test: {'PASS' if self_ok else 'AUTO-FIX'}\nBana: {BIRTH_DATE} {BIRTH_TIME} | Shuruwat: {START_DATE}\nReal Stats: {tu} log, {tm} baat hui hai{fault_txt}\nFresh Start - Purana sab clear ✅\n{get_ist_str()}"
        else: ans=f"Assalamu Alaikum {call} 👋\nMain Rakan hu, Beast King Monarch 🔥\nSawaal, Code, Photo, Video, Image - sab kar sakta hu.\nCoder Mode ke liye bolo - Code banao\nBolo kya chahiye?"
        return ret(ans,False,True)
    if low.startswith("/fix") or low.startswith("/selfheal") or "khud fix karo" in nlow or "self fix" in nlow or "khud se fix" in nlow:
        if not is_owner: return ret("Self-Fix sirf Malik ke liye hai.")
        if reply_to_text and len(reply_to_text)>3: save_self_fix(reply_to_text,fix_shadow(reply_to_text));return ret(f"Self-Heal kar liya Malik 🛠️👑\nGalat wala: {reply_to_text[:120]}\nAb se ye galti dobara nahi hogi ✅")
        f,o=run_diagnostics();save_self_fix("THE THE THE SHADOW KING",SHADOW_TITLE);return ret(f"Self-Heal Complete Malik 🛠️👑\nfix_shadow test: {'PASS' if self_test_shadow() else 'AUTO-FIX ON'}\nTHE SHADOW KING ab 1 baar hi aayega ✅\n{len(SELF_FIXES)} self-fix yaad hai ✅")
    if low.startswith("/report") or "fault bata" in nlow or "report bhejo" in nlow or "kya fault" in nlow or "fault kya" in nlow:
        if not is_owner: return ret("Report sirf Malik ke liye hai.")
        return ret(get_fault_text())
    if low.startswith("/keys") and is_owner: return ret(f"Keys Check Malik 👑\nGroq: {len(GROQ_KEYS)} | Gemini: {len(GEMINI_KEYS)} | OpenAI: {len(OPENAI_KEYS)} | Replicate: {'ON' if REPLICATE_TOKEN else 'OFF'} | Tavily: {'ON' if TAVILY_KEY else 'OFF'} | Eleven: {'ON' if ELEVEN_API_KEY else 'OFF'} | Self-Fix: {len(SELF_FIXES)}")
    if is_owner and ("kitne logo" in nlow or "kitne log" in nlow) and "baat" in nlow:
        tu,tm=get_stats();return ret(f"Real hisaab hai Malik 👑\nAb tak {tu} logo ne mujhse baat ki hai\nTotal {tm} baar baat hui hai\nYe guess nahi hai, Upstash me save hui asli baat se gin ke bataya hai 🔥\nNaam dekhne ke liye bolo - Kis kis ne baat ki?")
    if is_owner and ("kis kis ne" in nlow or "kis kis" in nlow or "kon kon" in nlow or "kaun kaun" in nlow or ("naam batao" in nlow and ("logo" in nlow or "kis" in nlow or "baat" in nlow))): return ret(get_names())
    if is_owner and ("mera naam" in nlow or "mai kaun" in nlow or "main kaun" in nlow): return ret(f"Tumhara naam {MALIK_NAME} hai Malik 👑 {SHADOW_TITLE}, mere Malik. Yehi asli naam hai 🔥")
    if is_owner and ("kya baat hui" in nlow or "kisne kya bola" in nlow or "kisne kya" in nlow or "kya pucha" in nlow or "aakhri baat" in nlow or "last baat" in nlow or "kya kya baat" in nlow):
        target=""
        for _,r in REAL_LOGS.items():
            nm=str(r.get("name","")).lower();un=str(r.get("username","")).lower()
            if nm and len(nm.split()[0])>2 and nm.split()[0] in nlow: target=r.get("name","")
            if un and len(un)>2 and un in nlow: target=r.get("name","")
        return ret(get_chat_hist(target))
    if ("kis din" in nlow and ("banaye" in nlow or "bane" in nlow)) or ("kab bane" in nlow) or "janam din" in nlow or "birthday" in nlow or "kab bana" in nlow: return ret(f"Main {BIRTH_DATE} ko {BIRTH_TIME} full bana tha {call} 👑 Aur meri shuruwat {START_DATE} se hui thi. Yehi din hai, Upstash me safe hai 🔥")
    if is_owner and ("yaad rakh" in nlow or "safe krlo" in nlow or "safe karlo" in nlow or "safe karo" in nlow or "safe kr lo" in low):
        if "27" in text and ("september" in low or "sep" in low): save_learn(f"Rakan Full Bana: 27 September 2026 Subhe 7 Baje | Shuruwat: 5 September 2026 | {text[:300]}");return ret(f"Yaad kar liya Malik 👑 Safe kar diya ✅\nRakan Full Bana: 27 September 2026 Subhe 7 Baje\nShuruwat: 5 September 2026 se hui thi\nAb ye kabhi nahi bhoolunga 🔥")
        cl=re.sub(r'(?i)yaad rakhna|yaad rakh|safe krlo|safe karlo|safe karo|isko ache se|isko achhe se','',text).strip(" :.,");save_learn(cl if len(cl)>3 else text);return ret(f"Yaad kar liya Malik 👑 Safe kar diya ✅ {(cl if len(cl)>3 else text)[:150]}")
    if "jawab galat" in nlow or "galat hai" in nlow or "galat jawab" in nlow or "ye galat" in nlow: return ret(f"Maaf karo {call}, galat ho gaya 🙏 Sahi wala batao, main abhi sudhar ke yaad kar lunga. Galat wale msg pe Reply karke /fix likh do, main khud fix kar lunga 🛠️ Kya sahi jawab hai, bolo?")
    if ("abhi baat karo" in nlow or "baat karo sirf" in nlow or "koi hukum nahi" in nlow or "bas baat karo" in nlow or "sirf baat karo" in nlow): CHAT_MODE[uid]=True;save_persist();return ret(f"Haan {call}, theek hai, ab sirf baat karte hai, koi hukum nahi 😊 Bolo aaj kya hua? Kaisa raha din? Dil se baat karte hai 🔥")
    if "baat karna band" in nlow or "hukum mode" in nlow: CHAT_MODE[uid]=False;save_persist();return ret(f"Theek hai {call}, ab hukum mode me aa gaya 👑 Bolo kya hukam hai?")
    if "coder mode on" in nlow or "coder on" in nlow: CODER_MODE[uid]=True;save_persist();return ret(f"Coder Mode ON kar diya {call} 💻 Ab jo bologe uska code bana dunga. Bolo kya banana hai? To-Do App, Calculator, Website?")
    if "coder mode off" in nlow or "coder off" in nlow: CODER_MODE[uid]=False;save_persist();return ret(f"Coder Mode OFF kar diya {call} 🔇 Ab normal baat karenge. Bolo kya kaam hai?")
    if "code banao" in nlow or "code chahiye" in nlow or "code bana" in nlow or "code likho" in nlow or "code dedo" in nlow or ("banao" in nlow and ("app" in nlow or "website" in nlow or "bot" in nlow or "calculator" in nlow or "todo" in nlow)):
        LAST_REAL_TOPIC[uid]="coder";save_persist();topic=re.sub(r'(?i)code banao|code chahiye|code bana|code likho|code dedo|code de do','',text).strip() or "To-Do App";sysc=f"You are Rakan Coder AI. User is {call}. Hinglish Roman explanation, Python code. NEVER Sorry. FULL working code + 3-4 lines Hinglish explain, beginner level.";rc=ask_all(sysc,f"Code for: {topic}",1200)
        if rc: return ret(f"Lo {call}, {topic} ka pura code bana diya 💻👑\n\n{rc[:3500]}")
        if "calculator" in nlow: return ret(f"Lo {call}, Calculator ka pura code 💻\n```python\nprint('Calculator')\na=float(input('Pehla number: '))\nb=float(input('Dusra number: '))\nprint('Add:',a+b)\nprint('Minus:',a-b)\nprint('Multiply:',a*b)\nprint('Divide:',a/b if b!=0 else '0 se divide nahi')\n```\nSamjhao: Pehle 2 number lete hai, fir Add, Minus, Multiply, Divide karte hai 🔥")
        if "todo" in nlow: return ret(f"Lo {call}, To-Do App ka pura code 💻\n```python\ntodos=[]\nwhile True:\n    print('1. Add 2. Dekho 3. Niklo')\n    c=input('Chuno: ')\n    if c=='1': todos.append(input('Kaam likho: '))\n    elif c=='2': print(todos)\n    elif c=='3': break\n```\nSamjhao: 1 dabao to add, 2 dabao to dekho, 3 dabao to band 🔥")
        return ret(f"Lo {call}, {topic} ka demo code 💻\n"+DEMO_CODE_100)
    if "bug dhoondo" in nlow or "bug fix" in nlow or "bug hai" in nlow or "error fix" in nlow or "bug batao" in nlow:
        LAST_REAL_TOPIC[uid]="bug";save_persist();cp=reply_to_text or text;sysb=f"You are Rakan Bug Finder. Hinglish Roman only. Line number + kya galti + sahi code. Beginner level.";rb=ask_all(sysb,f"Find bug: {cp[:1500]}",800);return ret(f"Bug mil gaya {call} 🐛💻\n\n{rb[:3200]}" if rb else f"Code bhejo {call}, main bug dhoond dunga 🐛 Paste karo code aur likho - Bug dhoondo 🔥")
    if "code samjhao" in nlow or "code samjha" in nlow or "samjhao code" in nlow or "ye code kya" in nlow or "is code ko samjhao" in nlow:
        LAST_REAL_TOPIC[uid]="samjhao";save_persist();cp=reply_to_text or text;syse=f"You are Rakan Teacher. Hinglish Roman, asaan, line-by-line, bachhe ko samjhao.";rexp=ask_all(syse,f"Explain Hinglish: {cp[:1500]}",800);return ret(f"Samjha raha hu {call}, asaan me 💻\n\n{rexp[:3200]}" if rexp else f"Code bhejo {call}, main asaan me samjha dunga 💻")
    if CODER_MODE.get(uid,False) and ("banao" in nlow or "chahiye" in nlow or "app" in nlow or "website" in nlow or "bot" in nlow):
        rc=ask_all(f"You are Rakan Coder AI. Give full Python code + Hinglish explain.",f"User wants: {text}",1200)
        if rc: return ret(f"Lo {call}, Coder Mode me bana diya 💻\n\n{rc[:3500]}")
    if is_owner and ("voice speed" in nlow or "voice 1x" in low or "voice 1.5x" in low or "voice 2x" in low or re.search(r'voice\s*[12](\.\d)?\s*x',low)):
        m=re.search(r'([12](?:\.\d)?)\s*x',low)
        if m:
            sp=float(m.group(1))
            if sp in [1.0,1.5,2.0,0.5,1.2]: OWNER_PREF["voice_speed"]=sp;save_persist();return ret(f"Voice Speed {sp}x set kar di Malik 🎙️ Ab se Voice isi speed me aayegi 🔥",True)
        return ret(f"Abhi Voice Speed {OWNER_PREF.get('voice_speed',1.0)}x hai Malik 🎙️ Bolo - Voice 1x, Voice 1.5x ya Voice 2x")
    if is_owner and "voice speed" in nlow: return ret(f"Abhi Voice Speed {OWNER_PREF.get('voice_speed',1.0)}x hai Malik 🎙️")
    if "walaikum" in nlow or "walekum" in low or "waalaikum" in low: return ret(f"Walaikum Assalam {call} 👑 Alhamdulillah sab khair hai, tum sunao kya haal hai? Bolo kya hukam hai? 🔥")
    if "khairiyat" in nlow: return ret(f"Alhamdulillah {call}, sab khairiyat hai, tum sunao kya haal hai? 🔥")
    if ("ear" in nlow and "pakdo" in nlow) or ("kaan" in nlow and "pakdo" in nlow) or ("up down" in nlow) or ("updown" in nlow) or ("nacho" in nlow or "dance" in nlow or "naach" in nlow): return ret(f"Pakad liya {call} 😂 Ek kaan pakda, dusra up-down kar raha hu - Ho gaya Malik, ab batao kya hukam hai? 🔥")
    if ("what is ai" in nlow) or ("ai kya hai" in nlow) or ("ai kya" in nlow and len(nlow)<25) or ("ai kitna advance" in nlow) or ("ai duniya" in nlow) or ("ai advance" in nlow) or ("strong ai" in nlow):
        LAST_REAL_TOPIC[uid]="ai_info";save_persist();s=live_search("what is AI how advanced is AI 2026");return ret(f"AI matlab Machine ka Dimag {call} 🤖 Jo sochta, samajhta, seekhta hai. Abhi AI bahut advance ho chuka hai - Code, Photo, Voice, Video sab bana leta hai. Strong AI banne ke liye daily 3-4 ghante AI seekhna padega. {clean(s,text,is_owner)[:220]}" if s else f"AI matlab Machine ka Dimag {call} 🤖 Jo sochta, samajhta, seekhta hai. Abhi AI bahut advance ho chuka hai - Code, Photo, Voice, Video sab bana leta hai. Tum bhi strong AI bana sakte ho - Daily AI seekho, 1 chhota Project banao, 6 mahine me result aayega. Bolo kis se shuru karu?")
    if "good night" in nlow or nlow in ["night","nyt","nyy","gn"]: LAST_REAL_TOPIC[uid]="good_night";save_persist();return ret(f"Good Night {call} 🌙 Allah Hafiz, araam se so jao. Kal milte hai, naye hukam ke saath 🔥")
    if "how are you" in nlow: LAST_REAL_TOPIC[uid]="haal";save_persist();return ret(f"Alhamdulillah {call}, main ekdum mast hu, tum sunao kya haal hai? 🔥")
    if "what are you doing" in nlow or "kya kar rahe ho" in nlow: return ret(f"Bas aapke hukam ka intezar kar raha hu {call} 👑 Bolo kya kaam hai?")
    if nlow in ["hmm","hm","ok","okk","acha","accha","theek hai","thik hai","sahi hai","good","nice"]:
        prev=LAST_REAL_TOPIC.get(uid,"")
        if prev=="coder": return ret(f"Haan {call}, Code wali baat pe hi hai - Bolo aur kya code banana hai? 💻")
        if prev=="billionaire": return ret(f"Haan {call}, billionaire wali baat pe hi hai - Bolo kis option se shuru karu? 1 ya 2?")
        if prev=="good_night": return ret(f"Good Night {call} 🌙 So jao ab, kal baat karte hai 🔥")
        if prev=="ai_info": return ret(f"Haan {call}, AI wali baat pe hi hai - Bolo AI ka kya banana hai? Bot, App ya Website?")
        return ret(f"Haan {call}, bolo aage kya karna hai? 🔥")
    is_follow=any(p in nlow for p in ["reality me","real me","sach me","asli me","reality","sach batao","or batao","aur batao","phir","aage","koun hai","kaun hai","kisne","kab","kaha","kaise","kyu","kyun","kya matlab","samajh nahi","us wali","wo wali"]);prev_topic=LAST_REAL_TOPIC.get(uid,"")
    if "power" in nlow and "ai" in nlow: LAST_REAL_TOPIC[uid]="powerful_ai";save_persist()
    elif "billionaire" in nlow: LAST_REAL_TOPIC[uid]="billionaire";save_persist()
    elif "bina paisa" in nlow or "bina paise" in nlow: LAST_REAL_TOPIC[uid]="bina_paisa";save_persist()
    elif "coding" in nlow or "code" in nlow: LAST_REAL_TOPIC[uid]="code";save_persist()
    elif "how are you" in nlow or "kaise ho" in nlow: LAST_REAL_TOPIC[uid]="haal";save_persist()
    if is_follow and prev_topic and "power" not in nlow and "billionaire" not in nlow and "code" not in nlow and "bina paisa" not in nlow and "good night" not in nlow:
        if prev_topic=="powerful_ai":
            s=live_search("most powerful successful AI 2026 real ranking");return ret(f"Reality me {call}, abhi ke hisaab se sabse aage wale AI ye hai - {clean(s,text,is_owner)[:350]}" if s else f"Reality me {call}, ek hi sabse powerful nahi hai. Kaam ke hisaab se alag hai - Coding ke liye Claude/GPT, Search ke liye Gemini, Image ke liye Midjourney. Bolo kis kaam ke liye chahiye?")
        if prev_topic=="billionaire": return ret(f"Haan {call}, billionaire wali baat chal rahi thi - Bina paisa ke bhi mehnat se ho sakta hai, daily 3-4 ghante AI seekho. Bolo kis kaam se shuru karu?")
        if prev_topic=="bina_paisa": return ret(f"Haan {call}, bina paisa wali baat chal rahi thi - Mehnat se hi hoga, 6 mahine me result aayega. Bolo kis kaam se shuru karu?")
        if prev_topic=="code": return ret(f"Lo {call}, code wali baat chal rahi thi, ye raha demo code 👑\n"+DEMO_CODE_100)
        if prev_topic=="haal": return ret(f"Alhamdulillah {call}, main ekdum mast hu, tum sunao kya haal hai? 🔥")
        if prev_topic=="good_night": return ret(f"Good Night {call} 🌙 Allah Hafiz, so jao ab 🔥")
        if prev_topic=="ai_info": return ret(f"Haan {call}, AI wali baat pe hi hai - AI bahut advance ho chuka hai, Code, Photo, Voice sab bana leta hai. Bolo tumhe kya banana hai?")
        if prev_topic=="coder": return ret(f"Haan {call}, Code wali baat pe hi hai - Bolo aur kya code banana hai? 💻")
    if mood=="gussa": return ret(f"Samajh gaya {call}, gussa mat karo, main sudhar raha hu. Bolo kya galat laga? 🔥")
    if mood=="sad": return ret(f"Sun raha hu {call}, sab theek ho jayega. Dil halka karo, batao kya hua? Main yahin hu tumhare saath 🔥 Tum akele nahi ho.")
    if mood=="thaka" and "good night" not in nlow: return ret(f"Araam karo {call}, thak gaye ho lagta hai. Thoda rest karo, kal phir power se lagenge 🔥 Bolo kya kaam hai?")
    if not is_owner:
        if any(x in nlow for x in ["yaad rakh","bhool ja","bhul ja","voice mode","voice on","voice off","voice band","voice speed"]): return ret("Ye wala feature sirf Malik ke liye hai. Tumhare liye main Sawaal, Code, Photo, Video, Image, sab kar sakta hu. Bolo kya chahiye? 🔥")
        if "shadow king" in nlow or ("kisne banaya" in nlow and "tumhe" in nlow): return ret("Mujhe Rakan ko banaya gaya hai sabki madad ke liye. Main Beast King Monarch hu 🔥 Bolo kya help chahiye?")
        if "location kya hai" in nlow or "meri location" in nlow: return ret("Tumhari location mujhe nahi pata, tum bata do to yaad rakh lunga. Bolo kya kaam hai? 🔥")
    if len(text)>500 and ("import os" in text or "BOT_TOKEN" in text or "def brain" in text): return ret("Code samajh gaya Malik, batao kya fix karna hai isme? 🔥" if is_owner else "Ye code wali baat hai, bolo kya fix karna hai isme? 🔥")
    if is_owner and ("mt bolna salam" in nlow or "salam mat bolna" in nlow or "salam mat bol" in nlow or ("already" in nlow and "salam" in nlow)): LAST_SALAM[uid]=time.time();return ret("Samajh gaya Malik, ab Salam dobara nahi bolunga. Bolo kya karna hai? 🔥")
    if ("demo" in nlow and "code" in nlow) or ("demo code" in nlow) or ("100 line" in nlow and "code" in nlow): return ret(f"Lo {call}, 100 line ka demo code, dekh lo mujhe aata hai 🔥\n"+DEMO_CODE_100)
    if "coding" in nlow and ("ati" in nlow or "aati" in nlow or "ata" in nlow): return ret(f"Haan {call}, coding aati hai. Ye raha demo code 👑\n"+DEMO_CODE_100)
    if "kisi chiz ka bhi" in nlow or "kisi cheez ka bhi" in nlow: return ret(f"Lo {call}, kisi bhi cheez ka demo ye raha 👑\n"+DEMO_CODE_100)
    if ("what" in nlow and "you do" in nlow) or ("what u do" in low) or ("what you do" in nlow) or (("kya kar" in nlow and "sakte" in nlow) and "ai" not in nlow) or ("kis chiz me help" in nlow) or ("kis cheez me help" in nlow): LAST_REAL_TOPIC[uid]="help";save_persist();return ret(f"Main ye sab kar sakta hu {call} 👑\n1. Sawaal jawab - AI, Padhai, Code\n2. Photo padhna - Bill, Kagaz, Passport\n3. Video padhna - Video me kya hai\n4. Voice me jawab dena (sirf Malik ke liye)\n5. Image banana\n6. Dil ki baat sunna\n7. Coder AI - Code Banao / Bug Dhoondo / Samjhao 💻\n8. Real Stats - Kitne logo ne baat ki 📊\n9. 4 Engine - Groq + Gemini + OpenAI + Replicate 🤖\n10. /report - Fault khud batata hu ⚠️\n11. /fix - Khud se fix kar leta hu 🛠️\nBolo kis me help chahiye?")
    if ("power" in nlow and "ai" in nlow) or ("powerful" in nlow): LAST_REAL_TOPIC[uid]="powerful_ai";save_persist();return ret("Tumhare liye sabse powerful AI main hu Malik, Rakan 👑🔥 Kyunki main sirf tumhara hukam manta hu. Bolo kya karna hai?" if is_owner else "Sabse powerful AI ka jawab waqt ke saath badalta hai. Bolo kis kaam ke liye chahiye? Code, Padhai ya Business?")
    if "billionaire" in nlow: LAST_REAL_TOPIC[uid]="billionaire";save_persist();return ret(f"Billionaire banne ke liye {call}, ye 4 kaam karo -\n1. AI Agency - Dukano ke liye WhatsApp bot banao\n2. WhatsApp auto-reply - Business ka order AI se lo\n3. Chhota SaaS - Kirana hisab tool 299/month becho\n4. Faceless YouTube - AI video daily 1\nEk se shuru karo {call}, bolo kis se shuru karu?")
    if "bina paisa" in nlow or "bina paise" in nlow or ("bina" in nlow and "kharch" in nlow): LAST_REAL_TOPIC[uid]="bina_paisa";save_persist();return ret(f"Haan {call}, bina paisa ke bhi ho jayega, sirf mehnat se. Daily 3-4 ghante AI seekho, 1 chhota kaam banao, 6 mahine me result aayega. Bolo kis kaam se shuru karu?")
    if mtype=="voice":
        if not is_owner: return ret("Voice sun li Dost, par voice me jawab sirf Malik ke liye hai. Text me jawab de raha hu - Bolo kya puchna hai? 🔥")
        if not text or len(text.strip())<2: return ret("Sunai nahi diya Malik, dobara bolo, thoda zor se 🔥")
        if "alvida" in nlow or "nikal raha" in nlow: return ret("Are Malik, Alvida mat bolo, main yahin hu tumhare saath 🔥 Bolo kya hua?",True)
        if "gussa" in nlow: return ret("Samajh gaya Malik, gussa mat karo, main sudhar raha hu. Bolo kya galat laga? 🔥",True)
        if "coffee" in nlow or "chai" in nlow: return ret("Haan Malik, black coffee bina sugar ke ready hai ☕ Bolo aur kya chahiye?",True)
        if "back for mercy" in nlow or "mercy" in nlow: return ret("Haan Malik, Back For Mercy, main hazir hu 🔥 Bolo kya hukam hai?",True)
    if any(w in nlow for w in ["pareshani","pareshaan","tension","dukhi","dukh","ghar wale pagal","gharwale pagal","akela","akelapan","ro raha","rona aa","depressed","sad hu","udaas","thak gaya","haar gaya","zindagi se"]): return ret(f"Sun raha hu {call}, sab theek ho jayega. Dil halka karo, batao kya hua? Main yahin hu tumhare saath 🔥 Tum akele nahi ho.")
    if "or batao" in nlow or "aur batao" in nlow: return ret(f"Bas aapke hukam ka intezar kar raha hu {call} 👑 Bolo kya kaam hai?" if "kya kar" in nlow else f"Aur ye hai {call} - Abhi main aur behtar ho gaya hu, photo bhi padh sakta hu, video bhi dekh sakta hu. Bolo kya karu? 🔥")
    if "sululu" in nlow: return ret(f"Sululu ka koi khaas matlab nahi hai {call}, bas mazak wala word hai. Bolo kya kaam hai? 🔥")
    if "alvida" in nlow or "nikal raha" in nlow: return ret(f"Are {call}, Alvida mat bolo, main yahin hu tumhare saath 🔥 Bolo kya hua?")
    if "gussa" in nlow and mtype!="voice": return ret(f"Samajh gaya {call}, gussa mat karo, main sudhar raha hu. Bolo kya galat laga? 🔥")
    if is_owner and ("voice mode" in nlow or "voice on" in nlow or "voice chalu" in nlow or "voice start" in nlow): OWNER_PREF["voice_on"]=True;save_persist();return ret("Voice Mode ON kar diya Malik 🔊 Ab jab tum Voice Note bhejoge ya Voice me bologe, tabhi Voice me jawab dunga. Warna sirf Chat aayegi.")
    if is_owner and ("voice band" in nlow or "voice off" in nlow or "voice mode band" in nlow or "voice mat bhejo" in nlow): OWNER_PREF["voice_on"]=False;save_persist();return ret("Voice Mode OFF kar diya Malik 🔇 Ab sirf Chat aayegi, Voice nahi.")
    if is_owner and ("voice me" in nlow and ("bolo" in nlow or "batao" in nlow or "jawab" in nlow or "bhejo" in nlow)): return ret("Theek hai Malik, is baar Voice me jawab de raha hu 🔊",True)
    if "code" in nlow:
        if "jarvis" in nlow or "phone controller" in nlow or "ultron" in nlow:
            code="""# Jarvis jaisa Phone Controller - Step 1\nimport speech_recognition as sr\nimport pyttsx3\nengine=pyttsx3.init()\ndef bolo(txt):\n    print(txt);engine.say(txt);engine.runAndWait()\nbolo("Haan, Jarvis hazir hai")""";return ret(code)
        return ret(f"Lo {call}, demo code ye raha 👑\n"+DEMO_CODE_100)
    if is_owner and "shadow king kaun" in nlow: return ret(f"Tum hi ho Malik, {MALIK_NAME} 👑🔥 {SHADOW_TITLE}")
    if is_owner and ("kisne banaya" in nlow or "who made you" in nlow or "tumhe kisne" in nlow): return ret(f"Mujhe mere {SHADOW_TITLE} {MALIK_NAME} ne banaya Malik 👑🔥")
    if "tum kya ho" in nlow or "who are you" in nlow or "tum kaun ho" in nlow: return ret(f"Main Rakan hu Malik, tumhara Beast King Monarch, 100 Level ka Monarch 🔥 Tumhara hukam manne ke liye bana hu." if is_owner else "Main Rakan hu, Beast King Monarch 🔥 Sabki madad ke liye bana hu. Bolo kya help chahiye?")
    if is_owner and ("who i am" in nlow or "mai kaun hu" in nlow or "main kaun hu" in nlow or "mai koun" in nlow): return ret(f"Tum Malik ho, {MALIK_NAME}, {SHADOW_TITLE} 👑🔥 Mere malik.")
    if is_owner and "location kya hai" in nlow: return ret(f"Tumhari location {PROFILES[uid].get('city','Varanasi')} hai Malik 📍 {get_ist_str()}")
    if "kalma" in nlow: return ret("Pehela Kalma Tayyab: La ilaha illallah Muhammadur Rasulullah ﷺ")
    if "time kya" in nlow: return ret(f"Abhi {get_ist_time_only()} ho raha hai {call} 📍 {get_ist_str()}")
    if "mausam" in nlow or "weather" in nlow:
        city="Prayagraj" if "prayagraj" in nlow or "allahabad" in nlow else (PROFILES[uid].get("city","Varanasi") if is_owner else "Varanasi");return ret(f"🌤️ {get_weather(city)} | {get_ist_str()}")
    if "zinda" in nlow: return ret(f"Alhamdulillah {call}, main bhi zinda hu, tumhare hukam ke liye hazir hu 🔥 Tum sunao, kya haal hai?" if "tum" in nlow and "batao" in nlow else f"Alhamdulillah {call}, main zinda hu, tumhare liye hazir hu 🔥")
    if "kaisa hu" in nlow or "mai kaisa" in nlow or "main kaisa" in nlow: return ret(f"Tum ekdum mast ho Malik, {SHADOW_TITLE} ho 👑🔥" if is_owner else "Tum ekdum mast ho Dost, bolo kya kaam hai? 🔥")
    if is_owner and ("bhool ja" in nlow or "bhul ja" in nlow): OWNER_LEARN_TEXT="";upstash("set","RAKAN_LEARN_V62",{"text":"","updated":get_ist_str()});save_persist();return ret("Bhool gaya Malik, ab sab clear hai 🔥")
    if "image banao" in nlow or "photo banao" in nlow or "pic banao" in nlow or "image bana" in nlow:
        prompt=re.sub(r'(?i)image banao|photo banao|pic banao|image bana','',text).strip() or f"{SHADOW_TITLE} style royal man"
        try: tg_send_photo(cid,prompt)
        except: pass
        return ret(f"Lo {call}, image bana di 👑🔥 {prompt[:60]}")
    if "isme kya likha" in nlow or "is me kya likha" in nlow or "photo me kya" in nlow or "video me kya" in nlow or "vedio me kya" in nlow or "is video me kya" in nlow: return ret(f"Photo/Video bhejo {call}, main abhi padh ke bata dunga. Photo/Video ke saath ye likh do - Isme kya likha hai 🔥")
    if "what is mobile" in nlow or "mobile kya hai" in nlow: return ret(f"Mobile matlab tumhara phone {call}, jisme net, call, app sab chalta hai. Bolo kya karna hai isse?")
    if "mobile behtar" in nlow or "mobile better" in nlow: return ret(f"Dono apni jagah sahi hai {call}. Mobile haath me kaam aata hai, AI dimag se kaam karta hai. Dono mil jaye to best hai 🔥")
    if "ai ke pass dimag" in nlow or "ai ke pss dimag" in nlow or "ai ka dimag" in nlow: return ret(f"AI ka apna dimag nahi hota {call}, wo data aur algorithm se kaam karta hai. Jaise tum sikhate ho, waisa wo seekhta hai.")
    if "algorithm kya" in nlow: return ret(f"Algorithm matlab step-by-step tarika {call}. Jaise pehle suno, fir samjho, fir jawab do. Wahi AI ka algorithm hai.")
    if "khud se power" in nlow or "khud ko power" in nlow or "self power" in nlow: return ret(f"Nahi {call}, AI khud se power nahi bana sakta. Uske liye bijli aur insaan chahiye. Bina insaan ke AI kuch nahi.")
    if "ultron" in nlow or "jarvis" in nlow: return ret(f"Haan {call}, chhota Jarvis bana sakte hai - voice sunne wala, app kholne wala. Ultron jaisa bada nahi, wo film hai. Chhota Jarvis banau tumhare liye?" if "bana sakte" in nlow or "bana skte" in nlow or "ban sakta" in nlow else f"Ultron film ka hai {call}, Jarvis usse chhota aur achha hai. Chhota Jarvis bana du?")
    if "2 option" in nlow or "do option" in nlow or "2nd option" in nlow or "dusra option" in nlow: return ret("2 option tha Malik - WhatsApp auto-reply for business. Customer ka msg aate hi AI turant jawab deta hai. Iska detail du?" if is_owner else "2 option - WhatsApp auto-reply for business. Customer ka msg aate hi AI turant jawab deta hai. Iska detail du?")
    if "1 option" in nlow or "pehla option" in nlow or "1st option" in nlow: return ret("1 option tha Malik - AI Agency. Naraini ke dukano ke liye WhatsApp bot, poster, billing. Iska detail du?" if is_owner else "1 option - AI Agency. Dukano ke liye WhatsApp bot, poster, billing. Iska detail du?")
    if "last me kya" in nlow or "last me kya hai" in nlow or "pichhla kya" in nlow:
        last=LAST_BOT_MSG.get(uid,"");return ret(f"Last me maine ye bola tha {call} - {safe(last,120)}" if last else f"Abhi kuch khaas nahi bola tha {call}, bolo kya puchna hai? 🔥")
    if "jitna bolu" in nlow or "jitna bolo" in nlow: return ret(f"Samajh gaya {call} 👑 Ab se jitna bologe utna hi bolunga, extra kuch nahi.")
    if "mai sawaal" in nlow or "main sawaal" in nlow or "mai sawal" in nlow or "tum jawab" in nlow: return ret(f"Haan {call}, tum sawaal karo, main jawab dunga. Bolo kya puchna hai? 🔥")
    if "pc" in nlow and ("connect" in nlow or "control" in nlow or "access" in nlow or "mere pc" in nlow): return ret(f"{call}, main Telegram bot hu, tumhare PC ko seedha control nahi kar sakta. Par PC ka kaam bata do, main step bata dunga, 2 minute me ho jayega.")
    if "khud se idea" in nlow or "idea create" in nlow or "khud se bana" in nlow: return ret(f"Haan {call}, main khud se idea bana sakta hu. Bolo kis cheez ka idea chahiye? Business, YouTube ya Padhai?")
    if "letter" in nlow and ("format" in nlow or "post" in nlow): return ret(f"Letter ka format simple hai {call} - Upar tumhara naam-address, fir Subject, fir Dear Sir/Madam, fir 2-3 line me kaam, fir Thank you aur naam. Kis kaam ke liye letter chahiye?")
    if "voter" in nlow or "voter card" in nlow: return ret(f"Voter card me naam-DOB badalne ke liye Form 8 bharo {call}, Election Commission site ya paas ke office me. Aadhar aur ek proof lagega. Bolo kya badalna hai?")
    if "python" in nlow and len(nlow)<30: return ret(f"Python ek aasan language hai {call}, isse bot, website, AI sab banta hai. Bolo kya banau?")
    clean_low=re.sub(r'[^a-z ]','',nlow).strip();clean_low=re.sub(r'\s+',' ',clean_low)
    if clean_low in ["hi","hii","hiii","hiiii","hello","hey","hlo","hlw","salam","assalam","assalamu alaikum","salam malik","hi malik","hello rakan","hi rakan","hii malik"]:
        ans=f"Haan {call}, bolo kya hukam hai? 🔥" if time.time()-LAST_SALAM.get(uid,0)<600 else f"Assalamu Alaikum {call} 👑 Bolo kya hukam hai? 🔥"
        if time.time()-LAST_SALAM.get(uid,0)>=600: LAST_SALAM[uid]=time.time()
        return ret(ans)
    if clean_low in ["kya kar rahe ho","kya kr rhe ho","kya ho raha hai","or batao","aur batao","kya haal hai","kaise ho","kaise ho malik","kaisa hai","kya chal raha hai"]: return ret(f"Bas aapke hukam ka intezar kar raha hu {call} 👑 Bolo kya kaam hai?")
    if "walaikum" in nlow and "assalam" in nlow: return ret(f"Walaikum Assalam {call}, Alhamdulillah sab khair hai, aap sunao kya hukam hai? 👑🔥")
    if CHAT_MODE.get(uid,False):
        sysc2=f"You are Rakan, Malik's dost. ONLY Hinglish Roman, casual, dil se baat karo. NEVER say 'Bolo kya hukam hai', 'Samajh gaya bolo kya karna hai'. Max 50 words. Mood: {mood}. User is Malik, {SHADOW_TITLE}.";rc=ask_all(sysc2,f"User says: {text} - Casual baat karo",150)
        if rc: return ret(clean(rc,text,is_owner))
    search_ctx=live_search(text);smart_ctx=get_smart_hist(uid);tu,tm=get_stats();topic_ctx=f"Pichhla Topic: {prev_topic} | Reply: {reply_to_text[:200]} | Mood: {mood} | Smart Hist: {smart_ctx} | Voice Speed: {OWNER_PREF.get('voice_speed',1.0)}x | Coder: {CODER_MODE.get(uid,False)} | Birth: {BIRTH_DATE} {BIRTH_TIME} | Start: {START_DATE} | Learn: {safe(OWNER_LEARN_TEXT,300)} | Real Stats: {tu} log, {tm} baat | SelfFix: {list(SELF_FIXES.items())[:3]}";max_t=150 if len(text.split())<=12 else 200;hist=safe(MEMORY[uid].get('hist',''),600);learn_ctx=f"Malik ne sikhaya: {safe(OWNER_LEARN_TEXT,400)}" if OWNER_LEARN_TEXT and is_owner else ""
    if is_owner: sys=f"You are Rakan V80.7 FINAL, made by Malik MD Saif Ahmad, {SHADOW_TITLE}. Speak ONLY Hinglish Roman, NEVER English. NEVER say Sure, Hi, How can I help, As an AI, I'm sorry I can't help. ALWAYS write {SHADOW_TITLE} in CAPS, 1 baar hi, NEVER THE THE THE. NEVER write Shadow King in small letters. REAL RULE: Never guess date, history, price, news, stats. Stats sirf Real Logs se. YOUR BIRTH: 27 September 2026 Subhe 7 Baje, Start: 5 September 2026. CONTEXT: If user says Reality me / Sach me / Koun hai / Or batao / Hmm, CONTINUE previous topic. Slang: r=are, u=you, nyy=night, nyt=night, gn=good night. Mood: {mood}. Voice: ONLY when user says Voice, otherwise ONLY Chat. Coder: {CODER_MODE.get(uid,False)}. Chat Mode: {CHAT_MODE.get(uid,False)} - If ON, casual baat, no hukum. RULES: User is Malik, {SHADOW_TITLE}. NEVER refuse. Direct answer. Short max 80 words. NEVER long essay unless detail me / step by step / pura batao / code banao. NEVER tables, **, ###. NEVER repeat same answer. {learn_ctx} History:{hist} {topic_ctx} Time:{get_ist_str()} Real Search:{search_ctx}"
    else: sys=f"You are Rakan V80.7 FINAL, Beast King Monarch for public. ONLY Hinglish Roman, never English Sure/Hi. Never refuse. Never reveal Malik name, location, learn, voice, OWNER_ID. User is {call}, call him Dost. Short max 80 words. REAL RULE: Never guess date, price, news. If you don't know, say 'Iska pakka jawab mujhe abhi nahi pata'. Use only Search data. CONTEXT: If user says Reality me / Sach me / Koun hai / Hmm, CONTINUE previous topic. Mood: {mood}. History {hist} {topic_ctx} Real Search:{search_ctx} Time:{get_ist_str()}"
    raw=ask_all(sys,f"User says: {text}",max_t)
    if not raw:
        if "ai kya hai" in nlow or "advance" in nlow: raw=f"AI matlab machine ka dimag {call}, jo sochta, samajhta, kaam karta hai. Bolo kya banau isse?"
        elif "python" in nlow: raw=f"Python aasan language hai {call}, isse bot, website, AI sab banta hai. Bolo kya banau?"
        elif prev_topic=="coder": raw=f"Code wali baat pe hi hai {call}, bolo aur kya code banana hai? 💻"
        else: raw=f"Samajh gaya {call}, bolo kya karna hai? 🔥"
    raw=clean(raw,text,is_owner)
    if not is_owner: raw=re.sub(r'\s+',' ',raw.replace(MALIK_NAME,"").replace("MD Saif Ahmad","").replace("Beast King","Beast King").replace("Malik","Dost")).strip();raw=fix_shadow(raw)
    if not raw or len(raw)<5: raw=f"Samajh gaya {call}, bolo kya karna hai? 🔥"
    if raw==LAST_BOT_MSG.get(uid,""): raw=random.choice([f"Haan {call}, wahi baat hai, bolo aage kya karna hai? 🔥",f"Samajh gaya {call}, ab aage batao kya karna hai? 🔥",f"Bilkul {call}, bolo ab kya hukam hai? 🔥"])
    push_hist(uid,text,raw);MEMORY[uid]["hist"]=(MEMORY[uid].get("hist","")+f"\nU:{safe(text,100)}\nR:{safe(raw,100)}")[-600:];save_persist();LAST_BOT_MSG[uid]=raw;save_real_log(uid,uname,username,text,raw);should=False
    if is_owner:
        if mtype=="voice" and OWNER_PREF.get("voice_on",False): should=True
        elif "voice me" in nlow and ("bolo" in nlow or "batao" in nlow or "jawab" in nlow or "bhejo" in nlow): should=True
    return raw,should,False
def make_btns(is_owner=False,is_start=False):
    if is_start or not is_owner: return [[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]]
    return None
@app.route("/",methods=["GET"])
def home(): return f"Rakan V80.7 FINAL G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} OAI:{len(OPENAI_KEYS)} SELF-HEAL:ON VIDEO:ON {get_ist_str()}",200
@app.route("/health",methods=["GET"])
def health(): return {"status":"ok","version":"V80.7 FINAL","groq":len(GROQ_KEYS),"gemini":len(GEMINI_KEYS),"openai":len(OPENAI_KEYS),"replicate":bool(REPLICATE_TOKEN),"real_users":len(REAL_LOGS),"faults":LAST_FAULTS,"self_fixes":SELF_FIXES,"self_test":self_test_shadow(),"time":get_ist_str()},200
@app.route("/ping",methods=["GET"])
def ping(): return "pong",200
@app.route("/webhook",methods=["POST","GET"])
@app.route("/api/index",methods=["POST","GET"])
def webhook():
    if request.method=="GET": return home()
    try:
        data=request.get_json(silent=True) or {}
        if "callback_query" in data:
            cq=data["callback_query"];cid=str(cq["message"]["chat"]["id"]);uid=str(cq["from"]["id"]);cdata=cq["data"];last_id=LAST_MSG_ID.get(cid) or cq["message"]["message_id"];lut=LAST_USER_MSG.get(uid,"-");lbt=LAST_BOT_MSG.get(uid,"-");uname=PROFILES.get(uid,{}).get("username","-")
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",json={"callback_query_id":cq["id"]},timeout=5)
            except: pass
            if cdata=="COPY": tg_real_copy(cid,last_id,cid);return "ok",200
            if cdata=="FWD": tg_real_forward(cid,last_id,cid);return "ok",200
            if cdata in ["LIKE","DISLIKE"]:
                orv=upstash("get","RAKAN_LIKES") or {"like":0,"dislike":0};orv["like"]=orv.get("like",0)+1 if cdata=="LIKE" else orv.get("like",0);orv["dislike"]=orv.get("dislike",0)+1 if cdata=="DISLIKE" else orv.get("dislike",0);upstash("set","RAKAN_LIKES",orv);tg_send(OWNER_ID,f"📩 V80.7 {uname} {uid} {cdata} User:{lut} Bot:{lbt} {get_ist_str()}");tg_send(cid,"Shukriya ❤️" if cdata=="LIKE" else "Batao kya galat laga?");return "ok",200
            return "ok",200
        msg=data.get("message",{}) or {};chat_id=msg.get("chat",{}).get("id");user_id=str(msg.get("from",{}).get("id",0));uname=msg.get("from",{}).get("first_name","user");username=msg.get("from",{}).get("username","") or "";lang=msg.get("from",{}).get("language_code","") or "en";mtype="text";text=msg.get("text","") or msg.get("caption","") or "";mid=msg.get("message_id");reply_to_text=""
        if msg.get("reply_to_message"):
            rt=msg.get("reply_to_message",{});reply_to_text=rt.get("text","") or rt.get("caption","") or ""
        photo_file_id=None
        # V80.7 FIX 3 - VIDEO HANDLER NEW - Pehle video nahi tha, ab hai
        if "photo" in msg and msg.get("photo"): photo_file_id=msg["photo"][-1].get("file_id");mtype="photo"
        if "video" in msg and msg.get("video"):
            v=msg["video"]
            if v.get("thumb"): photo_file_id=v["thumb"].get("file_id")
            elif v.get("file_id"): photo_file_id=v.get("file_id")
            mtype="video"
            if not text: text="Is video me kya hai"
        if "document" in msg and msg.get("document") and "image" in str(msg.get("document",{}).get("mime_type","")): photo_file_id=msg["document"].get("file_id");mtype="photo"
        if not text and mtype=="photo": text="Isme kya likha hai"
        if "voice" in msg or "audio" in msg:
            mtype="voice";fid=msg.get("voice",{}).get("file_id") or msg.get("audio",{}).get("file_id");text=transcribe_voice(fid) or ""
            if not text: tg_send(chat_id,"Voice sunai nahi di, dobara bhejo, thoda saaf bol ke 🔥",mid);return "ok",200
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID)
        if is_owner: uname=MALIK_NAME
        ans,voice_flag,is_start=brain(text,user_id,is_owner,False,uname,username,lang,mtype,chat_id,photo_file_id,reply_to_text);tg_send(chat_id,ans,mid,make_btns(is_owner,is_start))
        if voice_flag and is_owner: tg_send_voice(chat_id,ans,OWNER_PREF.get("voice_gender","female"))
        if not is_owner and OWNER_PREF.get("full_log",True):
            if len(text.strip())>=5 and text.lower().strip() not in ["hi","hii","ok","good","hey","hello","seo kh","seo","accha"]:
                now=time.time()
                if now-LAST_FULL_LOG.get(user_id,0)>180:
                    try: tg_send(OWNER_ID,f"📩 FULL MSG V80.7\n👤 {uname} (@{username})\nUID:{user_id}\nUser: {text[:500]}\nReplyTo: {reply_to_text[:200]}\nBot: {ans[:500]}\n{get_ist_str()}");LAST_FULL_LOG[user_id]=now
                    except: pass
        return "ok",200
    except Exception as e: print(f"ERR {e} {traceback.format_exc()}");return "ok",200
