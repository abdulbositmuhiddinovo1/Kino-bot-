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
    
    # Kinolar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            file_id TEXT
        )
    ''')
    
    # Foydalanuvchilar jadvali (YANGI O'ZGARISH)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
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
    user_id = message.chat.id
    
    # Foydalanuvchini bazaga saqlash (YANGI O'ZGARISH)
    conn = sqlite3.connect('movies.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

    welcome_text = (
        "✨ *Assalomu alaykum, hurmatli foydalanuvchi!*\n\n"
        "🎬 *Kinolar olamiga xush kelibsiz!*\n\n"
        "🍿 Menga kino kodini yuboring, men darhol sizga o'sha kinoni topib beraman."
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')

# Admin uchun /stat buyrug'i (YANGI O'ZGARISH)
@bot.message_handler(commands=['stat'])
def get_stats(message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect('movies.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        conn.close()
        
        bot.reply_to(
            message, 
            f"📊 **Bot statistikasi:**\n\n👥 Barcha foydalanuvchilar: **{user_count} ta**", 
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, "⚠️ Bu buyruq faqat admin uchun!")

# Admin uchun /add buyrug'i
@bot.message_handler(commands=['add'])
def start_add_movie(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.send_message(
            message.chat.id, 
            "🎬 **Yangi kino kodini kiting:**\n(Masalan: 101)", 
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_movie_code)

def process_movie_code(message):
    code = message.text.strip()
    msg = bot.send_message(message.chat.id, f"📥 Endi `{code}` kodi uchun video faylni yuboring:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_movie_video, code)

def process_movie_video(message, code):
    if message.content_type == 'video':
        file_id = message.video.file_id
        conn = sqlite3.connect('movies.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO movies (code, file_id) VALUES (?, ?)", (code, file_id))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ **Kino saqlandi!**\n🎬 Kodi: `{code}`", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Iltimos, faqat **video** yuboring!")

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
    
    # Qidiruv vaqtida ham foydalanuvchini saqlab qo'yish
    conn = sqlite3.connect('movies.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (message.chat.id,))
    cursor.execute("SELECT file_id FROM movies WHERE code = ?", (code,))
    result = cursor.fetchone()
    conn.close()

    if result:
        file_id = result[0]
        bot.send_video(
            message.chat.id, 
            file_id, 
            caption=f"🎬 *Kino kodi:* `{code}`\n✨ Yoqimli tomosha!", 
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, "❌ *Kechirasiz, bu kod bo'yicha kino topilmadi.*", parse_mode='Markdown')

# --- 5. BOTNI ISHGA TUSHIRISH (ENG OXIRIDA) ---
if __name__ == '__main__':
    print("Bot ishga tushdi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
        
