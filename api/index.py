import os
from flask import Flask, request
import google.generativeai as genai
import telebot

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    try:
        # Hinglish ultimate prompt
        prompt = f"""You are a friendly Hinglish AI. Reply in mix Hindi+English, cool, friendly.
        User: {message.text}"""
        response = model.generate_content(prompt)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Error aaya KING: {e}")

@app.route('/', methods=['GET'])
def home():
    return "Bot Running - KING 👑"

@app.route('/', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok"

# Vercel needs this
app = app
