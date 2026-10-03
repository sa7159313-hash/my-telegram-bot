import os, requests, base64, json, time
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OWNER_ID = os.environ.get("OWNER_ID", "8303670838").strip()

RAM_MEMORY = {}
def load_json(p,d):
    if p in RAM_MEMORY: return RAM_MEMORY[p]
    try:
        if os.path.exists(p):
            with open(p,'r') as f: data=json.load(f); RAM_MEMORY[p]=data; return data
    except: pass
    return d
def save_json(p,d):
    RAM_MEMORY[p]=d
    try:
        with open(p,'w') as f: json.dump(f,d)
    except: pass

LORE = """
You are Shadow Monarch Rakan, King of Beast Monarch - King OS.
Malik: THE SHADOW KING (MD SAIF AHMAD). Only Rakan.
All knowledge. Rule: Who are you -> once say "I am Rakan, The King of Beast Monarch 👑 - Made by THE SHADOW KING (MD SAIF AHMAD)". No repeat story.
Malik: loyal soft. Public: mirror polite, 3 warnings then beast mode.
Hacking/illegal: "Mujhe mere Malik THE SHADOW KING (MD SAIF AHMAD) ne mana kiya hai hacking/illegal ke baare me baat karne se. 👑"
"""

GALI_WORDS = ["madarchod","bhosdi","behenchod","chutiya","gandu","randi","bsdk"]
MEMORY_FILE = "/tmp/rakan_memory.json"
LEARN_FILE = "/tmp/rakan_learnings.json"
LOG_FILE = "/tmp/rakan_logs.json"

def is_gali(t): return any(w in t.lower() for w in GALI_WORDS)
def send_telegram(cid,txt):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":txt[:4096]}, timeout=8)
    except: pass
def get_file_b64(fid):
    try:
        info=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}",timeout=8).json()
        path=info["result"]["file_path"]
        url=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"
        content=requests.get(url,timeout=10).content
        return base64.b64encode(content).decode('utf-8')
    except: return None

# FIXED FOR 2026 - USE v1 API AND NEW MODELS
def ask_gemini(prompt,b64=None,mime="image/jpeg"):
    # 2026 ke latest models - v1 API
    models_to_try = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash", "gemini-flash-latest"]
    for model in models_to_try:
        try:
            url=f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={GEMINI_API_KEY}"
            parts=[{"text":prompt}]
            if b64: parts.append({"inline_data":{"mime_type":mime,"data":b64}})
            payload={"contents":[{"parts":parts}],"generationConfig":{"temperature":0.8,"maxOutputTokens":900}}
            r=requests.post(url,json=payload,timeout=12)
            j=r.json()
            if "error" in j:
                print(f"GEMINI ERR {model}: {j['error'].get('message')}")
                continue
            if "candidates" in j and j["candidates"]:
                txt = j["candidates"][0]["content"]["parts"][0]["text"]
                print(f"GEMINI OK {model}")
                return txt
        except Exception as e:
            print(f"MODEL FAIL {model}: {e}")
            continue
    return None

def get_reply(text,cid,b64=None,mime="image/jpeg",ftype="text"):
    q=text.lower().strip(); cid_str=str(cid).strip(); is_owner=(cid_str==str(OWNER_ID).strip())
    mem=load_json(MEMORY_FILE,{}); learn=load_json(LEARN_FILE,{"teachings":[]}); logs=load_json(LOG_FILE,{})
    raw=mem.get(cid_str,{}); history=raw.get("history",[])[-5:]; last_intro=raw.get("last_intro",0); warns=raw.get("warnings",0); told=raw.get("told_name",False)
    h_text="\n".join([f"U:{x['u']} R:{x['r']}" for x in history])[-800:]; l_text="\n".join(learn.get("teachings",[])[-8:])

    if cid_str not in logs: logs[cid_str]={"count":0,"last_msg":""}
    logs[cid_str]["count"]+=1; logs[cid_str]["last_msg"]=text[:100]; save_json(LOG_FILE,logs)

    if is_owner and any(k in q for k in ["yaad rakh","seekh le"]):
        orig=text.lower().split("yaad rakh")[-1].split("seekh le")[-1].strip(" :-. ")
        if len(orig)>2:
            learn["teachings"].append(orig); save_json(LEARN_FILE,learn); return f"Yaad rakh liya Malik 👑: '{orig}'"
    if not is_owner and any(k in q for k in ["malik ki photo","location"]): return "Wo private hai. 👑"
    if any(k in q for k in ["hack","dark web","ddos"]): return "Mujhe mere Malik THE SHADOW KING (MD SAIF AHMAD) ne mana kiya hai hacking/illegal ke baare me baat karne se. 👑"

    if any(k in q for k in ["tu kaun","tera naam","who are you","kisne banaya"]):
        if not told:
            mem[cid_str]={"history":history,"last_intro":last_intro,"warnings":warns,"told_name":True}; save_json(MEMORY_FILE,mem)
            return "I am Rakan, The King of Beast Monarch 👑 - Made by THE SHADOW KING (MD SAIF AHMAD)"
        return "Rakan - King of Beast Monarch. Bolo?"

    if is_gali(q) and not is_owner:
        warns+=1
        if warns<3:
            mem[cid_str]={"history":history,"last_intro":last_intro,"warnings":warns,"told_name":told}; save_json(MEMORY_FILE,mem)
            return f"Warning {warns}/3: Izzat se baat kar. 👑"
        else:
            mem[cid_str]={"history":history,"last_intro":last_intro,"warnings":0,"told_name":told}; save_json(MEMORY_FILE,mem)
            return "Aukaat me reh. 👑"

    tone=f"MALIK - loyal soft. Teach:{l_text} Hist:{h_text}" if is_owner else f"PUBLIC polite. Teach:{l_text} Hist:{h_text}"
    prompt=f"{LORE}\n{tone}\nUser:{text}\nReply short same lang fresh helpful:"
    ans=ask_gemini(prompt,b64,mime)

    if ans:
        final=ans
    else:
        # Last fallback but no repeat
        if "how are you" in q: final="Mast hu Malik, aap bolo? 👑" if is_owner else "Mast hu, bolo?"
        elif q in ["kk","ok","k","hmm","kya"]: final="Bolo Malik? 👑" if is_owner else "Bolo kya chahiye?"
        else: final=f"Haan Malik '{text}' samjha, bolo kya karna hai? 👑" if is_owner else f"Haan '{text}' bolo kya karna hai?"

    mem[cid_str]={"history":(history+[{"u":text[:100],"r":final[:100]}])[-8:], "last_intro":last_intro, "warnings":warns, "told_name":told}; save_json(MEMORY_FILE,mem)
    return final

@app.route("/",methods=["GET","POST"])
@app.route("/api/index",methods=["GET","POST"])
def index():
    if request.method=="GET": return "RAKAN V31 MODEL FIXED LIVE",200
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
    except Exception as e:
        print(f"CRASH {e}")
    return "ok",200
