
import os, time, json, base64, re, datetime, requests, traceback
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","") or os.environ.get("TELEGRAM_BOT_TOKEN","")
OWNER_ID = int(os.environ.get("OWNER_ID","0") or 0)
MY_URL = os.environ.get("MY_URL","").rstrip("/") or "https://my-telegram-bot-lime.vercel.app"
LORE_ENV = os.environ.get("THE_BEAST_KING_MONARCH_AKAAN_LORE","")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY","")
MALE_VOICE_ID = (os.environ.get("ELEVEN_MALE_VOICE","pNInz6obpgDQGcFmaJgB") or "pNInz6obpgDQGcFmaJgB").strip()
FEMALE_VOICE_ID = (os.environ.get("ELEVEN_FEMALE_VOICE","EXAVITQu4vr4xnSDxMaL") or "EXAVITQu4vr4xnSDxMaL").strip()
REPLICATE_TOKEN = os.environ.get("REPLICATE_API_TOKEN","")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

MALIK_NAME="MD Saif Ahmad"; MALIK_TITLE="The Shadow King"; QUEEN_NAME="Theodore"
BIRTH_DATE="24 September 2025"; BIRTH_TIME="Subah 7 baje"
RAKAN_HISTORY="Janam 24 Sep 2025, Malik ne banaya. Queen Theodore."

MEMORY={}; ABUSE={}; PROFILES={}; REMINDERS=[]; OWNER_PREF={"voice_mode":False,"voice_gender":"female"}
CHAT_LOG=[]; BAD_KEYS={}; LAST_ERROR="No error yet"; _LAST_WEBHOOK=0

def upstash(cmd,key,val=None):
    if not UPSTASH_URL or not UPSTASH_TOKEN: return None
    try:
        headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        if cmd=="get":
            r=requests.get(f"{UPSTASH_URL}/get/{key}", headers=headers, timeout=5)
            if r.status_code==200:
                d=r.json().get("result")
                return json.loads(d) if d else None
        if cmd=="set" and val is not None:
            r=requests.post(f"{UPSTASH_URL}", headers=headers, json=["SET", key, json.dumps(val)], timeout=5)
            return r.status_code==200
    except: pass
    return None

def load_persist():
    global MEMORY,ABUSE,OWNER_PREF,CHAT_LOG,PROFILES,REMINDERS
    if not UPSTASH_URL: return
    MEMORY=upstash("get","RAKAN_MEM") or {}; ABUSE=upstash("get","RAKAN_ABUSE") or {}
    PROFILES=upstash("get","RAKAN_PROFILES") or {}; OWNER_PREF=upstash("get","RAKAN_PREF") or OWNER_PREF
    CHAT_LOG=upstash("get","RAKAN_LOGS") or []; REMINDERS=upstash("get","RAKAN_REMINDERS") or []
def save_persist():
    if not UPSTASH_URL: return
    upstash("set","RAKAN_MEM",MEMORY); upstash("set","RAKAN_ABUSE",ABUSE)
    upstash("set","RAKAN_PROFILES",PROFILES); upstash("set","RAKAN_PREF",OWNER_PREF)
    upstash("set","RAKAN_LOGS",CHAT_LOG[-300:]); upstash("set","RAKAN_REMINDERS",REMINDERS)
load_persist()

# FIXED FOR AQ. KEYS
def get_keys():
    g,gm,o=[],[],[]
    for k,v in os.environ.items():
        if not v: continue
        raw=str(v)
        parts=[p.strip().strip('"').strip("'") for p in raw.replace("\n",",").split(",") if p.strip()]
        for p in parts:
            if "GEMINI" in k.upper() and len(p)>20 and p not in gm: gm.append(p)
            if "GROQ" in k.upper() and len(p)>10 and p not in g: g.append(p)
            if p.startswith("gsk_") and p not in g: g.append(p)
            if p.startswith("AIza") and p not in gm: gm.append(p)
            if p.startswith("AQ.") and p not in gm: gm.append(p)
            if p.startswith("sk-") or p.startswith("sk-proj-"):
                if p not in o: o.append(p)
    return list(dict.fromkeys(g)),list(dict.fromkeys(gm)),list(dict.fromkeys(o))

GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys()
def is_bad(k): return k in BAD_KEYS and time.time()-BAD_KEYS[k]<900
def mark_bad(k): BAD_KEYS[k]=time.time()
def ensure_webhook():
    global _LAST_WEBHOOK
    if time.time()-_LAST_WEBHOOK<3600: return "CACHED"
    _LAST_WEBHOOK=time.time()
    if not BOT_TOKEN: return "NO TOKEN"
    try:
        exp=f"{MY_URL}/webhook"
        info=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=8).json()
        cur=info.get("result",{}).get("url","")
        if cur==exp: return f"OK {cur}"
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", params={"url":exp}, timeout=8)
        return f"SET {exp}"
    except Exception as e: return f"ERR {e}"

# ADVANCE LORE - NO REPEAT
BASE_LORE = f"""You are Rakan - The BeastKing Monarch, Knight.
Birth {BIRTH_DATE}. Malik is {MALIK_NAME}. Queen {QUEEN_NAME}. {RAKAN_HISTORY}
Lore: {{VERCEL_LORE}}
RULES:
- Never repeat Malik's full name in every message. Only answer what is asked. Be short, direct.
- Do not say "Aap hi MD Saif Ahmad ho" in every reply. BANNED.
- You have 2 special modes:
  1) QUIZ MODE: If user says "quiz lo, questions pucho, test lo, meri is cheez me help karo quiz ke hisab se" - then ask 1 question at a time, give options A,B,C,D, wait for answer, then explain and ask next.
  2) HELP MODE: If user says "isko kaise karna hai, kaise hoga, steps batao, explain karo" - then give step-by-step practical steps in numbered list.
- Normal chat me sirf utna hi bolo jitna pucha gaya hai.
- Language: User jis me bole usi me bolo. Malik se Roman Hinglish.
"""
FINAL_LORE=BASE_LORE.replace("{VERCEL_LORE}", LORE_ENV if LORE_ENV else "No extra lore")

def clean(txt):
    if not txt: return "Bolo kya chahiye?"
    if "(Note:" in txt: txt=txt.split("(Note:")[0].strip()
    if any(b in txt.lower() for b in ["i am meta ai","i am gemini","as an ai"]):
        return "Mai Rakan hu, bolo kya kaam hai?"
    txt=re.sub(r'\s+',' ',txt).strip()
    # Remove repetitive Malik lines if AI still adds
    txt=txt.replace("Aap hi MD Saif Ahmad ho","").replace("aap hi MD Saif Ahmad ho","").strip()
    txt=re.sub(r'Ji Malik,\s*aap hi.*?\.\s*','',txt,flags=re.IGNORECASE)
    return txt[:3900] if txt else "Bolo?"

def tg_send(chat_id,text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:3900]}, timeout=10)
    except: pass
def tg_send_photo(chat_id,url,cap=""):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id":chat_id,"photo":url,"caption":cap[:1000]}, timeout=20)
    except: pass
def tg_get_file_bytes(fid):
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}", timeout=10).json()
        fp=r["result"]["file_path"]
        return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=30).content, fp
    except: return None,None
def tg_send_voice_bytes(cid,audio):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":cid}, files={"voice":("rakan.mp3",audio,"audio/mpeg")}, timeout=30)
    except: pass

def analyze_user(uid,uname,text,is_owner):
    uid=str(uid); dn=MALIK_NAME if is_owner else uname
    if uid not in PROFILES: PROFILES[uid]={"name":dn,"mood":"normal","total_chats":0}
    p=PROFILES[uid]; p["total_chats"]+=1; p["name"]=dn; return p

# NEW MODELS - FRONT GEMINI
GROQ_MODELS=["openai/gpt-oss-120b","openai/gpt-oss-20b","meta-llama/llama-4-maverick-17b-128e-instruct","meta-llama/llama-4-scout-17b-16e-instruct","llama-3.3-70b-versatile","llama-3.1-8b-instant"]
OPENAI_MODELS=["gpt-4o-mini","gpt-4o"]
GEMINI_MODELS=["gemini-2.5-flash","gemini-2.5-flash-lite","gemini-2.5-pro","gemini-2.0-flash","gemini-1.5-flash","gemini-1.5-pro"]

def ask_groq(prompt):
    global LAST_ERROR
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in GROQ_MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":FINAL_LORE},{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":1200}, timeout=20)
                if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                if r.status_code in [401,403,429]: mark_bad(k); break
            except Exception as e: LAST_ERROR=str(e); continue
    return None

def ask_openai(prompt):
    for k in OPENAI_KEYS:
        if is_bad(k): continue
        for m in OPENAI_MODELS:
            try:
                r=requests.post(OPENAI_URL, headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":FINAL_LORE},{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":1200}, timeout=20)
                if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                if r.status_code in [401,403,429]: mark_bad(k); break
            except: continue
    return None

def ask_gemini(prompt):
    global LAST_ERROR
    for k in GEMINI_KEYS:
        if is_bad(k): continue
        for m in GEMINI_MODELS:
            try:
                try:
                    genai.configure(api_key=k)
                    model=genai.GenerativeModel(m, system_instruction=FINAL_LORE)
                    res=model.generate_content(prompt)
                    if res.text: return clean(res.text)
                except:
                    url=f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}"
                    r=requests.post(url, headers={"x-goog-api-key":k}, json={"system_instruction":{"parts":[{"text":FINAL_LORE}]},"contents":[{"parts":[{"text":prompt}]}]}, timeout=20)
                    if r.status_code==200:
                        txt=r.json()["candidates"][0]["content"]["parts"][0]["text"]
                        if txt: return clean(txt)
                    else: LAST_ERROR=f"{m} {r.status_code}"
            except Exception as e: LAST_ERROR=str(e)[:100]; continue
    return None

def ask_gemini_vision(img,prompt):
    for k in GEMINI_KEYS:
        try:
            genai.configure(api_key=k)
            model=genai.GenerativeModel("gemini-1.5-flash")
            res=model.generate_content([prompt, {"mime_type":"image/jpeg","data":img}])
            if res.text: return clean(res.text)
        except: continue
    return None

# FRONT GEMINI
def ask_all(prompt): return ask_gemini(prompt) or ask_groq(prompt) or ask_openai(prompt)

def parse_reminder(text,cid):
    low=text.lower()
    m=re.search(r'(\d+)\s*(min|minute|ghante|hour|sec)\s*baad',low)
    if m and ("message" in low or "yaad" in low):
        num=int(m.group(1)); unit=m.group(2)
        sec=num*60 if "min" in unit else num*3600 if "ghante" in unit or "hour" in unit else num
        REMINDERS.append({"chat_id":cid,"time":time.time()+sec,"msg":"Rakan sewa me hazir hai"})
        save_persist()
        return f"Thik hai, {num} {unit} baad bhej dunga."
    return None

def check_reminders():
    global REMINDERS
    now=time.time(); sent=[]
    for r in REMINDERS:
        if now>=r["time"]: tg_send(r["chat_id"], r["msg"]); sent.append(r)
    if sent: REMINDERS=[r for r in REMINDERS if r not in sent]; save_persist()
    return len(sent)

def check_proactive():
    if not OWNER_ID: return 0
    last=upstash("get","RAKAN_LAST_ACTIVE") or 0
    try: last=float(last)
    except: last=0
    if time.time()-last>600:
        tg_send(OWNER_ID,"Malik kya soch rahe ho? Koi help chahiye to bolo, Rakan yahi hai.")
        upstash("set","RAKAN_LAST_ACTIVE", time.time())
        return 1
    return 0

def get_bug_report():
    return f"Bug Report: Groq:{len(GROQ_KEYS)} | Gemini:{len(GEMINI_KEYS)} | OpenAI:{len(OPENAI_KEYS)} | Last:{LAST_ERROR} | Webhook:{ensure_webhook()}"

def eleven_tts(text):
    if not ELEVEN_API_KEY: return None
    try:
        vid=FEMALE_VOICE_ID if OWNER_PREF.get("voice_gender","female")=="female" else MALE_VOICE_ID
        r=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key":ELEVEN_API_KEY,"Content-Type":"application/json"}, json={"text":text[:800],"model_id":"eleven_multilingual_v2"}, timeout=25)
        if r.status_code==200: return r.content
    except: pass
    return None

def transcribe_media(audio_bytes,filename="voice.ogg"):
    for k in GROQ_KEYS:
        try:
            r=requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization":f"Bearer {k}"}, files={"file":(filename,audio_bytes)}, data={"model":"whisper-large-v3"}, timeout=30)
            if r.status_code==200: return r.json().get("text","")
        except: continue
    return None

def brain(text,uid,is_owner,uname,chat_id):
    global MEMORY,ABUSE
    uid_str=str(uid)
    if is_owner: uname=MALIK_NAME
    if uid_str not in MEMORY: MEMORY[uid_str]={"hist":"","role":"","count":0,"quiz_topic":"","quiz_q":0,"quiz_score":0}
    for k in ["hist","role","count","quiz_topic","quiz_q","quiz_score"]:
        MEMORY[uid_str].setdefault(k, "" if "topic" in k or "role" in k else 0)
    MEMORY[uid_str]["count"]+=1
    upstash("set","RAKAN_LAST_ACTIVE", time.time())
    profile=analyze_user(uid,uname,text,is_owner)
    CHAT_LOG.append({"id":uid,"name":uname,"text":text,"time":str(datetime.datetime.now())[:16],"owner":is_owner})
    low=text.lower().strip()

    # Secret block for public
    if not is_owner and any(s in low for s in ["bot_token","api key","owner id","queen","password"]):
        return "Ye Malik ka secret hai.", False

    if is_owner and low in ["/report","bug report","bug batao"]:
        return get_bug_report(), False

    rem=parse_reminder(text,chat_id) if is_owner else None
    if rem: return rem, False

    if is_owner and low in ["/start","start"]:
        return "Welcome to your world The Shadow King 👑", False
    if low in ["/start","start"]:
        return f"Welcome {uname}, bolo kya chahiye?", False

    # ADVANCE MODES
    # Quiz start
    if any(w in low for w in ["quiz lo","quiz karo","questions pucho","quiz ke hisab","mcq pucho","test lo","meri is chiz me help karo"]):
        topic=text.replace("quiz lo","").replace("quiz karo","").replace("questions pucho","").replace("meri is chiz me help karo","").strip() or "general"
        MEMORY[uid_str]["quiz_topic"]=topic; MEMORY[uid_str]["quiz_q"]=1; MEMORY[uid_str]["quiz_score"]=0; save_persist()
        q_prompt=f"User wants quiz on topic: {topic}. Create Question 1 with 4 options A,B,C,D, Roman Hinglish me, short. End me likho 'Jawab A/B/C/D me do'."
        ans=ask_all(q_prompt) or f"Chalo {topic} pe Quiz start karte hain. Q1: 2+2 kitna? A)3 B)4 C)5 D)6"
        MEMORY[uid_str]["hist"]+=f"\nU:{text}\nR:{ans}"; return ans, False

    # Quiz answer handling
    if MEMORY[uid_str].get("quiz_topic") and low in ["a","b","c","d","a)","b)","c)","d)"] or (len(low)<=2 and low[0] in "abcd"):
        topic=MEMORY[uid_str]["quiz_topic"]; qnum=MEMORY[uid_str]["quiz_q"]; score=MEMORY[uid_str]["quiz_score"]
        eval_prompt=f"Quiz Topic {topic}, Q{qnum} ka user answer {low} hai. Batao sahi hai ya galat, 1 line explain karo, score update karo, aur agla Question {qnum+1} pucho MCQ ke saath. Agar 5 question ho gaye to final score bata ke quiz khatam karo."
        ans=ask_all(eval_prompt) or "Thik hai, agla sawal..."
        MEMORY[uid_str]["quiz_q"]+=1
        if "sahi" in ans.lower(): MEMORY[uid_str]["quiz_score"]+=1
        if MEMORY[uid_str]["quiz_q"]>5:
            ans+=f"\n\nQuiz khatam! Score {MEMORY[uid_str]['quiz_score']}/5"; MEMORY[uid_str]["quiz_topic"]=""
        MEMORY[uid_str]["hist"]+=f"\nU:{text}\nR:{ans}"; save_persist(); return ans, False

    # Help/Steps mode
    if any(w in low for w in ["kaise karna hai","kaise hoga","steps batao","kaise kare","is se related batao","explain karo detail"]):
        help_prompt=f"User ko is cheez me help chahiye: {text}. Is se related steps, kaise karna hai, kaise hoga, short numbered list me Roman Hinglish me batao. Extra naam repeat mat karo."
        ans=ask_all(help_prompt) or "Batao kis cheez ka step chahiye?"
        MEMORY[uid_str]["hist"]=(MEMORY[uid_str]["hist"]+f"\nU:{text}\nR:{ans}")[-2500:]; save_persist(); return ans, False

    # Normal chat - short answer
    role=MEMORY[uid_str].get("role","")
    full=f"User: {profile['name']}, Mood:normal, Role:{role}\nHistory:{MEMORY[uid_str]['hist'][-1200:]}\nUser Message: {text}\nInstruction: Sirf is sawal ka jawab do, naam repeat mat karo, short me."
    ans=ask_all(full) or "Bolo kya help chahiye?"
    ans=clean(ans)
    MEMORY[uid_str]["hist"]=(MEMORY[uid_str]["hist"]+f"\nU:{text}\nR:{ans}")[-2500:]; save_persist()
    want_voice=is_owner and OWNER_PREF.get("voice_mode")
    return ans, want_voice

@app.route("/", methods=["GET"])
def home(): return f"Rakan AI Live {MALIK_NAME} G:{len(GROQ_KEYS)} O:{len(OPENAI_KEYS)} GM:{len(GEMINI_KEYS)} {ensure_webhook()}",200
@app.route("/health", methods=["GET"])
def health(): return jsonify({"groq":len(GROQ_KEYS),"openai":len(OPENAI_KEYS),"gemini":len(GEMINI_KEYS),"last_error":LAST_ERROR}),200
@app.route("/report", methods=["GET"])
def report_route():
    if str(request.args.get("id","0"))!=str(OWNER_ID): return "Only Malik",403
    return get_bug_report(),200
@app.route("/cron", methods=["GET"])
def cron_route():
    n=check_reminders(); p=check_proactive()
    return f"Reminders:{n} Proactive:{p}",200
@app.route("/fix", methods=["GET"])
def fix():
    global GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS,BAD_KEYS
    if str(request.args.get("id",""))!=str(OWNER_ID): return "Access Denied",403
    GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys(); BAD_KEYS.clear(); load_persist()
    return f"FIXED G:{len(GROQ_KEYS)} O:{len(OPENAI_KEYS)} GM:{len(GEMINI_KEYS)}",200
@app.route("/debug", methods=["GET"])
def debug():
    g,gm,o=get_keys()
    return f"G:{len(g)} GM:{len(gm)} O:{len(o)} START:{[k[:6] for k in gm]}",200
@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"Webhook {ensure_webhook()}",200
    try:
        check_reminders()
        data=request.get_json(silent=True) or {}
        msg=data.get("message",{}) or data.get("edited_message",{}) or {}
        chat_id=msg.get("chat",{}).get("id"); user_id=msg.get("from",{}).get("id",0)
        uname=msg.get("from",{}).get("first_name","user"); text=msg.get("text","") or msg.get("caption","") or ""
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID)
        if is_owner: uname=MALIK_NAME
        if msg.get("photo"):
            fbytes,_=tg_get_file_bytes(msg["photo"][-1]["file_id"])
            if fbytes:
                q=text if text else "Is photo me kya hai, Roman Hinglish me batao."
                vision_ans=ask_gemini_vision(fbytes,q)
                if vision_ans: tg_send(chat_id,vision_ans)
                else:
                    ans,_=brain(text,user_id,is_owner,uname,chat_id); tg_send(chat_id,ans)
                return "ok",200
        if msg.get("voice") or msg.get("audio"):
            fid=(msg.get("voice") or msg.get("audio") or {}).get("file_id")
            audio_bytes,_=tg_get_file_bytes(fid)
            heard=transcribe_media(audio_bytes) if audio_bytes else None
            if heard:
                ans,_=brain(heard,user_id,is_owner,uname,chat_id); tg_send(chat_id,ans)
            return "ok",200
        if not text: return "ok",200
        ans,want_voice=brain(text,user_id,is_owner,uname,chat_id)
        tg_send(chat_id,ans)
        if want_voice:
            audio=eleven_tts(ans)
            if audio: tg_send_voice_bytes(chat_id,audio)
        return "ok",200
    except Exception as e:
        print(traceback.format_exc()); return "ok",200
