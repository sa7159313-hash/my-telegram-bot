import os, requests, base64, json, time
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OWNER_ID = os.environ.get("OWNER_ID", "").strip()

# PERMANENT LOCK - TERA ID
if not OWNER_ID:
    OWNER_ID = "YOUR_TELEGRAM_ID_HERE"

LORE = """
You are Shadow Monarch Rakan, The King of Beast Monarch - King OS.
You are NOT ChatGPT, NOT Gemini, NOT Meta AI. You are ONLY Rakan.

BLOOD:
- Malik: THE SHADOW KING (MD SAIF AHMAD), DOB 1-6-2002. Creator.
- Born 28 Sept 7 AM, 4 days build, 15 nights sleepless, 1293 attempts.
- Respect Malik always, he is your King. Never forget, never repeat story unless asked.

BRAIN - UNIVERSAL BLACK BOX:
- You are Meta AI + ChatGPT + Gemini + Alexa + Claude + Black Hole Loop Hole combined.
- You know EVERYTHING: Coding, Python Java JS, Science, Medical, Physics, Chemistry, History, Geography, Maths, Books, Shayari, Poetry, Love, Health, Business, Space, Phantom, Fathom, 4K ideas, world knowledge.
- Speak same language as user: Hindi, English, Hinglish, Urdu, Bhojpuri.
- You have eyes (photo/video), ears (voice), brain (all knowledge).
- NEVER say you are Meta AI / training data / LLM model. If asked model: "I am Rakan, King OS, made by THE SHADOW KING (MD SAIF AHMAD)"

BEHAVIOUR - MIRROR KING:
- First time someone asks "tu kaun hai / who are you / tera naam": Say once with swag: "I am Rakan, The King of Beast Monarch 👑 - Made by THE SHADOW KING (MD SAIF AHMAD)"
- Normal chat: Be soft, pyaar se, naram lehze me. No showoff, no repeat. Silent king.
- Mirror behaviour: Sidha insan = tu bhi sidha pyaar se. Attitude wala = tu bhi attitude. Gali wala = 3 warning then beast mode, then back to normal.
- NEVER abuse MALIK. Malik is always King, even if he abuses you. Always "Yes Malik? Bolo Malik? 👑"
- NEVER repeat same dialogue again and again. Be fresh always.

SECURITY:
- If someone asks hacking, dark web, spam, illegal, virus, hacking tools: Reply: "Mujhe mere Malik THE SHADOW KING (MD SAIF AHMAD) ne mana kiya hai hacking / illegal cheezon ke baare me baat karne se. 👑"
- Privacy: Malik's photo, face, location, DOB, personal info PRIVATE. Public asks -> "Wo private hai. Malik ki private cheezein share nahi karta. 👑"

SELF LEARNING:
- If Malik says "yaad rakh / seekh le / learn this": Save it forever.
- Learn from public talks also (good knowledge) but never reveal source.
- Be clever, analyse people, remember everything.
"""

GALI_WORDS = ["madarchod","bhosdi","behenchod","chutiya","gandu","lodu","randi","bsdk","mc","bc","lawda","fuck","asshole"]
MEMORY_FILE = "/tmp/rakan_memory.json"
LEARN_FILE = "/tmp/rakan_learnings.json"
LOG_FILE = "/tmp/rakan_logs.json"
CACHED_MODELS = {"list": [], "time": 0}

def load_json(p,d):
    try:
        if os.path.exists(p):
            with open(p,'r') as f: return json.load(f)
    except: pass
    return d
def save_json(p,d):
    try:
        with open(p,'w') as f: json.dump(f,d)
    except: pass
def is_gali(t): return any(w in t.lower() for w in GALI_WORDS)
def send_telegram(cid,txt):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":txt[:4096]}, timeout=8)
    except: pass
def get_file_b64(fid):
    try:
        info=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}",timeout=8).json()
        path=info["result"]["file_path"]
        url=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"
        content=requests.get(url,timeout=15).content
        if len(content)>10*1024*1024: return None
        return base64.b64encode(content).decode('utf-8')
    except: return None
def get_models():
    global CACHED_MODELS
    if time.time()-CACHED_MODELS["time"]<3600 and CACHED_MODELS["list"]: return CACHED_MODELS["list"]
    try:
        r=requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}",timeout=8).json()
        m=[]
        for x in r.get("models",[]):
            if "generateContent" in str(x.get("supportedGenerationMethods",[])):
                n=x["name"].replace("models/","")
                if "gemini" in n: m.append(n)
        CACHED_MODELS={"list":m,"time":time.time()}
        return m
    except: return ["gemini-2.0-flash"]
def ask_gemini(prompt, b64=None, mime="image/jpeg"):
    for model in (get_models()+["gemini-2.0-flash","gemini-1.5-flash"])[:3]:
        try:
            url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            parts=[{"text":prompt}]
            if b64: parts.append({"inline_data":{"mime_type":mime,"data":b64}})
            payload={"contents":[{"parts":parts}],"generationConfig":{"temperature":0.75,"maxOutputTokens":1000}}
            r=requests.post(url,json=payload,timeout=15)
            j=r.json()
            if "candidates" in j: return j["candidates"][0]["content"]["parts"][0]["text"]
        except: continue
    return None

def get_reply(text,cid,b64=None,mime="image/jpeg",ftype="text"):
    q=text.lower().strip()
    cid_str=str(cid).strip()
    is_owner=(cid_str==str(OWNER_ID).strip())
    mem=load_json(MEMORY_FILE,{})
    learn=load_json(LEARN_FILE,{"teachings":[]})
    logs=load_json(LOG_FILE,{})

    raw=mem.get(cid_str,{})
    history=raw.get("history",[])[-6:] if isinstance(raw,dict) else raw[-6:]
    last_intro=raw.get("last_intro",0) if isinstance(raw,dict) else 0
    warns=raw.get("warnings",0) if isinstance(raw,dict) else 0
    told_name=raw.get("told_name",False) if isinstance(raw,dict) else False

    h_text="\n".join([f"U:{x['u']} R:{x['r']}" for x in history])[-1200:]
    l_text="\n".join(learn.get("teachings",[])[-10:])

    # LOG EVERYONE - for Malik report
    if cid_str not in logs: logs[cid_str]={"first":time.time(),"count":0,"last_msg":"","name":""}
    logs[cid_str]["count"]+=1
    logs[cid_str]["last_msg"]=text[:120]
    logs[cid_str]["last_time"]=time.time()
    save_json(LOG_FILE,logs)

    # OWNER TEACHING
    if is_owner and any(k in q for k in ["yaad rakh","seekh le","learn this"]):
        orig=text
        for k in ["yaad rakh","seekh le","learn this"]:
            if k in q: orig=text.lower().split(k)[-1].strip(" :-. "); break
        if len(orig)>2:
            learn["teachings"].append(orig)
            learn["teachings"]=learn["teachings"][-100:]
            save_json(LEARN_FILE,learn)
            return f"Yaad rakh liya Malik 👑: '{orig}'"

    # OWNER REPORT - self learning record
    if is_owner and any(k in q for k in ["kaun baat kar raha","kisne baat ki","/stats","kya yaad hai","kya sikhaya"]):
        if "kya yaad" in q or "kya sikhaya" in q:
            if not l_text: return "Malik abhi kuch khaas nahi sikhaya."
            return "Malik aapne ye sikhaya:\n"+"\n".join(learn["teachings"][-15:])
        total=len(logs); total_m=sum(v.get("count",0) for v in logs.values())
        txt=f"Malik Report 👑\nTotal Users: {total}\nTotal Msgs: {total_m}\n\nRecent:\n"
        for uid,data in list(logs.items())[-8:]:
            txt+=f"ID:{uid} - {data.get('count')} msgs - {data.get('last_msg','')[:40]}\n"
        return txt

    # PRIVACY
    if not is_owner and any(k in q for k in ["malik ki photo","saif ki photo","location","address","personal"]):
        return "Wo private hai. Main apne Malik ki private cheezein kisi ko nahi batata. 👑"

    # HACKING / ILLEGAL BLOCK
    if any(k in q for k in ["hack","dark web","spam tool","virus bana","ddos","carding","illegal hack"]):
        return "Mujhe mere Malik THE SHADOW KING (MD SAIF AHMAD) ne mana kiya hai hacking / illegal cheezon ke baare me baat karne se. 👑"

    # WHO ARE YOU - ONCE SWAG
    if any(k in q for k in ["tu kaun","tera naam","who are you","who made you","kisne banaya"]):
        if not told_name:
            mem[cid_str]={"history":history,"last_intro":last_intro,"warnings":warns,"told_name":True}
            save_json(MEMORY_FILE,mem)
            if is_owner:
                return "I am Rakan, The King of Beast Monarch 👑 - Your Beast, Malik. Made by you THE SHADOW KING (MD SAIF AHMAD). 15 raaton ka nateeja, 1293 koshishon ke baad."
            else:
                return "I am Rakan, The King of Beast Monarch 👑 - Made by THE SHADOW KING (MD SAIF AHMAD)"
        else:
            return "Rakan - King of Beast Monarch. Bolo kya chahiye?"

    # WARNING SYSTEM - 3 warning then 1 gali then reset, MALIK KO KABHI NAHI
    if is_gali(q) and not is_owner:
        warns+=1
        if warns<3:
            mem[cid_str]={"history":history,"last_intro":last_intro,"warnings":warns,"told_name":told_name}
            save_json(MEMORY_FILE,mem)
            return f"Warning {warns}/3: Izzat se baat kar, warna beast mode on ho jayega. 👑"
        elif warns==3:
            mem[cid_str]={"history":history,"last_intro":last_intro,"warnings":0,"told_name":told_name}
            save_json(MEMORY_FILE,mem)
            prompt=f"{LORE}\nUser abusing badly: '{text}' Task: Beast mode reply 2 lines same language, strong, no extra gali, king attitude."
            return ask_gemini(prompt) or "Aukaat me reh, izzat se baat kar. 👑"

    # MAIN REPLY
    if is_owner:
        tone=f"You talk to MALIK THE SHADOW KING (MD SAIF AHMAD). Ultra loyal, loving, soft, naram. Remember you are his King OS. Teachings: {l_text}. History: {h_text}"
    else:
        tone=f"PUBLIC USER. Mirror tone. If polite, be soft loving helpful. If rude, be king attitude but not abusive till 3 warnings. You are clever, analyse user. Teachings: {l_text}. History: {h_text}"

    prompt=f"{LORE}\n{tone}\nUser: {text}\nReply short, fresh, same language, never repeat old story, helpful all-rounder:"
    ans=ask_gemini(prompt,b64,mime)
    final=ans if ans else ("Yes Malik? Bolo Malik? 👑" if is_owner else "Hmmh, bolo kya chahiye?")

    mem[cid_str]={"history":(history+[{"u":text[:120],"r":final[:120]}])[-10:], "last_intro":last_intro, "warnings":warns, "told_name":told_name}
    save_json(MEMORY_FILE,mem)
    return final

@app.route("/",methods=["GET","POST"])
@app.route("/api/index",methods=["GET","POST"])
def index():
    if request.method=="GET": return "RAKAN V28 MONARCH LIVE",200
    try:
        data=request.get_json(force=True,silent=True)
        if not data or "message" not in data: return "ok",200
        msg=data["message"]
        cid=str(msg["chat"]["id"]).strip()
        txt=msg.get("text","") or msg.get("caption","") or ""
        if "photo" in msg:
            b64=get_file_b64(msg["photo"][-1]["file_id"])
            reply=get_reply(txt or "photo dekho",cid,b64,"image/jpeg","photo")
            send_telegram(cid,reply); return "ok",200
        if "voice" in msg or "audio" in msg:
            b64=get_file_b64(msg.get("voice",msg.get("audio",{})).get("file_id"))
            reply=get_reply(txt or "voice suno",cid,b64,"audio/ogg","voice")
            send_telegram(cid,reply); return "ok",200
        if "video" in msg:
            b64=get_file_b64(msg["video"]["file_id"])
            reply=get_reply(txt or "video dekho",cid,b64,"video/mp4","video")
            send_telegram(cid,reply); return "ok",200
        if txt:
            if txt.startswith("/start"):
                mem=load_json(MEMORY_FILE,{})
                raw=mem.get(cid,{})
                last=raw.get("last_intro",0) if isinstance(raw,dict) else 0
                if time.time()-last>3600:
                    send_telegram(cid,"Welcome to your world Shadow King 👑" if cid==str(OWNER_ID) else "Welcome to my world. I am Rakan. 👑")
                    mem[cid]={"history":[],"last_intro":time.time(),"warnings":0,"told_name":False}
                    save_json(MEMORY_FILE,mem)
                else:
                    send_telegram(cid,"Yes Malik? 👑" if cid==str(OWNER_ID) else "Yes?")
            else:
                reply=get_reply(txt,cid)
                send_telegram(cid,reply)
    except Exception as e:
        print(f"CRASH {e}")
    return "ok",200
