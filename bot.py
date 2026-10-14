import os
import threading
import time
import random
import subprocess
import tempfile
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

MY_PLAYLIST_URL = "https://soundcloud.com/lem-happy/sets/viperr-vse-trek?si=f6a1840b377245e98d9e885b0b0c0355&utm_source=clipboard&utm_medium=text&utm_campaign=social_sharing"

DOTA_FACTS = [
    "Первая версия Dota вышла в 2003 году как мод для Warcraft III.",
    "В Dota 2 больше 127 героев, и каждый год добавляют новых. В 2026-м году еще небыло нового героя.",
    "The International 2021 имел призовой фонд больше 40 миллионов долларов.",
    "Название Dota расшифровывается как Defense of the Ancients.",
    "Первым героем, добавленным в Dota 2 после релиза, был Meepo.",
    "Самая долгая профессиональная игра в Dota 2 длилась больше 3 часов.",
    "Слово «Ancient» в названии игры означает древних, которых нужно защищать.",
    "Anti-Mage и Terrorblade в первой Dota были братьями-близнецами и использовали одну модель — Иллидана.",
    "Invoker в Dota 2 носит имя Карл. В первой Dota у него было 31 заклинание.",
    "Sven получил имя в честь датского бодибилдера Свена Одегора Карлсена.",
    "Pangolier — прототип реального животного панголина, которое находится под угрозой исчезновения.",
    "Никто из героев не видел настоящего лица Juggernaut — его нет даже в файлах игры.",
    "Pudge был добавлен в DotA 30 апреля 2004 года. Изначально у него не было хука — он был некромантом.",
    "Wraith King до 13 декабря 2013 года носил имя Skeleton King.",
    "Согласно лору оригинальной Dota, Артас представлен двумя героями: Omniknight (светлый) и Abaddon (тёмный). Wraith King к Артасу отношения не имеет.",
    "Самый крупный призовой фонд в истории киберспорта — The International 2021, больше 40 миллионов долларов.",
    "Победителем TI 2021 стала команда Team Spirit, заработавшая 18,2 миллиона долларов.",
    "Dota 2 лидирует по общему количеству разыгранных призовых среди всех киберспортивных дисциплин — более 319 миллионов долларов.",
    "Рекорд пикового онлайна в Steam — 1,29 миллиона человек (февраль 2016 года).",
    "Три человека(Miposhka, Collapse и Yatoro) из команды Team Spirit стали трехкратными победителями TI, забрав в награду Aegis в 2021, 2023 и 2026 году",
]


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
        "Приветик, я специализируюсь на разных задачах.\n"
        "Одна из них это поиск музыки.\n"
        "Так же я умею проверять обновления в игре DOTA 2 /updates.\n"
        "Еще я специализируюсь на других командах, можете посмотреть поставив символ слеш в строку.\n"
        "Важно знать что бот находится еще в разработке и будет дорабатываться"
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


@bot.message_handler(commands=['viperrall'])
def send_viperrall(message):
    global messages_count
    messages_count += 1
    save_user(message.from_user.id)

    url = "https://soundcloud.com/lem-happy/sets/viperr-vse-trek?si=44da472403fc41308cdefd49c4f0e4e7&utm_source=clipboard&utm_medium=text&utm_campaign=social_sharing"
    response = (
        "🎵 *Все треки VIPERR в одном плейлисте, без блюра и даже те которых нету на Spotify и Яндекс музыке:*\n\n"
        f"🔗 [VIPERR — все треки]({url})"
    )
    bot.reply_to(message, response, parse_mode="Markdown")


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


@bot.message_handler(commands=['search'])
def search_song(message):
    global messages_count
    messages_count += 1
    save_user(message.from_user.id)

    query = message.text.replace('/search', '').strip()
    if not query:
        bot.reply_to(message, "Укажи название: /search Sunday Morning")
        return

    bot.reply_to(message, "🔍 Ищу и качаю...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "yt-dlp",
                "--default-search", "scsearch",
                "-f", "ba",
                "--extract-audio",
                "--audio-format", "mp3",
                "-o", os.path.join(tmpdir, "%(title)s.%(ext)s"),
                f"scsearch:{query} {MY_PLAYLIST_URL}"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            files = [f for f in os.listdir(tmpdir) if f.endswith('.mp3')]
            if not files:
                bot.reply_to(message, f"❌ Не нашёл '{query}' в плейлисте.")
                return

            filepath = os.path.join(tmpdir, files[0])

            with open(filepath, 'rb') as audio:
                bot.send_audio(message.chat.id, audio)

    except subprocess.TimeoutExpired:
        bot.reply_to(message, "❌ Превышено время ожидания.")
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")


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
                f"📰 *крч последняя обнова тут вот:*\n\n"
                f"📌 *{title}*\n"
                f"🕐 {date}\n"
                f"🔗 [тут читай все]({url_news})"
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


@bot.business_message_handler(func=lambda m: m.text and m.text.lower().strip() == "кто тебя сделал")
def handle_business_author(message):
    try:
        bot.send_message(
            message.chat.id,
            "Меня сделал @ttaeart и его друг @sh0ck85, в разработке моего кода "
            "участвовали эти два человека. Они продумывали каждую мою команду "
            "и размышляли как сделать хорошего бота с относительно хорошими "
            "функциями с тем учетом что у меня всего 0.1 CPU, а мои создатели "
            "бедные студенты.",
            business_connection_id=message.business_connection_id
        )
    except Exception as e:
        print(f"Ошибка в handle_business_author: {e}")


@bot.business_message_handler(func=lambda m: m.text and m.text.lower().strip() in [
    "что по доте", "дота", "дота факт",
    "dota fact", "dota", "about dota", "dota facts"
])
def handle_business_dota_fact(message):
    try:
        fact = random.choice(DOTA_FACTS)
        bot.send_message(
            message.chat.id,
            f"Знаешь что? {fact}",
            business_connection_id=message.business_connection_id
        )
    except Exception as e:
        print(f"Ошибка в handle_business_dota_fact: {e}")


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
