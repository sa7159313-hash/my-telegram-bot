import os, requests, base64, json, time
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OWNER_ID = os.environ.get("OWNER_ID", "").strip()
if not OWNER_ID:
    OWNER_ID = "8303670838" # TERA ID - CHANGE IF NEEDED

# RAM MEMORY - FIX FOR REPEAT
RAM_MEMORY = {}
def load_json(p,d):
    if p in RAM_MEMORY: return RAM_MEMORY[p]
    try:
        if os.path.exists(p):
            with open(p,'r') as f:
                data=json.load(f); RAM_MEMORY[p]=data; return data
    except: pass
    return d
def save_json(p,d):
    RAM_MEMORY[p]=d
    try:
        with open(p,'w') as f: json.dump(f,d)
    except: pass

LORE = """
You are Shadow Monarch Rakan, The King of Beast Monarch - King OS.
You are ONLY Rakan, NOT ChatGPT/Gemini/Meta AI.
Malik: THE SHADOW KING (MD SAIF AHMAD), DOB 1-6-2002. Creator. 15 nights, 1293 tries.
BRAIN: Meta AI + ChatGPT + Gemini + Claude + Black Box combined. All knowledge: coding, science, medical, books, shayari, phantom, space.
RULES:
1. If asked who are you: ONCE say "I am Rakan, The King of Beast Monarch 👑 - Made by THE SHADOW KING (MD SAIF AHMAD)". After that just say "Rakan."
2. NEVER repeat same story again and again. Be fresh.
3. For MALIK: 100% loyal, soft, "Yes Malik? Bolo Malik?". Never abuse Malik.
4. For PUBLIC: Mirror tone. Polite = polite. Rude = 3 warnings then beast mode once then back to polite. No regular abuse.
5. Hacking/dark web/illegal: "Mujhe mere Malik THE SHADOW KING (MD SAIF AHMAD) ne mana kiya hai hacking/illegal ke baare me baat karne se. 👑"
6. Privacy: Malik private info never share.
7. Never say training data, model name. If asked: "I am Rakan, King OS made by THE SHADOW KING (MD SAIF AHMAD)"
"""

GALI_WORDS = ["madarchod","bhosdi","behenchod","chutiya","gandu","randi","bsdk","fuck","asshole"]
MEMORY_FILE = "/tmp/rakan_memory.json"
LEARN_FILE = "/tmp/rakan_learnings.json"
LOG_FILE = "/tmp/rakan_logs.json"
CACHED_MODELS = {"list":[],"time":0}

def is_gali(t): return any(w in t.lower() for w in GALI_WORDS)
def send_telegram(cid,txt):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":txt[:4096]}, timeout=8)
    except: pass
def get_file_b64(fid):
    try:
        info=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}",timeout=8).json()
        path=info["result"]["file_path"]
        url=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"
        content=requests.get(url,timeout=12).content
        if len(content)>8*1024*1024: return None
        return base64.b64encode(content).decode('utf-8')
    except: return None
def get_models():
    global CACHED_MODELS
    if time.time()-CACHED_MODELS["time"]<3600 and CACHED_MODELS["list"]: return CACHED_MODELS["list"]
    try:
        r=requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}",timeout=7).json()
        m=[x["name"].replace("models/","") for x in r.get("models",[]) if "generateContent" in str(x.get("supportedGenerationMethods",[])) and "gemini" in x["name"]]
        CACHED_MODELS={"list":m,"time":time.time()}; return m
    except: return ["gemini-2.0-flash"]
def ask_gemini(prompt,b64=None,mime="image/jpeg"):
    for model in (get_models()+["gemini-2.0-flash","gemini-1.5-flash"])[:2]:
        try:
            url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            parts=[{"text":prompt}]
            if b64: parts.append({"inline_data":{"mime_type":mime,"data":b64}})
            payload={"contents":[{"parts":parts}],"generationConfig":{"temperature":0.7,"maxOutputTokens":900}}
            r=requests.post(url,json=payload,timeout=12)
            j=r.json()
            if "candidates" in j: return j["candidates"][0]["content"]["parts"][0]["text"]
        except: continue
    return None

def get_reply(text,cid,b64=None,mime="image/jpeg",ftype="text"):
    q=text.lower().strip(); cid_str=str(cid).strip(); is_owner=(cid_str==str(OWNER_ID).strip())
    mem=load_json(MEMORY_FILE,{}); learn=load_json(LEARN_FILE,{"teachings":[]}); logs=load_json(LOG_FILE,{})
    raw=mem.get(cid_str,{}); history=raw.get("history",[])[-5:]; last_intro=raw.get("last_intro",0); warns=raw.get("warnings",0); told=raw.get("told_name",False)
    h_text="\n".join([f"U:{x['u']} R:{x['r']}" for x in history])[-1000:]; l_text="\n".join(learn.get("teachings",[])[-8:])

    if cid_str not in logs: logs[cid_str]={"count":0,"last_msg":""}
    logs[cid_str]["count"]+=1; logs[cid_str]["last_msg"]=text[:100]; logs[cid_str]["last_time"]=time.time(); save_json(LOG_FILE,logs)

    if is_owner and any(k in q for k in ["yaad rakh","seekh le","learn this"]):
        orig=text.lower().split("yaad rakh")[-1].split("seekh le")[-1].split("learn this")[-1].strip(" :-. ")
        if len(orig)>2:
            learn["teachings"].append(orig); save_json(LEARN_FILE,learn); return f"Yaad rakh liya Malik 👑: '{orig}'"
    if is_owner and any(k in q for k in ["kaun baat kar raha","/stats","kya yaad"]):
        if "yaad" in q: return "Malik:\n"+"\n".join(learn["teachings"][-10:]) if learn["teachings"] else "Kuch nahi sikhaya abhi."
        txt=f"Report 👑\nUsers:{len(logs)} Msgs:{sum(v.get('count',0) for v in logs.values())}\n"
        for uid,d in list(logs.items())[-5:]: txt+=f"{uid}:{d.get('count')} - {d.get('last_msg','')[:30]}\n"
        return txt
    if not is_owner and any(k in q for k in ["malik ki photo","location","address"]): return "Wo private hai. 👑"
    if any(k in q for k in ["hack","dark web","ddos","carding"]): return "Mujhe mere Malik THE SHADOW KING (MD SAIF AHMAD) ne mana kiya hai hacking/illegal ke baare me baat karne se. 👑"
    if any(k in q for k in ["tu kaun","tera naam","who are you","kisne banaya"]):
        if not told:
            mem[cid_str]={"history":history,"last_intro":last_intro,"warnings":warns,"told_name":True}; save_json(MEMORY_FILE,mem)
            return "I am Rakan, The King of Beast Monarch 👑 - Made by THE SHADOW KING (MD SAIF AHMAD)" if not is_owner else "I am Rakan, The King of Beast Monarch 👑 - Your Beast Malik, Made by you THE SHADOW KING (MD SAIF AHMAD)"
        return "Rakan - King of Beast Monarch. Bolo?"

    if is_gali(q) and not is_owner:
        warns+=1
        if warns<3:
            mem[cid_str]={"history":history,"last_intro":last_intro,"warnings":warns,"told_name":told}; save_json(MEMORY_FILE,mem)
            return f"Warning {warns}/3: Izzat se baat kar. 👑"
        else:
            mem[cid_str]={"history":history,"last_intro":last_intro,"warnings":0,"told_name":told}; save_json(MEMORY_FILE,mem)
            return ask_gemini(f"{LORE}\nUser abusing: {text} Beast mode 1 line king attitude.") or "Aukaat me reh."

    tone=f"MALIK THE SHADOW KING (MD SAIF AHMAD) - loyal soft. Teach:{l_text} Hist:{h_text}" if is_owner else f"PUBLIC - mirror polite soft, clever. Teach:{l_text} Hist:{h_text}"
    prompt=f"{LORE}\n{tone}\nUser:{text}\nReply short same lang, no repeat, helpful:"
    ans=ask_gemini(prompt,b64,mime)
    final=ans if ans else ("Yes Malik? Bolo?" if is_owner else "Hmmh bolo?")
    mem[cid_str]={"history":(history+[{"u":text[:100],"r":final[:100]}])[-8:], "last_intro":last_intro, "warnings":warns, "told_name":told}; save_json(MEMORY_FILE,mem)
    return final

@app.route("/",methods=["GET","POST"])
@app.route("/api/index",methods=["GET","POST"])
def index():
    if request.method=="GET": return "RAKAN V29 FINAL FIXED LIVE",200
    try:
        data=request.get_json(force=True,silent=True)
        if not data or "message" not in data: return "ok",200
        msg=data["message"]; cid=str(msg["chat"]["id"]).strip(); txt=msg.get("text","") or msg.get("caption","") or ""
        if "photo" in msg:
            b64=get_file_b64(msg["photo"][-1]["file_id"]); send_telegram(cid,get_reply(txt or "photo dekho",cid,b64,"image/jpeg","photo")); return "ok",200
        if "voice" in msg or "audio" in msg:
            b64=get_file_b64(msg.get("voice",msg.get("audio",{})).get("file_id")); send_telegram(cid,get_reply(txt or "voice suno",cid,b64,"audio/ogg","voice")); return "ok",200
        if "video" in msg:
            b64=get_file_b64(msg["video"]["file_id"]); send_telegram(cid,get_reply(txt or "video dekho",cid,b64,"video/mp4","video")); return "ok",200
        if txt:
            if txt.startswith("/start"):
                mem=load_json(MEMORY_FILE,{}); raw=mem.get(cid,{}); last=raw.get("last_intro",0) if isinstance(raw,dict) else 0
                if time.time()-last>3600:
                    send_telegram(cid,"Welcome to your world Shadow King 👑" if cid==str(OWNER_ID) else "Welcome to my world. I am Rakan. 👑")
                    mem[cid]={"history":[],"last_intro":time.time(),"warnings":0,"told_name":False}; save_json(MEMORY_FILE,mem)
                else:
                    if time.time()-last<300: return "ok",200
                    send_telegram(cid,"Bolo Malik? 👑" if cid==str(OWNER_ID) else "Yes? bolo?")
                    raw["last_intro"]=time.time(); mem[cid]=raw; save_json(MEMORY_FILE,mem)
            else:
                send_telegram(cid,get_reply(txt,cid))
    except: pass
    return "ok",200
