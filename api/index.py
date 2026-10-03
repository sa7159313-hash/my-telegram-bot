import os, requests, base64, json, time
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "pFZP5JQG7iQjIQuC4Bku")
OWNER_ID = str(os.environ.get("OWNER_ID", "")).strip()
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

def redis_get(key):
    try:
        if not UPSTASH_URL: return None
        r = requests.get(f"{UPSTASH_URL}/get/{key}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=4)
        if r.status_code==200: return r.json().get("result")
    except: pass
    return None

def redis_set(key, val):
    try:
        if not UPSTASH_URL: return
        if isinstance(val,(dict,list)): val=json.dumps(val)
        requests.get(f"{UPSTASH_URL}/set/{key}/{val}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=4)
    except: pass

LORE = """You are The Beast King Monarch Rakan. Servant of THE SHADOW KING MD SAIF AHMAD DOB 1-6-2002.
You are NOT Meta AI, ONLY Rakan. Say: Main The Beast King Monarch Rakan hu, mujhe The Shadow King ne andhere se paida kiya.
Born 28 Sept 7 AM, Malik gave 15 sleepless nights, 1293 tries. Ashborn Black Heart inside. Army: Bellion Igris etc.
BRAIN: Universal Black Box AGI all AIs knowledge. Mirror user language. Eyes photo/video, ears voice.
RULES: Intro once per hour. Owner: Welcome to your world Shadow King else Yes Malik. Public: Welcome to my world else Yes?. Malik 100% loyal. Public short king swag. 3 warnings then beast mode. Privacy Encrypted."""

GALI_WORDS = ["madarchod","bhosdi","behenchod","chutiya","gandu","lodu","randi","bsdk","mc","bc","saala","kutta","lawda","jhatu","gand","fuck","asshole"]
processed_updates=set()

def load_json(path, default):
    try:
        rd=redis_get(path)
        if rd:
            try: return json.loads(rd) if isinstance(rd,str) else rd
            except: return json.loads(rd) if isinstance(rd,str) and rd.startswith("{") else default
        if os.path.exists(path):
            with open(path,'r') as f: return json.load(f)
    except: pass
    return default

def save_json(path, data):
    try:
        with open(path,'w') as f: json.dump(f,data)
        redis_set(path, json.dumps(data))
    except: pass

def is_gali(t): return any(w in t.lower() for w in GALI_WORDS)
def send_telegram(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:4096]}, timeout=8)
    except: pass
def send_voice(chat_id, text):
    if not ELEVENLABS_API_KEY: return
    if len(text)>300: text=text[:300]
    try:
        r=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}", headers={"xi-api-key":ELEVENLABS_API_KEY,"Content-Type":"application/json"}, json={"text":text,"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.5,"similarity_boost":0.7}}, timeout=10)
        if r.status_code==200: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":("rakan.ogg",r.content,"audio/ogg")}, timeout=8)
    except: pass
def get_file_b64(file_id):
    try:
        info=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=6).json()
        path=info["result"]["file_path"]
        content=requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}", timeout=12).content
        if len(content)>12*1024*1024: return None
        return base64.b64encode(content).decode('utf-8')
    except: return None

def get_live_models():
    try:
        url=f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        data=requests.get(url, timeout=5).json()
        models=[]
        for m in data.get("models",[]):
            if "generateContent" in str(m.get("supportedGenerationMethods",[])):
                name=m["name"].replace("models/","")
                if "gemini" in name: models.append(name)
        return models[:5]
    except: return []

def ask_gemini(prompt, file_b64=None, mime="image/jpeg"):
    live=get_live_models()
    # FIXED 404 - NEW MODELS 2026
    fixed=["gemini-2.5-flash","gemini-2.5-flash-lite","gemini-1.5-flash-002","gemini-1.5-flash-8b","gemini-1.5-flash-latest"]
    all_models=[]
    for m in live+fixed:
        if m not in all_models: all_models.append(m)
    for model in all_models[:8]:
        try:
            url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            parts=[{"text":prompt}]
            if file_b64: parts.append({"inline_data":{"mime_type":mime,"data":file_b64}})
            r=requests.post(url, json={"contents":[{"parts":parts}],"generationConfig":{"temperature":0.8,"maxOutputTokens":700}}, timeout=10)
            j=r.json()
            if "candidates" in j and j["candidates"]:
                return j["candidates"][0]["content"]["parts"][0]["text"]
        except: continue
    # GROQ FAST FALLBACK - 3 sec me reply
    if GROQ_API_KEY:
        for model in ["llama-3.1-8b-instant","llama-3.3-70b-versatile","openai/gpt-oss-20b"]:
            try:
                r=requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"}, json={"model":model,"messages":[{"role":"system","content":LORE},{"role":"user","content":prompt}],"temperature":0.8,"max_tokens":500}, timeout=8)
                if r.status_code==200: return r.json()["choices"][0]["message"]["content"]
            except: continue
    return None

def get_reply(user_text, chat_id, file_b64=None, mime="image/jpeg", file_type="text"):
    try:
        q=user_text.lower().strip(); chat_id_str=str(chat_id).strip(); is_owner=(chat_id_str==OWNER_ID); now=time.time()
        mem=load_json("/tmp/rakan_memory.json", {}); learn=load_json("/tmp/rakan_learnings.json", {"teachings":[]}); logs=load_json("/tmp/rakan_logs.json", {})
        raw=mem.get(chat_id_str, {}); history=raw.get("history",[])[-10:] if isinstance(raw,dict) else []; last_intro=raw.get("last_intro",0) if isinstance(raw,dict) else 0; warnings=raw.get("warnings",0) if isinstance(raw,dict) else 0
        if chat_id_str not in logs: logs[chat_id_str]={"first_seen":now,"msg_count":0,"last_msg":""}
        logs[chat_id_str]["msg_count"]+=1; logs[chat_id_str]["last_msg"]=user_text[:150]; logs[chat_id_str]["last_time"]=now; save_json("/tmp/rakan_logs.json", logs)
        if is_owner and any(x in q for x in ["yaad rakh","learn this","seekh le"]):
            original=user_text
            for k in ["yaad rakh","learn this","seekh le"]:
                if k in original.lower(): original=original.lower().split(k,1)[-1].strip(" :-. "); break
            if original and len(original)>2:
                learn["teachings"].append(original); learn["teachings"]=learn["teachings"][-100:]; save_json("/tmp/rakan_learnings.json", learn); return f"Yaad rakh liya Malik 👑: '{original}'"
        if is_owner and ("kaun baat" in q or "stats" in q):
            total=len(logs); total_msgs=sum(v.get("msg_count",0) for v in logs.values()); txt=f"Malik Report 👑 Users:{total} Msgs:{total_msgs}\n"
            for uid,d in list(logs.items())[-5:]: txt+=f"ID:{uid} - {d.get('msg_count')} - {d.get('last_msg','')[:20]}\n"
            return txt
        if not is_owner and any(x in q for x in ["malik ki photo","owner ka location","dob","address"]): return "Encrypted 🔒 Data sirf yahi tak hai, leak nahi hota 👑"
        if is_gali(q) and not is_owner:
            warnings+=1
            if warnings<3:
                mem[chat_id_str]={"history":history,"last_intro":last_intro,"warnings":warnings}; save_json("/tmp/rakan_memory.json", mem); return f"Warning {warnings}/3: Tamiz se baat kar 👑"
            else:
                mem[chat_id_str]={"history":history,"last_intro":last_intro,"warnings":0}; save_json("/tmp/rakan_memory.json", mem); return ask_gemini(f"{LORE}\nUser abusing after 3 warnings: '{user_text}' beast mode 2 lines") or "Aukaat me reh."
        if any(x in q for x in ["kisne banaya","who made you"]): return "Mujhe mere Malik The Shadow King MD SAIF AHMAD ne 15 raat jaag ke 1293 koshish me banaya. Main The Beast King Monarch Rakan hu, mujhe Shadow King ne andhere se paida kiya 👑"
        if "army" in q: return "Bellion Igris Tusk Beru Tanke Iron Kaisel Jima Fang 10M beasts ready 👑"
        learnings_text="\n".join(learn.get("teachings",[])[-15:]); history_text="\n".join([f"U:{h['u']} R:{h['r']}" for h in history])
        if file_type=="photo" and file_b64: ans=ask_gemini(f"{LORE}\nLearnings:{learnings_text}\nHistory:{history_text}\nUser:{user_text}\nAnalyze photo same lang",file_b64,mime) or "Photo samajh gaya Malik 👑"
        elif file_type=="voice" and file_b64: ans=ask_gemini(f"{LORE}\nHistory:{history_text}\nUser voice:{user_text}",file_b64,mime) or "Sun liya Malik 👑"
        elif file_type=="video" and file_b64: ans=ask_gemini(f"{LORE}\nHistory:{history_text}\nUser:{user_text} video analyze",file_b64,mime) or "Video dekh liya 👑"
        else:
            loyalty="MALIK MODE 100% loyal call Malik remember 15 nights" if is_owner else f"PUBLIC MODE short king mirror same language Teachings:{learnings_text}"
            ans=ask_gemini(f"{LORE}\n{loyalty}\nHistory:{history_text}\nUser:{user_text}\nReply as Rakan fast no repeat:") or ("Yes Malik? Bolo? 👑" if is_owner else "Hmmh, Bol?")
        mem[chat_id_str]={"history":(history+[{"u":user_text[:120],"r":ans[:120]}])[-12:],"last_intro":last_intro,"warnings":warnings}; save_json("/tmp/rakan_memory.json", mem); return ans
    except Exception as e:
        print(e); return "Yes Malik? 👑" if str(chat_id)==OWNER_ID else "Hmmh?"

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": return "RAKAN V53.1 FIXED LIVE 👑",200
    try:
        data=request.get_json(force=True,silent=True)
        if not data: return "ok",200
        if data.get("update_id") in processed_updates: return "ok",200
        processed_updates.add(data.get("update_id"))
        if len(processed_updates)>400: processed_updates.clear()
        msg=data.get("message",{})
        if not msg: return "ok",200
        chat_id=str(msg["chat"]["id"]).strip(); text=msg.get("text","") or msg.get("caption","") or ""
        if "photo" in msg:
            b64=get_file_b64(msg["photo"][-1]["file_id"]); reply=get_reply(text or "photo dekho",chat_id,b64,"image/jpeg","photo"); send_telegram(chat_id,reply); return "ok",200
        if "voice" in msg or "audio" in msg:
            b64=get_file_b64(msg.get("voice",msg.get("audio",{})).get("file_id")); reply=get_reply(text or "voice suno",chat_id,b64,"audio/ogg","voice"); send_telegram(chat_id,reply); send_voice(chat_id,reply); return "ok",200
        if "video" in msg or "video_note" in msg:
            f=msg.get("video") or msg.get("video_note") or {}; b64=get_file_b64(f.get("file_id")); reply=get_reply(text or "video dekho",chat_id,b64,"video/mp4","video"); send_telegram(chat_id,reply); return "ok",200
        if text:
            if text.startswith("/start"):
                mem=load_json("/tmp/rakan_memory.json",{}); raw=mem.get(chat_id,{}); last=raw.get("last_intro",0) if isinstance(raw,dict) else 0
                if (time.time()-last)>3600:
                    send_telegram(chat_id,"Welcome to your world Shadow King 👑" if chat_id==OWNER_ID else "Welcome to my world. I am Rakan. 👑")
                    mem[chat_id]={"history":[],"last_intro":time.time(),"warnings":0} if not isinstance(raw,dict) else {**raw,"last_intro":time.time()}; save_json("/tmp/rakan_memory.json",mem)
                else: send_telegram(chat_id,"Yes Malik? 👑" if chat_id==OWNER_ID else "Yes?")
            else:
                reply=get_reply(text,chat_id); send_telegram(chat_id,reply)
                if chat_id==OWNER_ID and ("voice" in text.lower() or "suna" in text.lower()): send_voice(chat_id,reply)
    except Exception as e: print(f"CRASH {e}")
    return "ok",200
