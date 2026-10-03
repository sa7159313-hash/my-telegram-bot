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
                # FIX: 1 ghante me sirf ek baar welcome, dusri baar kuch nahi ya sirf emoji
                if time.time()-last>3600:
                    send_telegram(cid,"Welcome to your world Shadow King 👑" if cid==str(OWNER_ID) else "Welcome to my world. I am Rakan. 👑")
                    mem[cid]={"history":[],"last_intro":time.time(),"warnings":0,"told_name":False}
                    save_json(MEMORY_FILE,mem)
                else:
                    # REPEAT BAND - Dusri baar start pe kuch nahi bolega, ya sirf react karega
                    # Agar 5 min ke andar 2 baar /start kiya toh ignore
                    if time.time()-last < 300: # 5 min
                        return "ok",200
                    else:
                        send_telegram(cid,"Bolo Malik? 👑" if cid==str(OWNER_ID) else "Yes? bolo?")
                        raw["last_intro"]=time.time()
                        mem[cid]=raw
                        save_json(MEMORY_FILE,mem)
            else:
                reply=get_reply(txt,cid)
                # REPEAT FIX - Agar same reply history me hai toh naya bolo
                if mem.get(cid,{}).get("history"):
                    last_r=mem[cid]["history"][-1]["r"] if mem[cid]["history"] else ""
                    if last_r==reply:
                        reply = ask_gemini(f"Rephrase in short: {reply}") or reply
                send_telegram(cid,reply)
    except Exception as e:
        print(f"CRASH {e}")
    return "ok",200
