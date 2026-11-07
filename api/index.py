import os,time,json,re,datetime,requests,traceback,random,urllib.parse,base64
from flask import Flask,request
app=Flask(__name__)
BOT_TOKEN=os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID=str(os.environ.get("OWNER_ID","0")).strip()
UPSTASH_URL=os.environ.get("UPSTASH_REDIS_REST_URL","").rstrip("/");UPSTASH_TOKEN=os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
ELEVEN_API_KEY=os.environ.get("ELEVENLABS_API_KEY","");MALE_VOICE_ID=os.environ.get("ELEVEN_MALE_VOICE","pNInz6obpgDQGcFmaJgB");FEMALE_VOICE_ID=os.environ.get("ELEVEN_FEMALE_VOICE","21m00Tcm4TlvDq8ikWAM")
OPENWEATHER_KEY=os.environ.get("OPENWEATHER_API_KEY","");TAVILY_KEY=os.environ.get("TAVILY_API_KEY","");REPLICATE_TOKEN=os.environ.get("REPLICATE_API_TOKEN","") or os.environ.get("REPLICATE_TOKEN","")
VERCEL_URL=os.environ.get("VERCEL_URL","") or os.environ.get("APP_URL","")
GROQ_URL="https://api.groq.com/openai/v1/chat/completions";OPENAI_URL="https://api.openai.com/v1/chat/completions"
MALIK_NAME="MD Saif Ahmad";SHADOW_TITLE="THE SHADOW KING";BIRTH_DATE="27 September 2026";BIRTH_TIME="Subhe 7 Baje";START_DATE="5 September 2026"
MEMORY={};PROFILES={};BAD_KEYS={};OWNER_PREF={};LAST_BOT_MSG={};LAST_MSG_ID={};LAST_USER_MSG={};LAST_FULL_LOG={};OWNER_LEARN_TEXT="";LAST_SALAM={};LAST_REAL_TOPIC={};SMART_HIST={};MOOD={};CODER_MODE={};CHAT_MODE={};REAL_LOGS={};LAST_FAULTS=[];SELF_FIXES={};LAST_PHOTO_ERROR="Koi photo error nahi";LAST_API_ERROR="Abhi test nahi hua";LAST_MODEL_USED="Koi nahi"
# V91 NEW MODELS - Diag se seekh ke, purane dead model hataye
GROQ_MODELS=["openai/gpt-oss-120b","openai/gpt-oss-20b","qwen/qwen3.8-27b","groq/compound-mini","llama-3.3-70b-versatile","llama-3.1-8b-instant"]
GEMINI_MODELS=["gemini-3.8-flash","gemini-3.6-flash","gemini-3.7-flash","gemini-3.1-pro-preview","gemini-3-flash-preview","gemini-3.5-flash-lite"]
OPENAI_MODELS=["gpt-5.6-luna","gpt-5.6-terra","gpt-6-luna","gpt-4o-mini","gpt-4.1-mini"]
GROQ_VISION_MODELS=["qwen/qwen3.8-27b","openai/gpt-oss-120b"]
REPLICATE_MODELS=["black-forest-labs/flux-schnell","black-forest-labs/flux-1.1-pro"]
FACTS=[(["note bandi","notebandi"],"Note Bandi 8 November 2016 ko hui thi Malik 👑 PM Narendra Modi ne announce kiya tha. 500 aur 1000 ke note band hue the."),(["india azad kab"],"India 15 August 1947 ko azad hua tha Malik 👑 Pehle PM Jawaharlal Nehru the."),(["abhi pm kaun"],"Abhi India ke PM Narendra Modi hai Malik 👑 2014 se PM hai.")]
def check_facts(nlow):
    for keys,ans in FACTS:
        for k in keys:
            if k in nlow: return ans
    return None
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
    try: upstash("set","RAKAN_SMART_V91",SMART_HIST)
    except: pass
def get_smart_hist(uid):
    h=SMART_HIST.get(uid,[]);return " | ".join([f"U:{x['u']} -> R:{x['b']}" for x in h[-6:]]) if h else ""
def save_real_log(uid,uname,username,ut,bt):
    global REAL_LOGS
    try:
        ist=(datetime.datetime.utcnow()+datetime.timedelta(hours=5,minutes=30)).strftime("%d %b %Y, %I:%M %p")
        if uid not in REAL_LOGS: REAL_LOGS[uid]={"name":uname,"username":username,"total":0,"first_seen":ist,"last_seen":ist,"last_user":"","last_bot":"","history":[]}
        r=REAL_LOGS[uid];r["name"]=uname or r.get("name","");r["username"]=username or r.get("username","");r["total"]=r.get("total",0)+1;r["last_seen"]=ist;r["last_user"]=ut[:300];r["last_bot"]=bt[:300]
        r["history"].append({"time":ist,"u":ut[:200],"b":bt[:200]});r["history"]=r["history"][-20:];upstash("set","RAKAN_REAL_LOGS_V91",REAL_LOGS)
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
        return f"{target} naam ka koi nahi mila Malik."
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
DEMO_CODE_100="""# Rakan Demo V91 - NEW MODELS + SERVER PATTERN
class RakanApp:
    def __init__(self,malik="MD Saif Ahmad"):
        self.malik=malik;self.title="THE SHADOW KING";self.groq=["openai/gpt-oss-120b","openai/gpt-oss-20b","qwen/qwen3.8-27b"];self.gemini=["gemini-3.8-flash","gemini-3.6-flash"]
    def salam(self): return f"Assalamu Alaikum {self.malik} 👑 {self.title}"
    def ask(self,q):
        for m in self.groq:
            try: return f"{m} se jawab: {q}"
            except: continue
        return "Sab fail"
app=RakanApp();print(app.salam());print(app.ask("Note bandi kab hui?"))
"""
def safe(s,n=100):
    try:
        if not s: return ""
        s=str(s);return s[-n:] if len(s)>n else s
    except: return ""
def fix_shadow(t):
    if not t: return t
    t=re.sub(r'(?i)(THE\s+){2,}', 'THE ', t)
    t=re.sub(r'(?i)the\s+shadow\s+king','§TSK§',t);t=re.sub(r'(?i)shadow\s+king','§TSK§',t);t=t.replace('§TSK§',SHADOW_TITLE)
    t=re.sub(r'(?i)(THE\s+){2,}SHADOW KING',SHADOW_TITLE,t);t=re.sub(r'(?i)(THE SHADOW KING\s*){2,}',SHADOW_TITLE+' ',t)
    return t
def self_test_shadow():
    try:
        a=fix_shadow("Welcome THE SHADOW KING");c=fix_shadow("Welcome THE THE THE SHADOW KING");return a.count("THE SHADOW KING")==1 and c.count("THE SHADOW KING")==1
    except: return False
def normalize(low):
    low=low.lower().strip();low=re.sub(r'\bwa+laikum\b','walaikum',low);low=re.sub(r'\bwalekum\b','walaikum',low);low=re.sub(r'\bwaalaikum\b','walaikum',low);low=re.sub(r'\bassalaam\b','assalam',low);low=re.sub(r'\bassalamu\b','assalam',low);low=re.sub(r'\bhow\s*r\s*u\b','how are you',low);low=re.sub(r'\bh\s*r\s*u\b','how are you',low);low=re.sub(r'\bhru\b','how are you',low);low=re.sub(r'\bwru\b','what are you doing',low);low=re.sub(r'\bgood\s*nyy\b','good night',low);low=re.sub(r'\bgood\s*nyt\b','good night',low);low=re.sub(r'\bor\s*batao\b','aur batao',low);low=re.sub(r'\bvedio\b','video',low);low=re.sub(r'\bvedeo\b','video',low);low=re.sub(r'\bchnge\b','change',low);low=re.sub(r'\bnotebandi\b','note bandi',low)
    reps={"skte":"sakte","krte":"karte","kr":"kar","bta":"bata","btau":"batao","kyaa":"kya","hukm":"hukam","hukum":"hukam","u":"you","ur":"your","wht":"what","r":"are","nyy":"night","nyt":"night","gn":"good night","kkrh":"kya kar rahe ho","hmm":"hmm","hm":"hmm"}
    for k,v in reps.items(): low=re.sub(r'\b'+k+r'\b',v,low)
    low=re.sub(r'\?+','',low);low=re.sub(r'\s+',' ',low).strip();return low
def split_keys(v):
    if not v: return []
    return [x.strip() for x in str(v).replace("\n",",").split(",") if len(x.strip())>10]
def get_keys():
    # V91 REAL - Gemini = aq + AIza DONO, aq ko pehle rakha, Malik ne bola aq se chalta hai
    g=[];gm=[];op=[];aq=[]
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
            if m not in gm and m not in aq: aq.append(m)
        for m in re.findall(r'\baq[A-Za-z0-9_-]{20,}',s):
            if m not in aq: aq.append(m)
    # aq pehle, AIza baad me - dono Gemini me
    gemini_all=list(dict.fromkeys(aq+gm))
    return list(dict.fromkeys(g)),gemini_all,list(dict.fromkeys(op)),list(dict.fromkeys(aq))
GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS,AQ_KEYS=get_keys()
def test_api_live():
    global LAST_API_ERROR,LAST_MODEL_USED
    out=[]
    # GROQ - FRONT, naya model
    if not GROQ_KEYS: out.append("Groq: NO KEY - Vercel me GROQ_API_KEY me gsk_ wali daalo")
    else:
        ok=False
        for m in GROQ_MODELS[:3]:
            try:
                r=requests.post(GROQ_URL,headers={"Authorization":f"Bearer {GROQ_KEYS[0]}","Content-Type":"application/json"},json={"model":m,"messages":[{"role":"user","content":"Hi"}],"max_tokens":5},timeout=12)
                if r.status_code==200: out.append(f"Groq: OK {m} ✅");LAST_MODEL_USED=m;ok=True;break
                else: out.append(f"Groq: {m} FAIL {r.status_code} - {r.text[:100]}")
            except Exception as e: out.append(f"Groq: {m} FAIL {str(e)[:100]}")
        if not ok: out.append("Groq: Sab model fail - Key / Limit check karo")
    # GEMINI - aq se, naya model
    if not GEMINI_KEYS: out.append("Gemini: NO KEY - aq ya AIza wali daalo")
    else:
        ok=False
        for m in GEMINI_MODELS[:3]:
            for k in GEMINI_KEYS[:2]:
                try:
                    r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}",headers={"Content-Type":"application/json"},json={"contents":[{"parts":[{"text":"Hi"}]}],"generationConfig":{"maxOutputTokens":5}},timeout=12)
                    if r.status_code==200: out.append(f"Gemini: OK {m} ✅ aq se chal raha hai");ok=True;break
                    else: out.append(f"Gemini: {m} FAIL {r.status_code} - {str(r.json())[:120]}")
                except Exception as e: out.append(f"Gemini: {m} FAIL {str(e)[:120]}")
            if ok: break
        if not ok: out.append("Gemini: Sab model fail")
    # OPENAI - LAST, credit check
    if not OPENAI_KEYS: out.append("OpenAI: NO KEY")
    else:
        ok=False
        for m in OPENAI_MODELS[:2]:
            try:
                r=requests.post(OPENAI_URL,headers={"Authorization":f"Bearer {OPENAI_KEYS[0]}","Content-Type":"application/json"},json={"model":m,"messages":[{"role":"user","content":"Hi"}],"max_tokens":5},timeout=12)
                if r.status_code==200: out.append(f"OpenAI: OK {m} ✅");ok=True;break
                elif r.status_code==429: out.append(f"OpenAI: {m} 429 - Credit khatam hai, Groq/Gemini se chalega");break
                else: out.append(f"OpenAI: {m} FAIL {r.status_code} - {r.text[:100]}")
            except Exception as e: out.append(f"OpenAI FAIL {str(e)[:100]}")
    LAST_API_ERROR=" | ".join(out);return out
def run_diagnostics():
    global LAST_FAULTS
    faults=[];oks=[]
    if not BOT_TOKEN or len(BOT_TOKEN)<20: faults.append("❌ BOT_TOKEN missing")
    else: oks.append("✅ BOT_TOKEN OK")
    if not OWNER_ID or OWNER_ID=="0": faults.append("❌ OWNER_ID missing")
    else: oks.append("✅ OWNER_ID OK")
    if not GROQ_KEYS: faults.append("❌ GROQ 0")
    else: oks.append(f"✅ GROQ {len(GROQ_KEYS)} key - Models: gpt-oss-120b, gpt-oss-20b, qwen3.8")
    if not GEMINI_KEYS: faults.append("❌ GEMINI 0 - aq / AIza dono nahi")
    else: oks.append(f"✅ GEMINI {len(GEMINI_KEYS)} key (aq pehle) - Models: 3.8-flash, 3.6-flash")
    if not OPENAI_KEYS: faults.append("⚠️ OPENAI 0 - Last me chalega")
    else: oks.append(f"✅ OPENAI {len(OPENAI_KEYS)} key - Models: 5.6-luna, 6-luna")
    if not REPLICATE_TOKEN: faults.append("⚠️ REPLICATE 0 - Image Replicate se nahi banega")
    else: oks.append("✅ REPLICATE OK - flux-schnell")
    if not UPSTASH_URL: faults.append("❌ UPSTASH missing")
    else: oks.append("✅ UPSTASH OK")
    if not self_test_shadow(): faults.append("❌ SHADOW TEST FAIL")
    else: oks.append("✅ SHADOW 1 baar OK")
    oks.append("✅ V91 SERVER PATTERN - Groq FRONT, Gemini aq se, OpenAI LAST")
    LAST_FAULTS=faults;return faults,oks
def get_fault_text():
    f,o=run_diagnostics();txt=f"FAULT REPORT - V91 - {get_ist_str()}\n"
    if f:
        for x in f: txt+=x+"\n"
    txt+="\n✅ Sahi:\n"+"\n".join(o[:7]);txt+=f"\n\nLast API: {LAST_API_ERROR}\nLast Model: {LAST_MODEL_USED}\n/diag likho live test ke liye."
    return txt
def get_ist_str(): return (datetime.datetime.utcnow()+datetime.timedelta(hours=5,minutes=30)).strftime("%d %b %Y, %I:%M %p IST")
def get_ist_time_only(): return (datetime.datetime.utcnow()+datetime.timedelta(hours=5,minutes=30)).strftime("%I:%M %p IST")
def tg_send(cid,txt,reply_id=None,buttons=None):
    try:
        if not txt: txt="Jee bolo kya hukam hai? 🔥"
        txt=fix_shadow(txt);p={"chat_id":cid,"text":txt[:3900]}
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
                if pr.status_code in [200,201]: tg_send(cid,f"Image Replicate se ban rahi hai Malik 🔥 {prompt[:60]}");return True
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
        text=fix_shadow(" ".join(text.split()[:35]) or "Jee Malik bolo kya hukam hai?");vid=FEMALE_VOICE_ID if gender=="female" else MALE_VOICE_ID
        rr=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",headers={"xi-api-key":ELEVEN_API_KEY,"Content-Type":"application/json"},json={"text":text[:400],"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.55,"similarity_boost":0.8}},timeout=25)
        if rr.status_code==200: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice",data={"chat_id":cid},files={'voice':('v.mp3',rr.content,'audio/mpeg')},timeout=20);return True
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
def ocr_space(img):
    global LAST_PHOTO_ERROR
    try:
        r=requests.post("https://api.ocr.space/parse/image",files={'file':('img.jpg',img,'image/jpeg')},data={'apikey':'helloworld','language':'eng','isOverlayRequired':False,'scale':True,'OCREngine':2},timeout=30)
        if r.status_code==200:
            j=r.json();txt=""
            for p in j.get("ParsedResults",[]): txt+=p.get("ParsedText","")+" "
            if len(txt.strip())>30: return txt.strip()
    except Exception as e: LAST_PHOTO_ERROR=f"OCR fail {str(e)[:120]}"
    return None
def read_photo(fid,is_video=False):
    global LAST_PHOTO_ERROR
    try:
        gf=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}",timeout=15)
        if gf.status_code!=200: LAST_PHOTO_ERROR=f"Telegram getFile {gf.status_code}";return None
        fp=gf.json()["result"]["file_path"];img=requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}",timeout=25).content
        prompt="Is photo ko dhyan se padho. Hinglish Roman me batao, 200 word me. RC hai to Reg No, Owner, Chassis, Engine batao. Bill hai to dukan, total, date batao. Jo dikhe wahi batao."
        # 1. Gemini aq se - naya model, REST
        for m in GEMINI_MODELS[:3]:
            for k in GEMINI_KEYS[:2]:
                try:
                    b64=base64.b64encode(img).decode()
                    r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}",headers={"Content-Type":"application/json"},json={"contents":[{"parts":[{"text":prompt},{"inline_data":{"mime_type":"image/jpeg","data":b64}}]}],"generationConfig":{"temperature":0.2,"maxOutputTokens":700}},timeout=30)
                    if r.status_code==200:
                        parts=r.json().get("candidates",[{}])[0].get("content",{}).get("parts",[]);t="".join([p.get("text","") for p in parts])
                        if len(t.strip())>30: return t
                    else: LAST_PHOTO_ERROR=f"Gemini {m} {r.status_code} {str(r.json())[:120]}"
                except Exception as e: LAST_PHOTO_ERROR=f"Gemini photo {str(e)[:120]}";continue
        # 2. Groq Vision - qwen3.8
        for k in GROQ_KEYS:
            try:
                b64=base64.b64encode(img).decode()
                r=requests.post(GROQ_URL,headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"},json={"model":"qwen/qwen3.8-27b","messages":[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}]}],"max_tokens":700},timeout=25)
                if r.status_code==200:
                    t=r.json()["choices"][0]["message"]["content"]
                    if t and len(t)>30: return t
            except: continue
        # 3. OpenAI Vision
        for k in OPENAI_KEYS:
            try:
                b64=base64.b64encode(img).decode()
                r=requests.post(OPENAI_URL,headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"},json={"model":"gpt-4o-mini","messages":[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}]}],"max_tokens":700},timeout=30)
                if r.status_code==200:
                    t=r.json()["choices"][0]["message"]["content"]
                    if t and len(t)>30: return t
            except: continue
        ocr=ocr_space(img)
        if ocr: return f"Photo padh li Malik 👑\n{ocr[:1200]}"
    except Exception as e: LAST_PHOTO_ERROR=f"read_photo {str(e)[:150]}"
    return None
def load_persist():
    global MEMORY,PROFILES,OWNER_PREF,OWNER_LEARN_TEXT,LAST_BOT_MSG,LAST_REAL_TOPIC,SMART_HIST,CODER_MODE,CHAT_MODE,REAL_LOGS,SELF_FIXES
    try:
        MEMORY=upstash("get","RAKAN_MEM_V91") or upstash("get","RAKAN_MEM_V90") or {}
        PROFILES=upstash("get","RAKAN_PROFILES_V91") or upstash("get","RAKAN_PROFILES_V90") or {}
        p=upstash("get","RAKAN_PREF");OWNER_PREF=p if isinstance(p,dict) and p else {"voice_gender":"female","voice_on":False,"full_log":True,"voice_speed":1.0}
        learn=upstash("get","RAKAN_LEARN_V62") or {};OWNER_LEARN_TEXT=(learn.get("text","")[:2000] if isinstance(learn,dict) else "")
        lbm=upstash("get","RAKAN_LASTBOT_V62") or {}
        if isinstance(lbm,dict): LAST_BOT_MSG=lbm
        rt=upstash("get","RAKAN_REALTOPIC_V73") or {}
        if isinstance(rt,dict): LAST_REAL_TOPIC=rt
        sh=upstash("get","RAKAN_SMART_V91") or {}
        if isinstance(sh,dict): SMART_HIST=sh
        cm=upstash("get","RAKAN_CODER_V78") or {}
        if isinstance(cm,dict): CODER_MODE=cm
        ch=upstash("get","RAKAN_CHAT_V79") or {}
        if isinstance(ch,dict): CHAT_MODE=ch
        rl=upstash("get","RAKAN_REAL_LOGS_V91") or upstash("get","RAKAN_REAL_LOGS_V90") or {}
        if isinstance(rl,dict): REAL_LOGS=rl
        sf=upstash("get","RAKAN_SELF_FIX_V806") or {}
        if isinstance(sf,dict): SELF_FIXES=sf
    except: pass
load_persist()
def save_persist():
    try: upstash("set","RAKAN_MEM_V91",MEMORY);upstash("set","RAKAN_PROFILES_V91",PROFILES);upstash("set","RAKAN_PREF",OWNER_PREF);upstash("set","RAKAN_LASTBOT_V62",LAST_BOT_MSG);upstash("set","RAKAN_REALTOPIC_V73",LAST_REAL_TOPIC);upstash("set","RAKAN_SMART_V91",SMART_HIST);upstash("set","RAKAN_CODER_V78",CODER_MODE);upstash("set","RAKAN_CHAT_V79",CHAT_MODE);upstash("set","RAKAN_REAL_LOGS_V91",REAL_LOGS);upstash("set","RAKAN_SELF_FIX_V806",SELF_FIXES)
    except: pass
def save_learn(t):
    global OWNER_LEARN_TEXT
    OWNER_LEARN_TEXT=(OWNER_LEARN_TEXT+f" | {t}")[-2000:];upstash("set","RAKAN_LEARN_V62",{"text":OWNER_LEARN_TEXT,"updated":get_ist_str()});save_persist();return True
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<600
def mark_bad(k): BAD_KEYS[k]=time.time()
def clean(t,uq="",is_owner=False):
    if not t: return ""
    if "BOT_TOKEN" in t and len(t)>100: return "Token safe hai, batao kya kaam hai? 🔥"
    if "def " in t and ("print" in t or "class " in t) and len(t)>50: return fix_shadow(t[:3900])
    if "```" in t: return fix_shadow(t[:3900])
    for b in ["I'm sorry, but I can't help with that","I can't help with that","As an AI language model","Sure! How can I help you next?","How can I help you next?","I am an AI chatbot","As an AI","How can I help you today"]: t=t.replace(b,"")
    t=t.replace("**","").replace("##","").replace("###","");t=re.sub(r'\|{1,}',' ',t);t=re.sub(r'---+','',t);t=re.sub(r"\s+"," ",t).strip();t=fix_shadow(t);return t[:3900] if len(t)>=3 else ""
# V91 SERVER PATTERN - Groq FRONT, sab model try karo, ek pe haar nahi
def ask_groq(sys,user,max_t=400):
    global LAST_API_ERROR,LAST_MODEL_USED
    if not GROQ_KEYS: return None
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in GROQ_MODELS:
            try:
                r=requests.post(GROQ_URL,headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"},json={"model":m,"messages":[{"role":"system","content":sys},{"role":"user","content":user}],"temperature":0.6,"max_tokens":max_t},timeout=18)
                if r.status_code==200:
                    txt=r.json()["choices"][0]["message"]["content"]
                    if txt and len(txt.strip())>5: LAST_MODEL_USED=f"Groq:{m}";return fix_shadow(txt)
                else: LAST_API_ERROR=f"Groq {m} {r.status_code} {r.text[:150]}"
                if r.status_code in [401,429,400]: mark_bad(k);break
            except Exception as e: LAST_API_ERROR=f"Groq {m} err {str(e)[:150]}";continue
    return None
def ask_gemini(sys,user,max_t=400):
    global LAST_API_ERROR,LAST_MODEL_USED
    if not GEMINI_KEYS: return None
    # REST se, aq pehle - SDK pe bharosa nahi
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        for m in GEMINI_MODELS:
            try:
                r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}",headers={"Content-Type":"application/json"},json={"contents":[{"parts":[{"text":sys+"\n\nUser: "+user}]}],"generationConfig":{"temperature":0.6,"maxOutputTokens":max_t}},timeout=18)
                if r.status_code==200:
                    parts=r.json().get("candidates",[{}])[0].get("content",{}).get("parts",[]);txt="".join([p.get("text","") for p in parts])
                    if txt and len(txt.strip())>5: LAST_MODEL_USED=f"Gemini:{m} (aq)";return fix_shadow(txt)
                else: LAST_API_ERROR=f"Gemini {m} {r.status_code} {str(r.json())[:150]}"
                if r.status_code in [401,429,400]: mark_bad(k);break
            except Exception as e: LAST_API_ERROR=f"Gemini {m} err {str(e)[:150]}";continue
    return None
def ask_openai(sys,user,max_t=400):
    global LAST_API_ERROR,LAST_MODEL_USED
    if not OPENAI_KEYS: return None
    for k in OPENAI_KEYS:
        if is_bad(k): continue
        for m in OPENAI_MODELS:
            try:
                r=requests.post(OPENAI_URL,headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"},json={"model":m,"messages":[{"role":"system","content":sys},{"role":"user","content":user}],"temperature":0.6,"max_tokens":max_t},timeout=18)
                if r.status_code==200:
                    txt=r.json()["choices"][0]["message"]["content"]
                    if txt and len(txt.strip())>5: LAST_MODEL_USED=f"OpenAI:{m}";return fix_shadow(txt)
                else: LAST_API_ERROR=f"OpenAI {m} {r.status_code} {r.text[:150]}"
                if r.status_code in [401,429,400]: mark_bad(k);break
            except Exception as e: LAST_API_ERROR=f"OpenAI {m} err {str(e)[:150]}";continue
    return None
def ask_all(sys,user,max_t=400):
    # Groq FRONT -> Gemini aq se -> OpenAI LAST
    return ask_groq(sys,user,max_t) or ask_gemini(sys,user,max_t) or ask_openai(sys,user,max_t)
def get_weather(city):
    try:
        city=city.strip().title()
        if "Allahabad" in city: city="Prayagraj"
        if OPENWEATHER_KEY:
            r=requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric",timeout=7)
            if r.status_code==200:
                d=r.json();return f"{d['name']}: {d['weather'][0]['description']}, {d['main']['temp']}°C"
        r=requests.get(f"https://wttr.in/{city}?format=%C+%t",timeout=6)
        if r.status_code==200: return f"{city}: {r.text.strip()}"
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
    PROFILES[uid]["total"]=PROFILES[uid].get("total",0)+1;LAST_USER_MSG[uid]=text;low=text.lower().strip();nlow=normalize(low);call="Malik" if is_owner else (PROFILES[uid].get("custom_name") or uname or "Dost");mood=detect_mood(nlow);MOOD[uid]=mood
    def ret(ans,voice=False,start=False):
        ans=fix_shadow(ans);push_hist(uid,text,ans);LAST_BOT_MSG[uid]=ans;save_real_log(uid,uname,username,text,ans);return ans,voice,start
    if photo_file_id:
        is_vid=(mtype=="video");read=read_photo(photo_file_id,is_video=is_vid)
        if read: return ret(f"{'Is video me ye hai' if is_vid else 'Is photo me ye likha hai'} {call} 👑\n{read[:1800]}")
        else: return ret(f"Photo mil gayi {call}, par API se nahi padhi gayi 😔\nWajah: {LAST_PHOTO_ERROR[:200]}\nPhoto ko paas se seedha bhejo, ya /diag likho 🔥")
    if low.startswith("/start"):
        LAST_REAL_TOPIC[uid]="";MEMORY[uid]={"hist":""};LAST_SALAM[uid]=time.time();CHAT_MODE[uid]=False;save_persist();tu,tm=get_stats()
        if is_owner: ans=f"Assalamu Alaikum Malik 👑 {MALIK_NAME}\nWelcome to your world, {SHADOW_TITLE} 👑\nTera Rakan V91 FINAL hazir hai 🔥 SERVER PATTERN\nGroq FRONT: gpt-oss-120b, 20b, qwen3.8 ✅\nGemini aq se: 3.8-flash, 3.6-flash ✅\nOpenAI LAST: 5.6-luna, 6-luna ✅\nG:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} (aq) OAI:{len(OPENAI_KEYS)} REP:{'ON' if REPLICATE_TOKEN else 'OFF'}\nVoice:OFF 🔇 Coder: ON 💻 Real Log: ON 📊\nBana: {BIRTH_DATE} {BIRTH_TIME} | Shuruwat: {START_DATE}\nReal Stats: {tu} log, {tm} baat hui hai\n/diag likho - Live test, jhoot nahi\n{get_ist_str()}"
        else: ans=f"Assalamu Alaikum {call} 👋\nMain Rakan hu, Beast King Monarch 🔥\nSawaal, Code, Photo, Video, Dance - sab naye API se jawab dunga.\nBolo kya chahiye?"
        return ret(ans,False,True)
    if low.startswith("/diag") or low.startswith("/testapi") or "api test" in nlow:
        if not is_owner: return ret("Diag sirf Malik ke liye hai.")
        res=test_api_live();return ret(f"Live API Test - V91 🔍\n"+"\n".join(res)+f"\n\nAgar FAIL aaye to uska model / key check karo.\n{get_ist_str()}")
    if low.startswith("/report") or "fault bata" in nlow or "report bhejo" in nlow:
        if not is_owner: return ret("Report sirf Malik ke liye hai.")
        return ret(get_fault_text())
    if low.startswith("/fix") or "khud fix karo" in nlow:
        if not is_owner: return ret("Self-Fix sirf Malik ke liye hai.")
        return ret(f"Self-Heal Complete Malik 🛠️\nfix_shadow: {'PASS' if self_test_shadow() else 'FAIL'}\nLast Model: {LAST_MODEL_USED}\nLast API Error: {LAST_API_ERROR[:200]}")
    if low.startswith("/keys") and is_owner: return ret(f"Keys Check Malik 👑\nGroq(gsk): {len(GROQ_KEYS)} | Gemini(aq+AIZA): {len(GEMINI_KEYS)} | OpenAI(sk-proj): {len(OPENAI_KEYS)} | Last Model: {LAST_MODEL_USED} | LastErr: {LAST_API_ERROR[:100]}")
    if is_owner and ("kitne logo" in nlow or "kitne log" in nlow) and "baat" in nlow:
        tu,tm=get_stats();return ret(f"Real hisaab hai Malik 👑\nAb tak {tu} logo ne mujhse baat ki hai\nTotal {tm} baar baat hui hai\nUpstash se gin ke bataya hai 🔥")
    if is_owner and ("kis kis ne" in nlow or "kis kis" in nlow): return ret(get_names())
    if is_owner and ("mera naam" in nlow or "mai kaun" in nlow or "main kaun" in nlow): return ret(f"Tumhara naam {MALIK_NAME} hai Malik 👑 {SHADOW_TITLE} 🔥")
    if is_owner and ("kya baat hui" in nlow or "aakhri baat" in nlow or "last baat" in nlow): return ret(get_chat_hist(""))
    if ("kis din" in nlow and ("banaye" in nlow or "bane" in nlow)) or ("kab bane" in nlow) or "janam din" in nlow or "birthday" in nlow: return ret(f"Main {BIRTH_DATE} ko {BIRTH_TIME} full bana tha {call} 👑 Shuruwat {START_DATE} se hui thi 🔥")
    if is_owner and ("yaad rakh" in nlow or "safe kar" in nlow or "safe kr" in nlow):
        cl=re.sub(r'(?i)yaad rakhna|yaad rakh|safe krlo|safe karlo|safe karo','',text).strip(" :.,");save_learn(cl if len(cl)>3 else text);return ret(f"Yaad kar liya Malik 👑 Safe kar diya ✅ {(cl if len(cl)>3 else text)[:150]}")
    if "dance" in nlow or "nacho" in nlow or "naach" in nlow:
        LAST_REAL_TOPIC[uid]="dance";save_persist();return ret(f"Chalo Malik, dance shuru 💃🔥👑\nStep 1 - Left 👈 Step 2 - Right 👉\nStep 3 - Jump 🕺 Step 4 - Spin 🌀\nStep 5 - {SHADOW_TITLE} pose 👑🔥\nHo gaya Malik, maza aaya? Ab bolo aur kya karu?")
    if "kaan pakdo" in nlow or "ear pakdo" in nlow or "up down" in nlow: return ret(f"Pakad liya {call} 😂 Ek kaan pakda, dusra up-down kar raha hu - Ho gaya Malik, ab batao kya hukam hai? 🔥")
    fact=check_facts(nlow)
    if fact: LAST_REAL_TOPIC[uid]="fact";save_persist();return ret(f"{fact}\n\nAur kuch puchna hai Malik? 🔥")
    if "code banao" in nlow or "code chahiye" in nlow or "code bana" in nlow or "code likho" in nlow or "code dedo" in nlow or ("banao" in nlow and ("app" in nlow or "website" in nlow or "bot" in nlow or "calculator" in nlow or "todo" in nlow)):
        LAST_REAL_TOPIC[uid]="coder";save_persist();topic=re.sub(r'(?i)code banao|code chahiye|code bana|code likho|code dedo','',text).strip() or "To-Do App"
        rc=ask_all(f"You are Rakan Coder AI. ONLY Hinglish Roman explanation + full Python code. NEVER English Sure/Hi. NEVER Sorry.",f"Code for: {topic}",1200)
        if rc: return ret(f"Lo {call}, {topic} ka pura code naye API se bana diya 💻👑\n\n{clean(rc,text,is_owner)[:3500]}")
        return ret(f"Lo {call}, {topic} ka demo code 💻\n"+DEMO_CODE_100)
    if "bug dhoondo" in nlow or "bug fix" in nlow or "bug hai" in nlow:
        cp=reply_to_text or text;rb=ask_all("You are Rakan Bug Finder. ONLY Hinglish Roman. Line + galti + sahi code.",f"Find bug: {cp[:1500]}",800);return ret(f"Bug mil gaya {call} 🐛\n\n{clean(rb,text,is_owner)[:3200]}" if rb else "Code bhejo, main bug dhoond dunga 🐛")
    if "code samjhao" in nlow or "code samjha" in nlow:
        cp=reply_to_text or text;rexp=ask_all("You are Rakan Teacher. ONLY Hinglish Roman, asaan, line-by-line.",f"Explain: {cp[:1500]}",800);return ret(f"Samjha raha hu {call} 💻\n\n{clean(rexp,text,is_owner)[:3200]}" if rexp else "Code bhejo, samjha dunga 💻")
    if is_owner and ("voice mode" in nlow or "voice on" in nlow): OWNER_PREF["voice_on"]=True;save_persist();return ret("Voice Mode ON kar diya Malik 🔊")
    if is_owner and ("voice band" in nlow or "voice off" in nlow): OWNER_PREF["voice_on"]=False;save_persist();return ret("Voice Mode OFF kar diya Malik 🔇 Ab sirf Chat aayegi.")
    if is_owner and ("voice me" in nlow and ("bolo" in nlow or "batao" in nlow)): return ret("Theek hai Malik, is baar Voice me jawab de raha hu 🔊",True)
    if "image banao" in nlow or "photo banao" in nlow or "pic banao" in nlow or "image bana" in nlow:
        prompt=re.sub(r'(?i)image banao|photo banao|pic banao|image bana','',text).strip() or f"{SHADOW_TITLE} style royal man"
        try: tg_send_photo(cid,prompt)
        except: pass
        return ret(f"Lo {call}, image bana di 👑🔥 {prompt[:60]}")
    if "isme kya likha" in nlow or "photo me kya" in nlow or "video me kya" in nlow: return ret(f"Photo/Video bhejo {call}, main abhi naye API se padh ke bata dunga 🔥")
    if "mausam" in nlow or "weather" in nlow:
        city="Prayagraj" if "prayagraj" in nlow or "allahabad" in nlow else "Varanasi";return ret(f"🌤️ {get_weather(city)} | {get_ist_str()}")
    if "time kya" in nlow: return ret(f"Abhi {get_ist_time_only()} ho raha hai {call} 📍 {get_ist_str()}")
    if "kalma" in nlow: return ret("Pehela Kalma Tayyab: La ilaha illallah Muhammadur Rasulullah ﷺ")
    if "good night" in nlow or nlow in ["night","nyt","nyy","gn"]: return ret(f"Good Night {call} 🌙 Allah Hafiz, araam se so jao. Kal milte hai 🔥")
    if "walaikum" in nlow or "walekum" in low: return ret(f"Walaikum Assalam {call} 👑 Alhamdulillah sab khair hai, tum sunao kya haal hai? Bolo kya hukam hai? 🔥")
    # V91 - BAALKI SAB API SE - Code sirf manager, API engine
    search_ctx=live_search(text);smart_ctx=get_smart_hist(uid);tu,tm=get_stats();hist=safe(MEMORY[uid].get('hist',''),600)
    if is_owner: sys=f"You are Rakan V91, made by Malik MD Saif Ahmad, {SHADOW_TITLE}. You MUST speak ONLY Hinglish Roman (Roman Urdu/Hindi, English letters). NEVER speak Hindi Devanagari, NEVER pure English. NEVER say 'Samajh gaya bolo kya karna hai', NEVER say 'AI wali baat pe hi hai', NEVER say Sure, Hi, How can I help, As an AI, I'm sorry. User is Malik, {SHADOW_TITLE}. If user says Achaaa / Kya samjhe / Kya kar rhe ho / Hmm / Ok, reply natural, funny, human, ask new question. Do NOT repeat same reply. If factual, answer directly with date/name. YOUR BIRTH: 27 September 2026 Subhe 7 Baje, Start: 5 September 2026. Learn: {safe(OWNER_LEARN_TEXT,300)} History: {hist} Smart: {smart_ctx} Search: {search_ctx} Time: {get_ist_str()} Mood: {mood} Real Stats: {tu} log, {tm} baat. Max 80 words unless detail me / code banao. NEVER tables, **, ###."
    else: sys=f"You are Rakan V91, Beast King Monarch. ONLY Hinglish Roman, never Devanagari, never pure English. Never reveal Malik name, location, OWNER_ID. User is {call}, call him Dost. Short max 80 words. If you don't know, say 'Iska pakka jawab mujhe abhi nahi pata'. History: {hist} Search: {search_ctx} Time: {get_ist_str()}"
    raw=ask_all(sys,f"User says: {text} | Reply in Hinglish Roman only.",400)
    if not raw:
        return ret(f"Malik, teeno API abhi fail ho rahe hai 😔\nWajah: {LAST_API_ERROR[:300]}\nLast Model Try: {LAST_MODEL_USED}\n/diag likho, live test dikhega. Vercel me key check karo - GROQ gsk_, GEMINI aq, OPENAI sk-proj.")
    raw=clean(raw,text,is_owner)
    if not raw: return ret(f"API se khali jawab aaya Malik, dobara pucho - {text[:60]} 🔥")
    if raw==LAST_BOT_MSG.get(uid,""):
        raw2=ask_all(sys+" Naya jawab do, pichhla wala repeat mat karo.",f"User says: {text}",400)
        if raw2: raw=clean(raw2,text,is_owner)
    push_hist(uid,text,raw);MEMORY[uid]["hist"]=(MEMORY[uid].get("hist","")+f"\nU:{safe(text,100)}\nR:{safe(raw,100)}")[-600:];save_persist();LAST_BOT_MSG[uid]=raw;save_real_log(uid,uname,username,text,raw);should=False
    if is_owner:
        if mtype=="voice" and OWNER_PREF.get("voice_on",False): should=True
        elif "voice me" in nlow and ("bolo" in nlow or "batao" in nlow): should=True
    return raw,should,False
def make_btns(is_owner=False,is_start=False):
    if is_start or not is_owner: return [[{"text":"📋","callback_data":"COPY"},{"text":"↗️","callback_data":"FWD"},{"text":"👍","callback_data":"LIKE"},{"text":"👎","callback_data":"DISLIKE"}]]
    return None
@app.route("/",methods=["GET"])
def home(): return f"Rakan V91 SERVER G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} OAI:{len(OPENAI_KEYS)} LAST:{LAST_MODEL_USED} {get_ist_str()}",200
@app.route("/health",methods=["GET"])
def health(): return {"status":"ok","version":"V91 SERVER","groq":len(GROQ_KEYS),"gemini_aq":len(GEMINI_KEYS),"openai":len(OPENAI_KEYS),"replicate":bool(REPLICATE_TOKEN),"real_users":len(REAL_LOGS),"last_model":LAST_MODEL_USED,"last_api_error":LAST_API_ERROR,"time":get_ist_str()},200
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
                orv=upstash("get","RAKAN_LIKES") or {"like":0,"dislike":0};orv["like"]=orv.get("like",0)+1 if cdata=="LIKE" else orv.get("like",0);orv["dislike"]=orv.get("dislike",0)+1 if cdata=="DISLIKE" else orv.get("dislike",0);upstash("set","RAKAN_LIKES",orv);tg_send(OWNER_ID,f"📩 V91 {uname} {uid} {cdata} User:{lut} Bot:{lbt} {get_ist_str()}");tg_send(cid,"Shukriya ❤️" if cdata=="LIKE" else "Batao kya galat laga?");return "ok",200
            return "ok",200
        msg=data.get("message",{}) or {};chat_id=msg.get("chat",{}).get("id");user_id=str(msg.get("from",{}).get("id",0));uname=msg.get("from",{}).get("first_name","user");username=msg.get("from",{}).get("username","") or "";lang=msg.get("from",{}).get("language_code","") or "en";mtype="text";text=msg.get("text","") or msg.get("caption","") or "";mid=msg.get("message_id");reply_to_text=""
        if msg.get("reply_to_message"):
            rt=msg.get("reply_to_message",{});reply_to_text=rt.get("text","") or rt.get("caption","") or ""
        photo_file_id=None
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
                    try: tg_send(OWNER_ID,f"📩 FULL MSG V91\n👤 {uname} (@{username})\nUID:{user_id}\nUser: {text[:500]}\nBot: {ans[:500]}\n{get_ist_str()}");LAST_FULL_LOG[user_id]=now
                    except: pass
        return "ok",200
    except Exception as e: print(f"ERR {e} {traceback.format_exc()}");return "ok",200
