import os
import threading
import time
import requests
import telebot
from flask import Flask
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.environ.get('BOT_TOKEN')
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL')

if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN. Проверь переменные окружения.")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

start_time = datetime.now(timezone(timedelta(hours=5)))
messages_count = 0


@app.route('/')
def index():
    return "Bot is running"


@app.route('/health')
def health():
    return "OK"


@bot.message_handler(commands=['start'])
def send_welcome(message):
    global messages_count
    messages_count += 1
    response = (
        "Сапчик! Вот мои команды:\n\n"
        "/start - Показать этот список\n"
        "/pidor - Специальная команда\n"
        "/status - Статус работы бота"
    )
    bot.reply_to(message, response)


@bot.message_handler(commands=['pidor'])
def send_pidor(message):
    global messages_count
    messages_count += 1
    bot.reply_to(message, "Гандон живо домой")


@bot.message_handler(commands=['status'])
def send_status(message):
    global messages_count
    messages_count += 1
    
    now = datetime.now(timezone(timedelta(hours=5)))
    uptime = now - start_time
    total_seconds = int(uptime.total_seconds())
    
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 8600) // 60
    
    status_text = (
        f"📊 *Статус бота:*\n\n"
        f"✅ Статус: Работает\n"
        f"⏱ Время работы: {days}д {hours}ч {minutes}мин\n"
        f"📨 Обработано сообщений: {messages_count}\n"
        f"🕐 Текущее время (Екб): {now.strftime('%H:%M:%S')}"
    )
    bot.reply_to(message, status_text, parse_mode="Markdown")


@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    global messages_count
    messages_count += 1
    
    if message.content_type == 'text':
        text = message.text.lower().strip()
        username = message.from_user.username or ""
        
        if username in ["sh0ck85", "ttaeart"] and text == "даров, даров":
            bot.reply_to(message, "даров красавчик")
        elif text in ["здравствуйте", "привет"]:
            bot.reply_to(message, "Здравствуйте! Рад вас видеть.")
        elif text == "как дела?":
            bot.reply_to(message, "У меня всё отлично, спасибо! А у вас?")
        elif text == "что делаешь?":
            bot.reply_to(message, "Работаю, обрабатываю сообщения и жду новых команд!")


def run_bot():
    bot.polling(none_stop=True)


def keep_alive():
    while True:
        try:
            if RENDER_URL:
                requests.get(RENDER_URL, timeout=5)
                print("Пинганул сам себя")
        except Exception as e:
            print(f"Ошибка пинга: {e}")
        time.sleep(14 * 60) 


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    ping_thread = threading.Thread(target=keep_alive)
    ping_thread.daemon = True
    ping_thread.start()

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
