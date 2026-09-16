import os
import threading
import time
import requests
import telebot
from flask import Flask
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.environ.get('BOT_TOKEN')
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL')
USERS_FILE = 'bot_users.txt'
LAST_NEWS_FILE = 'last_dota_news_gid.txt'

if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN. Проверь переменные окружения.")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

start_time = datetime.now(timezone(timedelta(hours=5)))
messages_count = 0

def get_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    return []

def save_user(user_id):
    users = get_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        users.append(user_id_str)
        with open(USERS_FILE, 'w') as f:
            f.write('\n'.join(users))

def remove_user(user_id):
    users = get_users()
    user_id_str = str(user_id)
    if user_id_str in users:
        users.remove(user_id_str)
        with open(USERS_FILE, 'w') as f:
            f.write('\n'.join(users))

def get_last_gid():
    if os.path.exists(LAST_NEWS_FILE):
        with open(LAST_NEWS_FILE, 'r') as f:
            return f.read().strip()
    return ""

def save_last_gid(gid):
    with open(LAST_NEWS_FILE, 'w') as f:
        f.write(gid)

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
                    url_news = latest_news['url']
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
                            print(f"Не удалось отправить новость пользователю {user_id}: {e}")
                            if "bot was blocked" in str(e).lower() or "chat not found" in str(e).lower():
                                remove_user(user_id)
                    
                    save_last_gid(gid)
                    print(f"Отправлена новость '{title}' {sent_count} пользователям")
        except Exception as e:
            print(f"Ошибка проверки новостей Dota 2: {e}")
        
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
        "/status - Статус работы бота"
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

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    global messages_count
    messages_count += 1
    save_user(message.from_user.id)
    
    if message.content_type == 'text':
        text = message.text.lower().strip()
        username = (message.from_user.username or "").lower()
        
        print(f"Получено сообщение от @{username} (ID: {message.from_user.id}): {text}")
        
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

    news_thread = threading.Thread(target=check_dota_news)
    news_thread.daemon = True
    news_thread.start()

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
