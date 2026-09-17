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


def normalize_account_id(raw_id):
    try:
        account_id = int(raw_id)
    except ValueError:
        return None
    steam64_base = 76561197960265728
    if account_id > steam64_base:
        return account_id - steam64_base
    return account_id


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
                    date = datetime.fromtimestamp(latest_news['date'], tz=timezone(timedelta(hours=5))).strftime('%d.%m.%Y %H:%M')

                    message = (
                        f"🔥 *Новая новость в Dota 2!*\n\n"
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
                    print(f"Отправлена новость '{title}' {sent_count} пользователям")
        except Exception as e:
            print(f"Ошибка проверки новостей: {e}")

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
        "/pidor - Специальная команда\n"
        "/status - Статус работы бота\n"
        "/roll - Случайное число от 1 до 100\n"
        "/ping - Проверить, жив ли бот\n"
        "/news - Последняя новость Dota 2\n"
        "/lastgame [ID] - Последний матч игрока\n"
        "/mmr [ID] - Ранг игрока"
    )
    bot.reply_to(message, response)


@bot.message_handler(commands=['pidor'])
def send_pidor(message):
    global messages_count
    messages_count += 1
    save_user(message.from_user.id)
    bot.reply_to(message, "Гандон живо домой")


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


@bot.message_handler(commands=['news'])
def send_news(message):
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
            date = datetime.fromtimestamp(latest_news['date'], tz=timezone(timedelta(hours=5))).strftime('%d.%m.%Y %H:%M')

            message = (
                f"📰 *Последняя новость Dota 2:*\n\n"
                f"📌 *{title}*\n"
                f"🕐 {date}\n"
                f"🔗 [Читать полностью]({url_news})"
            )
            bot.reply_to(message, message, parse_mode="Markdown")
        else:
            bot.reply_to(message, "Новостей пока нет.")
    except Exception as e:
        bot.reply_to(message, f"Ошибка получения новостей: {e}")


@bot.message_handler(commands=['lastgame'])
def send_lastgame(message):
    global messages_count
    messages_count += 1
    save_user(message.from_user.id)

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(
            message,
            "Использование: /lastgame [Steam ID]\n"
            "Можно вводить как Steam64 (17 цифр), так и Steam32.\n"
            "Например: /lastgame 76561197966244188"
        )
        return

    account_id = normalize_account_id(parts[1])
    if account_id is None:
        bot.reply_to(message, "❌ Неверный формат ID. Введи число.")
        return

    try:
        url = f"https://api.opendota.com/api/players/{account_id}/recentMatches"
        response = requests.get(url, timeout=10)
        data = response.json()

        if not data or not isinstance(data, list) or len(data) == 0:
            bot.reply_to(message, "Не удалось найти матчи для этого игрока.")
            return

        match = data[0]
        hero_id = match.get('hero_id')
        kills = match.get('kills', 0)
        deaths = match.get('deaths', 0)
        assists = match.get('assists', 0)
        radiant_win = match.get('radiant_win')
        duration = match.get('duration', 0)
        player_slot = match.get('player_slot', 0)

        is_radiant = player_slot < 128
        won = (radiant_win and is_radiant) or (not radiant_win and not is_radiant)

        hero_name = f"Герой #{hero_id}"
        try:
            heroes_resp = requests.get("https://api.opendota.com/api/heroes", timeout=10)
            heroes_data = heroes_resp.json()
            for hero in heroes_data:
                if hero['id'] == hero_id:
                    hero_name = hero['localized_name']
                    break
        except Exception:
            pass

        minutes = duration // 60
        seconds = duration % 60
        result_text = "Победа ✅" if won else "Поражение ❌"

        reply = (
            f"🎮 *Последний матч:*\n\n"
            f"🦸 Герой: *{hero_name}*\n"
            f"📊 KDA: {kills}/{deaths}/{assists}\n"
            f"🏆 Результат: {result_text}\n"
            f"⏱ Длительность: {minutes}м {seconds}с"
        )
        bot.reply_to(message, reply, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"Ошибка получения матча: {e}")


@bot.message_handler(commands=['mmr'])
def send_mmr(message):
    global messages_count
    messages_count += 1
    save_user(message.from_user.id)

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(
            message,
            "Использование: /mmr [Steam ID]\n"
            "Можно вводить как Steam64 (17 цифр), так и Steam32.\n"
            "Например: /mmr 76561197966244188"
        )
        return

    account_id = normalize_account_id(parts[1])
    if account_id is None:
        bot.reply_to(message, "❌ Неверный формат ID. Введи число.")
        return

    try:
        url = f"https://api.opendota.com/api/players/{account_id}"
        response = requests.get(url, timeout=10)
        data = response.json()

        if not data or 'profile' not in data:
            bot.reply_to(message, "Не удалось найти игрока по этому ID.")
            return

        mmr = data.get('mmr_estimate', {}).get('estimate') or data.get('solo_competitive_rank') or data.get('competitive_rank')
        rank_tier = data.get('rank_tier')
        profile_name = data.get('profile', {}).get('personaname', 'Неизвестный')

        if mmr:
            reply = (
                f"📊 *Профиль игрока:* {profile_name}\n"
                f"🏅 MMR: *{mmr}*"
            )
        elif rank_tier:
            tiers = {1: "Herald", 2: "Guardian", 3: "Crusader", 4: "Archon", 5: "Legend", 6: "Ancient", 7: "Divine", 8: "Immortal"}
            star = rank_tier % 10
            tier_num = rank_tier // 10
            tier_name = tiers.get(tier_num, "Неизвестный ранг")
            reply = (
                f"📊 *Профиль игрока:* {profile_name}\n"
                f"🏅 Ранг: *{tier_name} {star}*"
            )
        else:
            reply = f"📊 *Профиль игрока:* {profile_name}\n🏅 Ранг: *не определён* (возможно, скрыт)"

        bot.reply_to(message, reply, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"Ошибка получения MMR: {e}")


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
