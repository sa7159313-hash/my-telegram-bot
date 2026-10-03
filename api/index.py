import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from groq import Groq
from openai import OpenAI
from upstash_redis import Redis

# --- TERI DETAILS - ENV SE ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
OPENAI_KEY = os.getenv("OPEN_API_KEY") # Tune OPEN likha hai Vercel me, wahi use kar raha hu
GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Redis
redis = Redis(url=os.getenv("UPSTASH_REDIS_REST_URL"), token=os.getenv("UPSTASH_REDIS_REST_TOKEN"))

# Clients
client_groq = Groq(api_key=GROQ_KEY)
client_openai = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None
genai.configure(api_key=GEMINI_KEY)

async def get_ai_reply(prompt):
    # 1. Try OpenAI (agar billing hai to chalega)
    try:
        if client_openai:
            res = client_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user", "content": prompt}]
            )
            return res.choices[0].message.content
    except Exception as e:
        print(f"OpenAI Fail: {e}")

    # 2. Fallback to GROQ (Free & Fast)
    try:
        res = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user", "content": prompt}]
        )
        return res.choices[0].message.content
    except Exception as e:
        print(f"Groq Fail: {e}")

    # 3. Final Fallback to Gemini
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(prompt)
        return res.text
    except Exception as e:
        return f"Error Malik: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Ha Malik! Bot Online Hai ✅\nOwner ID: {OWNER_ID}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    reply = await get_ai_reply(prompt)
    await update.message.reply_text(reply)

# Vercel ke liye Application
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def main(request):
    # Vercel webhook handler
    await app.initialize()
    await app.process_update(Update.de_json(request.get_json(force=True), app.bot))
    return "ok"
