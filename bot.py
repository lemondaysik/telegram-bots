import os
import threading
import time
import requests
import telebot
from flask import Flask

# Токен берём из переменной окружения.
# Локально создадим файл .env, а на Render добавим переменную BOT_TOKEN.
BOT_TOKEN = os.environ.get('BOT_TOKEN')
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL')  # Render сам подставит

if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN. Проверь переменные окружения.")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)


@app.route('/')
def index():
    return "Bot is running"


@app.route('/health')
def health():
    return "OK"


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет. Я пока в разработке")


def run_bot():
    bot.polling(none_stop=True)


# Пингер — не даёт Render усыпить бота
def keep_alive():
    while True:
        try:
            if RENDER_URL:
                requests.get(RENDER_URL)
                print("Пинганул сам себя")
        except Exception as e:
            print(f"Ошибка пинга: {e}")
        time.sleep(14 * 60)  # каждые 14 минут


if __name__ == "__main__":
    # Бот в отдельном потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # Пингер в отдельном потоке
    ping_thread = threading.Thread(target=keep_alive)
    ping_thread.daemon = True
    ping_thread.start()

    # Flask-сервер для Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)