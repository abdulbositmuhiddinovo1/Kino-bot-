import os
import sqlite3
import telebot
from flask import Flask
from threading import Thread

# --- 1. SOZLAMALAR ---
TOKEN = "8699655001:AAHMfemLFXxWcN6ZvJU6D6Mzw9DyJxLuObg"
ADMIN_ID = 8078471553

bot = telebot.TeleBot(TOKEN)

# --- 2. MA'LUMOTLAR BAZASINI YARATISH ---
def init_db():
    conn = sqlite3.connect('movies.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            file_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- 3. FLASK WEB SERVER (Render port xatosi bermasligi uchun) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot ishlayapti!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_flask).start()

# --- 4. TELEGRAM BOT HANDLERLARI ---

# /start buyrug'i
@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = (
        "✨ *Assalomu alaykum, hurmatli foydalanuvchi!*\n\n"
        "🎬 *Kinolar olamiga xush kelibsiz!*\n\n"
        "🍿 Menga kino kodini yuboring, men darhol sizga o'sha kinoni topib beraman."
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')

# Admin uchun /add buyrug'i
@bot.message_handler(commands=['add'])
def start_add_movie(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "🎬 **Yangi kino kodini kiriting:**\n(Masalan: 101)", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_movie_code)
    else:
        bot.send_message(message.chat.id, "Siz admin emassiz!")

def process_movie_code(message):
    movie_code = message.text.strip()
    msg = bot.send_message(message.chat.id, f"✅ Kod `{movie_code}` qabul qilindi.\n\nEndi kinoning **videosini yoki faylini** yuboring:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_movie_video, movie_code)

def process_movie_video(message, movie_code):
    if message.content_type == 'video':
        file_id = message.video.file_id
    elif message.content_type == 'document':
        file_id = message.document.file_id
    else:
        bot.send_message(message.chat.id, "❌ Iltimos, faqat video yoki fayl yuboring!")
        return

    conn = sqlite3.connect('movies.db', check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO movies (code, file_id) VALUES (?, ?)", (movie_code, file_id))
        conn.commit()
        bot.send_message(message.chat.id, f"🎉 **Kino saqlandi!**\nKodi: `{movie_code}`", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"Xatolik yuz berdi: {e}")
    finally:
        conn.close()

# Oddiy video kelganda (caption'da kodi bo'lsa) saqlash
@bot.message_handler(content_types=['video'])
def add_movie_by_caption(message):
    if message.from_user.id == ADMIN_ID and message.caption:
        code = message.caption.strip()
        file_id = message.video.file_id
        
        conn = sqlite3.connect('movies.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO movies (code, file_id) VALUES (?, ?)", (code, file_id))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ **Kino saqlandi!**\n🎬 Kodi: `{code}`", parse_mode='Markdown')

# Kinoni kodi bo'yicha qidirish (Eng oxirida turishi shart)
@bot.message_handler(func=lambda message: True)
def search_movie(message):
    code = message.text.strip()
    
    conn = sqlite3.connect('movies.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT file_id FROM movies WHERE code = ?", (code,))
    result = cursor.fetchone()
    conn.close()

    if result:
        file_id = result[0]
        bot.send_video(message.chat.id, file_id, caption=f"🎬 *Kino kodi:* `{code}`\n✨ Yoqimli tomosha!", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ *Kechirasiz, bu kod bo'yicha kino topilmadi.*", parse_mode='Markdown')

# --- 5. BOTNI ISHGA TUSHIRISH (ENG OXIRIDA) ---
if __name__ == '__main__':
    print("Bot ishga tushdi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
