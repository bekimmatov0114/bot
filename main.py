import telebot
from telebot import types
import json
import os
import threading
import schedule
import time
from datetime import datetime

# Token va adminlar
TOKEN = '8155112667:AAEy_LwzB-AEoFSlPQ4m8wUBljYCDgA1yQI'
ADMIN_IDS = [5987275429, 5085374242, 862298786]
TOTAL_ALGEBRA = 120
TOTAL_GEOMETRIYA = 100

bot = telebot.TeleBot(TOKEN)

users = {}
tasks = []
deadlines = {}

# Fayllardan yuklash
if os.path.exists("users.json"):
    with open("users.json") as f:
        users = json.load(f)

if os.path.exists("data.json"):
    with open("data.json") as f:
        tasks = json.load(f)

if os.path.exists("deadlines.json"):
    with open("deadlines.json") as f:
        deadlines = json.load(f)

# Saqlovchi funksiyalar
def save_users():
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)

def save_tasks():
    with open("data.json", "w") as f:
        json.dump(tasks, f, indent=2)

def save_deadlines():
    with open("deadlines.json", "w") as f:
        json.dump(deadlines, f, indent=2)

# /start
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

# Statistikam
@bot.message_handler(func=lambda m: m.text == "Statistikam")
def show_my_stats(message):
    user = users.get(str(message.from_user.id))
    if not user:
        return bot.send_message(message.chat.id, "Avval /start buyrug‘ini bering.")
    text = f"Statistikangiz:\n\nAlgebra: {user['algebra_done']} ta\nGeometriya: {user['geometriya_done']} ta"
    bot.send_message(message.chat.id, text)

# Admin paneli
def send_admin_panel(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Vazifalar", "50% dan kam ishlaganlar", "O‘quvchilar", "Muddat qo‘shish")
    bot.send_message(message.chat.id, "Admin paneliga xush kelibsiz!", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Ortga")
def go_back(message):
    if message.from_user.id in ADMIN_IDS:
        send_admin_panel(message)
    else:
        send_subjects(message)

# Admin uchun
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
    section, num = message.text.split(" mavzu ")
    topic = f"{section} mavzu {num}"
    relevant = [t for t in tasks if t['section'] == section and t['topic'] == topic]
    if not relevant:
        return bot.send_message(message.chat.id, "Bu mavzuga topshiriqlar yo‘q.")
    for task in relevant:
        cap = f"{task['user']} yuborgan: {task['topic']}"
        if task['type'] == "photo":
            bot.send_photo(message.chat.id, task['file_id'], caption=cap)
        else:
            bot.send_document(message.chat.id, task['file_id'], caption=cap)
    send_admin_panel(message)

# Foydalanuvchi bo‘lim tanlashi
@bot.message_handler(func=lambda m: m.text in ["Algebra", "Geometriya"])
def choose_topic(message):
    section = message.text
    users[str(message.from_user.id)]['section'] = section
    save_users()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    count = TOTAL_ALGEBRA if section == "Algebra" else TOTAL_GEOMETRIYA
    for i in range(1, count + 1):
        markup.add(f"{section} mavzu {i}")
    markup.add("Ortga")
    bot.send_message(message.chat.id, f"{section} bo‘limidagi mavzular:", reply_markup=markup)

# Deadline tekshiruvi bilan topshiriq yuborish
@bot.message_handler(func=lambda m: "mavzu" in m.text and m.from_user.id not in ADMIN_IDS)
def ask_task(message):
    topic = message.text
    user_id = str(message.from_user.id)
    section = topic.split(" mavzu")[0]

    deadline_str = deadlines.get(topic)
    if deadline_str:
        if datetime.now() > datetime.strptime(deadline_str, "%Y-%m-%d"):
            return bot.send_message(message.chat.id, "Bu mavzuga topshirish muddati tugagan.")

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
        return bot.send_message(message.chat.id, "Faqat rasm yoki fayl yuboring.")
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
    bot.send_message(message.chat.id, "Topshiriq qabul qilindi.")
    send_subjects(message)
    for admin_id in ADMIN_IDS:
        try:
            bot.forward_message(admin_id, message.chat.id, message.message_id)
        except: pass

# Admin: 50% dan kam ishlaganlar
@bot.message_handler(func=lambda m: m.text == "50% dan kam ishlaganlar" and m.from_user.id in ADMIN_IDS)
def show_low_progress_users(message):
    text = "50% dan kam bajarilgan foydalanuvchilar:\n\n"
    for uid, user in users.items():
        a = user['algebra_done'] * 100 / TOTAL_ALGEBRA
        g = user['geometriya_done'] * 100 / TOTAL_GEOMETRIYA
        if a < 50 or g < 50:
            text += f"{user['name']}: Algebra {a:.2f}%, Geometriya {g:.2f}%\n"
    bot.send_message(message.chat.id, text or "Barchasi 50%dan ko‘p bajargan.")

# 10 kunda avtomatik statistika
def check_user_progress():
    now = datetime.now()
    for user_id, user in users.items():
        last = datetime.strptime(user.get('last_check', '2000-01-01'), '%Y-%m-%d')
        if (now - last).days >= 10:
            a = round(user['algebra_done'] * 100 / TOTAL_ALGEBRA, 2)
            g = round(user['geometriya_done'] * 100 / TOTAL_GEOMETRIYA, 2)
            try:
                bot.send_message(int(user_id), f"Algebra: {a}%, Geometriya: {g}%")
                user['last_check'] = now.strftime('%Y-%m-%d')
            except: pass
    save_users()

def run_schedule():
    schedule.every().day.at("10:00").do(check_user_progress)
    while True:
        schedule.run_pending()
        time.sleep(60)

# Admin: O‘quvchilar ro‘yxati va statistikasi
@bot.message_handler(func=lambda m: m.text == "O‘quvchilar" and m.from_user.id in ADMIN_IDS)
def show_users_list(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for user in users.values():
        markup.add(user['name'])
    markup.add("Ortga")
    bot.send_message(message.chat.id, "Foydalanuvchilar ro‘yxati:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in [u['name'] for u in users.values()] and m.from_user.id in ADMIN_IDS)
def show_user_progress(message):
    uname = message.text
    user = next(u for u in users.values() if u['name'] == uname)
    a = user['algebra_done'] * 100 / TOTAL_ALGEBRA
    g = user['geometriya_done'] * 100 / TOTAL_GEOMETRIYA
    text = f"{uname} statistikasi:\n\nAlgebra: {a:.2f}%\nGeometriya: {g:.2f}%"
    bot.send_message(message.chat.id, text)

# Admin: Muddat qo‘shish
@bot.message_handler(func=lambda m: m.text == "Muddat qo‘shish" and m.from_user.id in ADMIN_IDS)
def add_deadline(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Algebra", "Geometriya", "Ortga")
    bot.send_message(message.chat.id, "Bo‘limni tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["Algebra", "Geometriya"] and m.from_user.id in ADMIN_IDS)
def add_deadline_for_topic(message):
    section = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    count = TOTAL_ALGEBRA if section == "Algebra" else TOTAL_GEOMETRIYA
    for i in range(1, count + 1):
        markup.add(f"{section} mavzu {i}")
    markup.add("Ortga")
    bot.send_message(message.chat.id, f"{section} bo‘limidagi mavzular:", reply_markup=markup)

@bot.message_handler(func=lambda m: "mavzu" in m.text and m.from_user.id in ADMIN_IDS)
def set_deadline(message):
    topic = message.text
    bot.send_message(message.chat.id, "Muddatni kiriting (YYYY-MM-DD formatida):")
    bot.register_next_step_handler(message, save_deadline, topic)

def save_deadline(message, topic):
    deadline = message.text
    try:
        datetime.strptime(deadline, "%Y-%m-%d")
        deadlines[topic] = deadline
        save_deadlines()
        bot.send_message(message.chat.id, f"{topic} mavzusi uchun muddat belgilandi.")
        send_admin_panel(message)
    except ValueError:
        bot.send_message(message.chat.id, "Noto‘g‘ri sana formatini kiritdingiz. Iltimos, qayta urinib ko‘ring.")

# Asosiy threading uchun
if __name__ == "__main__":
    threading.Thread(target=run_schedule).start()
    bot.polling(none_stop=True)
