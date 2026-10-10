import os
import threading
import time
import random
import requests
import telebot
import redis
from flask import Flask
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.environ.get('BOT_TOKEN')
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL')
REDIS_URL = os.environ.get('REDIS_URL')

if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

r = None
if REDIS_URL:
    r = redis.from_url(REDIS_URL, decode_responses=True)

start_time = datetime.now(timezone(timedelta(hours=5)))
messages_count = 0


def get_users():
    if not r:
        return []
    try:
        return list(r.smembers('bot_users'))
    except Exception as e:
        print(f"Redis get_users error: {e}")
        return []


def save_user(user_id):
    if not r:
        return
    try:
        r.sadd('bot_users', str(user_id))
    except Exception as e:
        print(f"Redis save_user error: {e}")


def remove_user(user_id):
    if not r:
        return
    try:
        r.srem('bot_users', str(user_id))
    except Exception as e:
        print(f"Redis remove_user error: {e}")


def get_last_gid():
    if not r:
        return ""
    try:
        return r.get('last_dota_news_gid') or ""
    except Exception as e:
        print(f"Redis get_last_gid error: {e}")
        return ""


def save_last_gid(gid):
    if not r:
        return
    try:
        r.set('last_dota_news_gid', gid)
    except Exception as e:
        print(f"Redis save_last_gid error: {e}")


def check_dota_news():
    while True:
        try:
            url = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=570&count=1&format=json"
            response = requests.get(url, timeout=10)
            data = response.json()

            if 'appnews' in data and 'newsitems' in data['appnews'] and len(data['appnews']['newsitems']) > 0:
                latest_news = data['appnews']['newsitems'][0]
                gid = latest_news['gid']
                last_gid = get_last_gid()

                if gid != last_gid:
                    title = latest_news['title']
                    url_news = latest_news.get('url', '')
                    date = datetime.fromtimestamp(
                        latest_news['date'], tz=timezone(timedelta(hours=5))
                    ).strftime('%d.%m.%Y %H:%M')

                    message = (
                        f"🔥 *Новое обновление Dota 2!*\n\n"
                        f"📌 *{title}*\n"
                        f"🕐 {date}\n"
                        f"🔗 [Читать полностью]({url_news})"
                    )

                    users = get_users()
                    sent_count = 0
                    for user_id in users:
                        try:
                            bot.send_message(user_id, message, parse_mode="Markdown")
                            sent_count += 1
                        except Exception as e:
                            print(f"Не удалось отправить новость {user_id}: {e}")
                            if "bot was blocked" in str(e).lower() or "chat not found" in str(e).lower():
                                remove_user(user_id)

                    save_last_gid(gid)
                    print(f"Отправлено обновление '{title}' {sent_count} пользователям")
        except Exception as e:
            print(f"Ошибка проверки обновлений: {e}")

        time.sleep(15 * 60)


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
    save_user(message.from_user.id)

    response = (
        "Сапчик! Вот мои команды:\n\n"
        "/start - Показать этот список\n"
        "/status - Статус работы бота\n"
        "/roll - Случайное число от 1 до 100\n"
        "/ping - Проверить, жив ли бот\n"
        "/updates - Последнее обновление Dota 2"
    )
    bot.reply_to(message, response)


@bot.message_handler(commands=['status'])
def send_status(message):
    global messages_count
    messages_count += 1
    save_user(message.from_user.id)

    now = datetime.now(timezone(timedelta(hours=5)))
    uptime = now - start_time
    total_seconds = int(uptime.total_seconds())

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    status_text = (
        f"📊 *Статус бота:*\n\n"
        f"✅ Статус: Работает\n"
        f"⏱ Время работы: {days}д {hours}ч {minutes}мин\n"
        f"📨 Обработано сообщений: {messages_count}\n"
        f"🕐 Текущее время (Екб): {now.strftime('%H:%M:%S')}"
    )
    bot.reply_to(message, status_text, parse_mode="Markdown")


@bot.message_handler(commands=['roll'])
def send_roll(message):
    global messages_count
    messages_count += 1
    save_user(message.from_user.id)
    number = random.randint(1, 100)
    bot.reply_to(message, f"🎲 Выпало: *{number}*", parse_mode="Markdown")


@bot.message_handler(commands=['ping'])
def send_ping(message):
    global messages_count
    messages_count += 1
    save_user(message.from_user.id)
    bot.reply_to(message, "🏓 Pong!")


@bot.message_handler(commands=['updates'])
def send_updates(message):
    global messages_count
    messages_count += 1
    save_user(message.from_user.id)

    try:
        url = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=570&count=1&format=json"
        response = requests.get(url, timeout=10)
        data = response.json()

        if 'appnews' in data and 'newsitems' in data['appnews'] and len(data['appnews']['newsitems']) > 0:
            latest_news = data['appnews']['newsitems'][0]
            title = latest_news['title']
            url_news = latest_news.get('url', '')
            date = datetime.fromtimestamp(
                latest_news['date'], tz=timezone(timedelta(hours=5))
            ).strftime('%d.%m.%Y %H:%M')

            msg = (
                f"📰 *Последнее обновление Dota 2:*\n\n"
                f"📌 *{title}*\n"
                f"🕐 {date}\n"
                f"🔗 [Читать полностью]({url_news})"
            )
            bot.reply_to(message, msg, parse_mode="Markdown")
        else:
            bot.reply_to(message, "Обновлений пока нет.")
    except Exception as e:
        bot.reply_to(message, f"Ошибка получения обновлений: {e}")


@bot.business_message_handler(func=lambda m: m.text and m.text.lower().strip() in ["новости", "news"])
def handle_business_news(message):
    try:
        url = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=570&count=1&format=json"
        response = requests.get(url, timeout=10)
        data = response.json()

        if 'appnews' in data and 'newsitems' in data['appnews'] and len(data['appnews']['newsitems']) > 0:
            latest_news = data['appnews']['newsitems'][0]
            title = latest_news['title']
            url_news = latest_news.get('url', '')
            date = datetime.fromtimestamp(
                latest_news['date'], tz=timezone(timedelta(hours=5))
            ).strftime('%d.%m.%Y %H:%M')

            msg = (
                f"📰 *Последнее обновление Dota 2:*\n\n"
                f"📌 *{title}*\n"
                f"🕐 {date}\n"
                f"🔗 [Читать полностью]({url_news})"
            )

            bot.send_message(
                message.chat.id,
                msg,
                parse_mode="Markdown",
                business_connection_id=message.business_connection_id
            )
        else:
            bot.send_message(
                message.chat.id,
                "Обновлений пока нет.",
                business_connection_id=message.business_connection_id
            )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"Ошибка получения обновлений: {e}",
            business_connection_id=message.business_connection_id
        )


@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    global messages_count
    messages_count += 1
    save_user(message.from_user.id)

    if message.content_type == 'text':
        text = message.text.lower().strip()
        username = message.from_user.username or ""

        if username.lower() in ["sh0ck85", "ttaeart"] and text == "даров":
            bot.reply_to(message, "даров красавчик")
        elif text in ["здравствуйте", "привет"]:
            bot.reply_to(message, "Здравствуйте! Рад вас видеть.")
        elif text == "как дела?":
            bot.reply_to(message, "У меня всё отлично, спасибо! А у вас?")
        elif text == "что делаешь?":
            bot.reply_to(message, "Работаю, обрабатываю сообщения и жду новых команд!")


def run_bot():
    bot.infinity_polling(timeout=10, long_polling_timeout=5)


def keep_alive():
    while True:
        try:
            if RENDER_URL:
                requests.get(RENDER_URL, timeout=5)
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

    news_thread = threading.Thread(target=check_dota_news)
    news_thread.daemon = True
    news_thread.start()

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
