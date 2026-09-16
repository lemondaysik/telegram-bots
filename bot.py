import os
import threading
import time
import requests
import telebot
from flask import Flask
from datetime import datetime

BOT_TOKEN = os.environ.get('BOT_TOKEN')
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL')

if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN. Проверь переменные окружения.")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

start_time = datetime.now()
messages_count = 0


@app.route('/')
def index():
    return "Bot is running"


@app.route('/health')
def health():
    return "OK"


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет. Я пока в разработке")


@bot.message_handler(commands=['pidor'])
def send_pidor(message):
    bot.reply_to(message, "Гандон живо домой")


@bot.message_handler(commands=['status'])
def send_status(message):
    global messages_count
    
    uptime = datetime.now() - start_time
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    
    status_text = (
        f"📊 *Статус бота:*\n\n"
        f"✅ Статус: Работает\n"
        f"⏱ Время работы: {hours}ч {minutes}мин\n"
        f"📨 Обработано сообщений: {messages_count}\n"
        f"🕐 Текущее время: {datetime.now().strftime('%H:%M:%S')}"
    )
    bot.reply_to(message, status_text, parse_mode="Markdown")


@bot.message_handler(func=lambda message: True)
def count_messages(message):
    global messages_count
    messages_count += 1


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
