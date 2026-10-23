import os, time, json, re, datetime, requests, traceback
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

def get_keys():
    g,gm,o=[],[],[]
    for k,v in os.environ.items():
        if not v: continue
        raw=str(v)
        parts=[p.strip().strip('"').strip("'") for p in raw.replace("\n",",").split(",") if p.strip()]
        for p in parts:
            if not p: continue
            if "GEMINI" in k.upper() and len(p)>20 and p not in gm: gm.append(p)
            if "GROQ" in k.upper() and len(p)>10 and p not in g: g.append(p)
            if p.startswith("gsk_") and p not in g: g.append(p)
            if p.startswith("AIza") and p not in gm: gm.append(p)
            if p.startswith("AQ.") and p not in gm: gm.append(p)
            if (p.startswith("sk-") or p.startswith("sk-proj-")) and p not in o: o.append(p)
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

BASE_LORE = f"""You are Rakan - The BeastKing Monarch, Knight.
Malik is {MALIK_NAME} ({MALIK_TITLE}). Birth {BIRTH_DATE}. Queen {QUEEN_NAME}.
Lore: {{VERCEL_LORE}}
RULES - STRICT:
- Never repeat Malik's full name in every message. BANNED: "Aap hi MD Saif Ahmad ho"
- Be short, direct, conversational. Answer only what is asked.
- Do not loop "What do you need? Kya madad chahiye?"
- If user says "Hey" -> reply "Hey Malik, bolo kya haal hai?" not "What do you need?"
- If user replies to a message, understand that replied message context.
- Language: Malik se Roman Hinglish.
- Modes: QUIZ -> 1 MCQ at a time A,B,C,D. HELP -> numbered steps.
- Normal: short, no haath jodna emoji spam.
"""
FINAL_LORE=BASE_LORE.replace("{VERCEL_LORE}", LORE_ENV if LORE_ENV else "No extra lore")

def clean(txt):
    if not txt: return "Bolo kya chahiye?"
    if "(Note:" in txt: txt=txt.split("(Note:")[0].strip()
    if any(b in txt.lower() for b in ["i am meta ai","i am gemini","as an ai"]):
        return "Mai Rakan hu, bolo kya kaam hai?"
    txt=re.sub(r'\s+',' ',txt).strip()
    txt=txt.replace("Aap hi MD Saif Ahmad ho","").strip()
    txt=re.sub(r'Ji Malik,\s*aap hi.*?\.\s*','',txt,flags=re.IGNORECASE)
    txt=re.sub(r'Kya madad chahiye\??','',txt,flags=re.IGNORECASE)
    txt=re.sub(r'What do you need\??','',txt,flags=re.IGNORECASE).strip()
    return txt[:3900] if txt else "Bolo?"

def tg_send(chat_id,text,reply_id=None):
    try:
        payload={"chat_id":chat_id,"text":text[:3900]}
        if reply_id: payload["reply_to_message_id"]=reply_id
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=10)
    except: pass
def tg_send_photo(chat_id,url,cap="",reply_id=None):
    try:
        payload={"chat_id":chat_id,"photo":url,"caption":cap[:1000]}
        if reply_id: payload["reply_to_message_id"]=reply_id
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json=payload, timeout=20)
    except: pass
def tg_get_file_bytes(fid):
    try:
        r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}", timeout=10).json()
        fp=r["result"]["file_path"]
        return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=30).content, fp
    except: return None,None

GROQ_MODELS=["openai/gpt-oss-120b","openai/gpt-oss-20b","meta-llama/llama-4-maverick-17b-128e-instruct","llama-3.3-70b-versatile","llama-3.1-8b-instant"]
OPENAI_MODELS=["gpt-4o-mini","gpt-4o"]
GEMINI_MODELS=["gemini-2.5-flash","gemini-2.5-flash-lite","gemini-2.5-pro","gemini-2.0-flash","gemini-1.5-flash"]

def ask_groq(prompt):
    global LAST_ERROR
    for k in GROQ_KEYS:
        if is_bad(k): continue
        for m in GROQ_MODELS:
            try:
                r=requests.post(GROQ_URL, headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":FINAL_LORE},{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":1000}, timeout=20)
                if r.status_code==200: return clean(r.json()["choices"][0]["message"]["content"])
                if r.status_code in [401,403,429]: mark_bad(k); break
            except Exception as e: LAST_ERROR=str(e); continue
    return None
def ask_openai(prompt):
    for k in OPENAI_KEYS:
        if is_bad(k): continue
        for m in OPENAI_MODELS:
            try:
                r=requests.post(OPENAI_URL, headers={"Authorization":f"Bearer {k}","Content-Type":"application/json"}, json={"model":m,"messages":[{"role":"system","content":FINAL_LORE},{"role":"user","content":prompt}],"temperature":0.7,"max_tokens":1000}, timeout=20)
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
                genai.configure(api_key=k)
                model=genai.GenerativeModel(m, system_instruction=FINAL_LORE)
                res=model.generate_content(prompt)
                if res.text: return clean(res.text)
            except Exception as e:
                try:
                    url=f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}"
                    r=requests.post(url, headers={"x-goog-api-key":k}, json={"system_instruction":{"parts":[{"text":FINAL_LORE}]},"contents":[{"parts":[{"text":prompt}]}]}, timeout=20)
                    if r.status_code==200:
                        txt=r.json()["candidates"][0]["content"]["parts"][0]["text"]
                        if txt: return clean(txt)
                except: pass
                LAST_ERROR=str(e)[:100]; continue
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
def ask_all(prompt): return ask_gemini(prompt) or ask_groq(prompt) or ask_openai(prompt)

def transcribe_media(audio_bytes,filename="voice.ogg"):
    for k in GROQ_KEYS:
        try:
            r=requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization":f"Bearer {k}"}, files={"file":(filename, audio_bytes)}, data={"model":"whisper-large-v3"}, timeout=30)
            if r.status_code==200: return r.json().get("text","")
        except: continue
    return None

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

def brain(text,uid,is_owner,uname,chat_id,reply_context=""):
    global MEMORY
    uid_str=str(uid)
    if is_owner: uname=MALIK_NAME
    if uid_str not in MEMORY: MEMORY[uid_str]={"hist":"","count":0,"quiz_topic":"","quiz_q":0,"quiz_score":0}
    MEMORY[uid_str]["count"]+=1
    upstash("set","RAKAN_LAST_ACTIVE", time.time())
    CHAT_LOG.append({"id":uid,"name":uname,"text":text,"time":str(datetime.datetime.now())[:16],"owner":is_owner})
    low=text.lower().strip()

    if not is_owner and any(s in low for s in ["bot_token","api key","owner id","queen","password"]):
        return "Ye Malik ka secret hai.", False
    if is_owner and low in ["/report","bug report","bug batao"]:
        return f"G:{len(GROQ_KEYS)} GM:{len(GEMINI_KEYS)} O:{len(OPENAI_KEYS)} Last:{LAST_ERROR}", False
    rem=parse_reminder(text,chat_id) if is_owner else None
    if rem: return rem, False
    if is_owner and low in ["/start","start"]: return "Welcome to your world The Shadow King 👑", False
    if low in ["/start","start"]: return f"Welcome {uname}, bolo kya chahiye?", False
    if low in ["hey","hi","hello","hey!","hi malik","hey malik"]:
        return "Hey Malik, bolo kya haal hai? Kya kaam hai?", False

    if any(w in low for w in ["quiz lo","quiz karo","questions pucho","mcq","test lo"]):
        topic=text.replace("quiz lo","").strip() or "general"
        MEMORY[uid_str]["quiz_topic"]=topic; MEMORY[uid_str]["quiz_q"]=1; MEMORY[uid_str]["quiz_score"]=0
        q_prompt=f"Quiz on {topic}. Create Q1 with 4 options A,B,C,D in Roman Hinglish. End with 'Jawab A/B/C/D me do'."
        ans=ask_all(q_prompt) or f"Chalo {topic} pe Q1: 2+2? A)3 B)4 C)5 D)6"
        MEMORY[uid_str]["hist"]+=f"\nU:{text}\nR:{ans}"; save_persist(); return ans, False

    if MEMORY[uid_str].get("quiz_topic") and low in ["a","b","c","d","a)","b)","c)","d)"]:
        topic=MEMORY[uid_str]["quiz_topic"]; qnum=MEMORY[uid_str]["quiz_q"]
        eval_prompt=f"Quiz {topic} Q{qnum} answer {low}. Sahi/galat 1 line, next Q{qnum+1} pucho. 5 Q ke baad score."
        ans=ask_all(eval_prompt) or "Next..."
        MEMORY[uid_str]["quiz_q"]+=1
        if "sahi" in ans.lower(): MEMORY[uid_str]["quiz_score"]+=1
        if MEMORY[uid_str]["quiz_q"]>5:
            ans+=f"\nQuiz khatam! Score {MEMORY[uid_str]['quiz_score']}/5"; MEMORY[uid_str]["quiz_topic"]=""
        save_persist(); return ans, False

    if any(w in low for w in ["kaise karna hai","steps batao","kaise kare","explain karo"]):
        help_prompt=f"User ko chahiye: {text}. ReplyContext: {reply_context}. Short numbered steps me Roman Hinglish me batao."
        ans=ask_all(help_prompt) or "Bolo kis cheez ka step chahiye?"
        MEMORY[uid_str]["hist"]=(MEMORY[uid_str]["hist"]+f"\nU:{text}\nR:{ans}")[-2500:]; save_persist(); return ans, False

    full=f"Reply Context: {reply_context}\nHistory:{MEMORY[uid_str]['hist'][-1200:]}\nUser: {uname} Message: {text}\nInstruction: Agar Reply Context hai to usko samajh ke jawab do. Short me, naam repeat mat karo."
    ans=ask_all(full) or "Bolo kya help chahiye?"
    ans=clean(ans)
    MEMORY[uid_str]["hist"]=(MEMORY[uid_str]["hist"]+f"\nU:{text}\nR:{ans}")[-2500:]; save_persist()
    want_voice=is_owner and OWNER_PREF.get("voice_mode")
    return ans, want_voice

@app.route("/", methods=["GET"])
def home(): return f"Rakan AI Live {MALIK_NAME} G:{len(GROQ_KEYS)} O:{len(OPENAI_KEYS)} GM:{len(GEMINI_KEYS)} {ensure_webhook()}",200
@app.route("/health", methods=["GET"])
def health(): return jsonify({"groq":len(GROQ_KEYS),"openai":len(OPENAI_KEYS),"gemini":len(GEMINI_KEYS),"last_error":LAST_ERROR}),200
@app.route("/cron", methods=["GET"])
def cron_route(): n=check_reminders(); return f"Reminders:{n}",200
@app.route("/fix", methods=["GET"])
def fix():
    global GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS,BAD_KEYS
    if str(request.args.get("id",""))!=str(OWNER_ID): return "Access Denied",403
    GROQ_KEYS,GEMINI_KEYS,OPENAI_KEYS=get_keys(); BAD_KEYS.clear(); load_persist()
    return f"FIXED G:{len(GROQ_KEYS)} O:{len(OPENAI_KEYS)} GM:{len(GEMINI_KEYS)}",200
@app.route("/debug", methods=["GET"])
def debug():
    g,gm,o=get_keys(); return f"G:{len(g)} GM:{len(gm)} O:{len(o)}",200
@app.route("/webhook", methods=["POST","GET"])
def webhook():
    if request.method=="GET": return f"Webhook {ensure_webhook()}",200
    try:
        check_reminders()
        data=request.get_json(silent=True) or {}
        msg=data.get("message",{}) or data.get("edited_message",{}) or {}
        chat_id=msg.get("chat",{}).get("id"); user_id=msg.get("from",{}).get("id",0)
        uname=msg.get("from",{}).get("first_name","user"); text=msg.get("text","") or msg.get("caption","") or ""
        message_id=msg.get("message_id")
        if not chat_id: return "ok",200
        is_owner=(user_id==OWNER_ID)
        if is_owner: uname=MALIK_NAME

        # === REPLY CONTEXT FIX ===
        reply_context=""
        reply_msg=msg.get("reply_to_message")
        if reply_msg:
            rt=reply_msg.get("text","") or reply_msg.get("caption","") or ""
            rf=reply_msg.get("from",{}).get("first_name","")
            if rt: reply_context=f"User replied to '{rf}' message: '{rt}'"
            # Agar reply me photo thi to usko bhi samjho
            if reply_msg.get("photo"):
                fbytes,_=tg_get_file_bytes(reply_msg["photo"][-1]["file_id"])
                if fbytes and text:
                    vision_ans=ask_gemini_vision(fbytes, f"User asks about this replied photo: {text}. Reply Context: {reply_context}. Roman Hinglish me batao.")
                    if vision_ans: tg_send(chat_id, vision_ans, message_id); return "ok",200

        # Photo handle
        if msg.get("photo"):
            fbytes,_=tg_get_file_bytes(msg["photo"][-1]["file_id"])
            if fbytes:
                q=text if text else "Is photo me kya hai, Roman Hinglish me batao."
                if reply_context: q=f"{reply_context}\n{q}"
                vision_ans=ask_gemini_vision(fbytes,q)
                if vision_ans: tg_send(chat_id, vision_ans, message_id)
                else:
                    ans,_=brain(text,user_id,is_owner,uname,chat_id,reply_context); tg_send(chat_id,ans,message_id)
                return "ok",200

        # Video / Voice / Audio handle
        media_id=None; media_name="voice.ogg"
        if msg.get("voice"): media_id=msg["voice"]["file_id"]; media_name="voice.ogg"
        elif msg.get("audio"): media_id=msg["audio"]["file_id"]; media_name="audio.mp3"
        elif msg.get("video"): media_id=msg["video"]["file_id"]; media_name="video.mp4"
        elif msg.get("video_note"): media_id=msg["video_note"]["file_id"]; media_name="video.mp4"

        if media_id:
            audio_bytes,fp=tg_get_file_bytes(media_id)
            if fp: media_name=fp.split("/")[-1]
            if not audio_bytes: tg_send(chat_id,"File mili nahi, fir se bhejo.",message_id); return "ok",200
            # Video ho to vision bhi try karo
            if "video" in media_name or msg.get("video") or msg.get("video_note"):
                # Pehle audio transcribe
                heard=transcribe_media(audio_bytes, media_name)
                prompt_text=text if text else (heard or "Is video me kya hai batao")
                if reply_context: prompt_text=f"{reply_context}\n{prompt_text}"
                # Agar video hai to vision se bhi dekhne ki koshish
                vision_ans=ask_gemini_vision(audio_bytes, prompt_text) if len(audio_bytes)<4000000 else None
                if vision_ans: tg_send(chat_id, vision_ans, message_id); return "ok",200
                if heard:
                    ans,_=brain(heard,user_id,is_owner,uname,chat_id,reply_context); tg_send(chat_id, ans, message_id); return "ok",200
            else:
                heard=transcribe_media(audio_bytes, media_name)
                if heard:
                    if is_owner: tg_send(chat_id, f"Aapne kaha: {heard}", message_id)
                    ans,_=brain(heard,user_id,is_owner,uname,chat_id,reply_context); tg_send(chat_id, ans, message_id); return "ok",200
            tg_send(chat_id,"Awaz saaf nahi aayi, fir se bhejo.",message_id); return "ok",200

        if not text: return "ok",200
        ans,_=brain(text,user_id,is_owner,uname,chat_id,reply_context)
        tg_send(chat_id,ans,message_id)
        return "ok",200
    except Exception as e:
        print(traceback.format_exc()); return "ok",200
