import telebot
from telebot import types
import json
import os
import threading
import schedule
import time
from datetime import datetime
from flask import Flask
from threading import Thread

TOKEN = 'TOKENNI_BUYERGA_KIRITING'
ADMIN_IDS = [5987275429, 5085374242, 862298786]
TOTAL_ALGEBRA = 120
TOTAL_GEOMETRIYA = 100

bot = telebot.TeleBot(TOKEN)

users = {}
tasks = []
deadlines = {}

if os.path.exists("users.json"):
    with open("users.json") as f:
        users = json.load(f)

if os.path.exists("data.json"):
    with open("data.json") as f:
        tasks = json.load(f)

if os.path.exists("deadlines.json"):
    with open("deadlines.json") as f:
        deadlines = json.load(f)

def save_users():
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)

def save_tasks():
    with open("data.json", "w") as f:
        json.dump(tasks, f, indent=2)

def save_deadlines():
    with open("deadlines.json", "w") as f:
        json.dump(deadlines, f, indent=2)

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = str(message.from_user.id)
    if user_id not in users:
        bot.send_message(message.chat.id, "Ismingizni kiriting:")
        bot.register_next_step_handler(message, get_name)
    else:
        if message.from_user.id in ADMIN_IDS:
            send_admin_panel(message)
        else:
            send_subjects(message)

def get_name(message):
    user_id = str(message.from_user.id)
    users[user_id] = {
        'name': message.text,
        'algebra_done': 0,
        'geometriya_done': 0,
        'last_check': '2000-01-01'
    }
    save_users()
    send_subjects(message)

def send_subjects(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Algebra", "Geometriya")
    markup.add("Statistikam")
    bot.send_message(message.chat.id, "Bo‘limni tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Statistikam")
def show_my_stats(message):
    user_id = str(message.from_user.id)
    user = users.get(user_id)
    if not user:
        bot.send_message(message.chat.id, "Avval /start buyrug‘ini bering.")
        return

    algebra_done = user.get("algebra_done", 0)
    geometriya_done = user.get("geometriya_done", 0)

    text = f"Statistikangiz:\n\nAlgebra: {algebra_done} ta vazifa\nGeometriya: {geometriya_done} ta vazifa"
    bot.send_message(message.chat.id, text)

# Admin Panel
def send_admin_panel(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Vazifalar", "50% dan kam ishlaganlar", "O‘quvchilar")
    bot.send_message(message.chat.id, "Admin paneliga xush kelibsiz!", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Ortga")
def go_back(message):
    if message.from_user.id in ADMIN_IDS:
        send_admin_panel(message)
    else:
        send_subjects(message)

@bot.message_handler(func=lambda m: m.text == "Vazifalar" and m.from_user.id in ADMIN_IDS)
def admin_choose_subject(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Admin - Algebra", "Admin - Geometriya", "Ortga")
    bot.send_message(message.chat.id, "Bo‘limni tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith("Admin -") and m.from_user.id in ADMIN_IDS)
def admin_choose_topic(message):
    section = message.text.replace("Admin - ", "")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    count = TOTAL_ALGEBRA if section == "Algebra" else TOTAL_GEOMETRIYA
    for i in range(1, count + 1):
        markup.add(f"{section} mavzu {i}")
    markup.add("Ortga")
    bot.send_message(message.chat.id, f"{section} bo‘limidagi mavzular:", reply_markup=markup)

@bot.message_handler(func=lambda m: "mavzu" in m.text and m.from_user.id in ADMIN_IDS)
def show_tasks_for_topic(message):
    parts = message.text.split(" mavzu ")
    if len(parts) != 2: return
    section = parts[0]
    topic = f"{section} mavzu {parts[1]}"
    relevant = [t for t in tasks if t['section'] == section and t['topic'] == topic]

    if not relevant:bot.send_message(message.chat.id, "Bu mavzuga topshiriqlar yo‘q.")
        return

    for task in relevant:
        cap = f"{task['user']} yuborgan: {task['topic']}"
        if task['type'] == "photo":
            bot.send_photo(message.chat.id, task['file_id'], caption=cap)
        elif task['type'] == "document":
            bot.send_document(message.chat.id, task['file_id'], caption=cap)

    send_admin_panel(message)

@bot.message_handler(func=lambda m: m.text == "Algebra" or m.text == "Geometriya")
def choose_topic(message):
    user_id = str(message.from_user.id)
    section = message.text
    users[user_id]['section'] = section
    save_users()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    count = TOTAL_ALGEBRA if section == "Algebra" else TOTAL_GEOMETRIYA
    for i in range(1, count + 1):
        markup.add(f"{section} mavzu {i}")
    markup.add("Ortga")
    bot.send_message(message.chat.id, f"{section} bo‘limidagi mavzular:", reply_markup=markup)

@bot.message_handler(func=lambda m: "mavzu" in m.text and m.from_user.id not in ADMIN_IDS)
def ask_task(message):
    user_id = str(message.from_user.id)
    topic = message.text
    section = topic.split(" mavzu")[0]

    deadline_str = deadlines.get(topic)
    if deadline_str:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d")
        if datetime.now() > deadline:
            bot.send_message(message.chat.id, "Bu mavzu uchun topshirish muddati tugagan.")
            return

    users[user_id]['topic'] = topic
    users[user_id]['section'] = section
    save_users()
    bot.send_message(message.chat.id, "Topshiriqni yuboring (rasm yoki fayl).")
    bot.register_next_step_handler(message, handle_task)

def handle_task(message):
    user_id = str(message.from_user.id)
    user = users[user_id]
    section = user['section']
    topic = user['topic']

    if message.content_type not in ["photo", "document"]:
        bot.send_message(message.chat.id, "Faqat rasm yoki fayl yuboring.")
        return

    file_id = message.photo[-1].file_id if message.content_type == "photo" else message.document.file_id

    tasks.append({
        "user": user['name'],
        "section": section,
        "topic": topic,
        "type": message.content_type,
        "file_id": file_id
    })

    if section == "Algebra":
        user['algebra_done'] += 1
    else:
        user['geometriya_done'] += 1

    save_users()
    save_tasks()

    bot.send_message(message.chat.id, "Topshiriq qabul qilindi. Rahmat!")
    send_subjects(message)

    for admin_id in ADMIN_IDS:
        try:
            bot.forward_message(admin_id, message.chat.id, message.message_id)
        except:
            pass

@bot.message_handler(func=lambda msg: msg.text == "50% dan kam ishlaganlar" and msg.from_user.id in ADMIN_IDS)
def show_low_progress_users(message):
    text = "50% dan kam bajarilgan foydalanuvchilar:\n\n"
    count = 0
    for user_id, user in users.items():
        algebra_percent = user['algebra_done'] * 100 / TOTAL_ALGEBRA
        geometriya_percent = user['geometriya_done'] * 100 / TOTAL_GEOMETRIYA
        if algebra_percent < 50 or geometriya_percent < 50:
            count += 1
            text += f"{user['name']}:\n  - Algebra: {algebra_percent:.2f}%\n  - Geometriya: {geometriya_percent:.2f}%\n\n"
    if count == 0:
        text = "Barcha foydalanuvchilar 50% dan ko‘proq bajargan."
    bot.send_message(message.chat.id, text)

def check_user_progress():
    now = datetime.now()
    for user_id, user in users.items():
        last_check = datetime.strptime(user.get('last_check', '2000-01-01'), '%Y-%m-%d')
        if (now - last_check).days >= 10:
            algebra_percent = round(user['algebra_done'] * 100 / TOTAL_ALGEBRA, 2)
            geometriya_percent = round(user['geometriya_done'] * 100 / TOTAL_GEOMETRIYA, 2)
            text = f"Salom, {user['name']}!\n\nAlgebra: {algebra_percent}% bajarilgan\nGeometriya: {geometriya_percent}% bajarilgan"
            try:
                bot.send_message(int(user_id), text)
            except:
                passuser['last_check'] = now.strftime('%Y-%m-%d')
    save_users()

def run_schedule():
    schedule.every().day.at("10:00").do(check_user_progress)
    while True:
        schedule.run_pending()
        time.sleep(60)

@bot.message_handler(func=lambda m: m.text == "O‘quvchilar" and m.from_user.id in ADMIN_IDS)
def show_users_list(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for user_id in users:
        markup.add(users[user_id]['name'])
    markup.add("Ortga")
    bot.send_message(message.chat.id, "Foydalanuvchilar ro‘yxati:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in [users[uid]['name'] for uid in users] and m.from_user.id in ADMIN_IDS)
def show_user_progress(message):
    selected_user = message.text
    user_id = next(uid for uid in users if users[uid]['name'] == selected_user)
    algebra_topics = []
    geometriya_topics = []

    for i in range(1, TOTAL_ALGEBRA + 1):
        topic = f"Algebra mavzu {i}"
        status = "Yuborgan" if any(t for t in tasks if t['user'] == selected_user and t['topic'] == topic) else "Yo'q"
        algebra_topics.append(f"{i}-mavzu: {status}")

    for i in range(1, TOTAL_GEOMETRIYA + 1):
        topic = f"Geometriya mavzu {i}"
        status = "Yuborgan" if any(t for t in tasks if t['user'] == selected_user and t['topic'] == topic) else "Yo'q"
        geometriya_topics.append(f"{i}-mavzu: {status}")

    result = f"{selected_user} statistikasi:\n\n*Algebra:*\n" + "\n".join(algebra_topics)
    result += "\n\n*Geometriya:*\n" + "\n".join(geometriya_topics)
    bot.send_message(message.chat.id, result, parse_mode='Markdown')

# Flask server
app = Flask('')

@app.route('/')
def home():
    return "Bot ishlayapti!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_schedule, daemon=True).start()
Thread(target=run_web).start()
bot.infinity_polling()
