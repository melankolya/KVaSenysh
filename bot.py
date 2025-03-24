import json
import os
import threading
import telebot
import random
import datetime
import pytz
from config import ALLOWED_USERS, BACKGROUND_IMAGE, CHAT_ID, COLOR_NAME, COLOR_TEXT, DATA_FILE, FONT_NAME, FONT_SIZE_NAME, FONT_SIZE_TEXT, FONT_TEXT, MEDIA_FOLDER, RIGHT_NOW_FILE, TOKEN
from data import members, metro_lines, metro_stations, TIME_VARIANTS, THOUGHTFUL_PHRASES, savee_data
import telebot
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import re
import time
import openai

bot = telebot.TeleBot(TOKEN)

bot.set_my_commands([
    telebot.types.BotCommand("start", "Запуск бота-Квасёныша"),
    telebot.types.BotCommand("info", "Информация о квасёнке"),
    telebot.types.BotCommand("ship", "Случайно объединяет двух людей в пару"),
    telebot.types.BotCommand("pidor", "Определяет пидора дня"),
    telebot.types.BotCommand("quote", "Увековечить цитату"),
    telebot.types.BotCommand("think", "Цитата к размышлению"),
    telebot.types.BotCommand("rightnow", "Выводит текст последнего райтнау"),
    telebot.types.BotCommand("when", "Заглянуть в будущее"),
    telebot.types.BotCommand("wheel", "ПИВНОЕ КОЛЕСО"),
    telebot.types.BotCommand("sause", "Соус дня"),
    telebot.types.BotCommand("daddy", "Отец бота"),
    telebot.types.BotCommand("compat", "Рассчёт совместимости двух активистов"),
    telebot.types.BotCommand("who", "Определяет, кто из комитета..."),
    telebot.types.BotCommand("hero", "Определяет хозяина болота на день"),
    telebot.types.BotCommand("prob", "Определяет вероятность события"),
    telebot.types.BotCommand("top", "Выводит лучших в указанной сфере"),
    telebot.types.BotCommand("ranking", "Рейтинг респекта среди квасят"),
    telebot.types.BotCommand("respect", "Респектнуть пользователя (ответом на его сообщение)"),
    telebot.types.BotCommand("disrespect", "Дизреспектнуть пользователя (ответом на его сообщение)"),
    telebot.types.BotCommand("help", "Показать список команд"),
    telebot.types.BotCommand("zodiac", "Квасята по знаку зодиака"),
    telebot.types.BotCommand("faculty", "Квасята по факультету"),
])


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Привет! Я бот для Комитета Внешних Связей. Введи /help, чтобы узнать, что я умею.")
 
 # Функция для генерации цитаты
def generate_quote_image(text, author_name):
    # Загружаем фон
    bg = Image.open(BACKGROUND_IMAGE).convert("RGB")
    img_width, img_height = bg.size
    img = bg.copy()
    draw = ImageDraw.Draw(img)

    # Загружаем шрифты
    font_text = ImageFont.truetype(FONT_TEXT, FONT_SIZE_TEXT)
    font_name = ImageFont.truetype(FONT_NAME, FONT_SIZE_NAME)

    # Позиции текста
    text_x = img_width * 0.05  # Отступ слева
    text_y = img_height * 0.25  # Четверть изображения вверх

    name_x = img_width * 0.25  # Чуть левее середины
    name_y = img_height - 180  # Внизу изображения

    # Ограничиваем длину текста
    text = text[:200] + "..." if len(text) > 200 else text
    text = f"«{text}»"  # Добавляем ёлочные кавычки

    # Разбиваем цитату на строки, если она слишком длинная
    max_width = img_width * 0.9
    lines = []
    words = text.split()
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        if draw.textbbox((0, 0), test_line, font=font_text)[2] < max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)

    # Рисуем цитату (по левому краю)
    y_offset = text_y
    for line in lines:
        draw.text((text_x, y_offset), line, font=font_text, fill=COLOR_TEXT)
        y_offset += FONT_SIZE_TEXT * 1.2  # Межстрочный интервал

    # Рисуем имя (увеличенное и сдвинутое влево)
    if len(author_name) > 15:
        draw.text((name_x, name_y), author_name, font=ImageFont.truetype(FONT_NAME, FONT_SIZE_NAME*0.9), fill=COLOR_NAME)
    else:
        draw.text((name_x, name_y), author_name, font=font_name, fill=COLOR_NAME)

    # Сохраняем в буфер
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output

# Команда /цитата
@bot.message_handler(commands=["цитата", "quote"])
def send_quote(message):
    if not message.reply_to_message or not message.reply_to_message.text:
        bot.reply_to(message, "Необходимо ответить на сообщение с текстом.")
        return  # Игнорируем, если нет ответа на сообщение
    text = message.reply_to_message.text
    author_telegram = f"@{message.reply_to_message.from_user.username}" if message.reply_to_message.from_user.username else None
    author_name = f"{message.reply_to_message.from_user.first_name} {message.reply_to_message.from_user.last_name}".strip() or "Квасёныш"

    # Ищем автора в списке members
    author = next((m for m in members if m["telegram"] == author_telegram), None)
    if author:
        author_name = f"{author['first_name']} {author['last_name']}"

    # Генерируем изображение
    img = generate_quote_image(text, author_name)
    os.makedirs(MEDIA_FOLDER, exist_ok=True)
    file_path = os.path.join(MEDIA_FOLDER, f"quote_{message.message_id}.jpg")
    with open(file_path, "wb") as f:
        f.write(img.getvalue())
    img = generate_quote_image(text, author_name)
    bot.send_photo(message.chat.id, img, reply_to_message_id=message.message_id)

quote_parts = []
quote_author = None

@bot.message_handler(commands=["запомни"])
def remember_quote(message):
    global quote_parts, quote_author
    
    if not message.reply_to_message or not message.reply_to_message.text:
        bot.reply_to(message, "Необходимо ответить на сообщение с текстом.")
        return
    
    if not quote_parts:
        quote_author = message.reply_to_message.from_user.username
    
    quote_parts.append(message.reply_to_message.text)
    bot.reply_to(message, "Запомнил!")

@bot.message_handler(commands=["отправь"])
def send_stored_quote(message):
    global quote_parts, quote_author
    
    if not quote_parts:
        bot.reply_to(message, "Нет сохранённой цитаты.")
        return
    
    author_name = "Квасёныш"
    if quote_author:
        author = next((m for m in members if m["telegram"] == f"@{quote_author}"), None)
        if author:
            author_name = f"{author['first_name']} {author['last_name']}"
    
    text = ", ".join(quote_parts)
    img = generate_quote_image(text, author_name)
    os.makedirs(MEDIA_FOLDER, exist_ok=True)
    file_path = os.path.join(MEDIA_FOLDER, f"quote_{message.message_id}.jpg")
    with open(file_path, "wb") as f:
        f.write(img.getvalue())
    bot.send_photo(message.chat.id, img, reply_to_message_id=message.message_id)
    
    quote_parts = []
    quote_author = None 
    
@bot.message_handler(commands=['metro'])
def find_members_by_metro(message):
    line_query = message.text.split(maxsplit=1)
    if len(line_query) < 2:
        bot.reply_to(message, "Пожалуйста, укажите номер, цвет или название линии метро.")
        return
    
    line_input = line_query[1].strip().lower()
    line_number = None
    
    for num, names in metro_lines.items():
        if line_input in [num] + [name.lower() for name in names]:
            line_number = num
            break
    
    if not line_number:
        bot.reply_to(message, "Не удалось найти указанную линию метро.")
        return
    
    stations_on_line = metro_stations.get(line_number, [])
    found_members = [f"{m['first_name']} {m['last_name']} ({m['metro']})" for m in members if m['metro'] in stations_on_line]
    
    if found_members:
        bot.reply_to(message, f"Активисты КВС, живущие на {line_number} линии метро:\n" + "\n".join(found_members))
    else:
        bot.reply_to(message, "На этой линии метро нет активистов.")


def send_member_info(message, member):
    """Функция отправки информации о человеке."""
    info = (
        f"👤 {member['formal_last_name']} {member['formal_first_name']} {member['mrespectdle_name']}\n"
        f"📅 Дата рождения: {member['birth_date']}\n"
        f"🏫 Факультет: {member['faculty']}\n"
        f"🎓 Группа: {member['group']}\n"
        f"📞 Телефон: {member['phone']}\n"
        f"📧 Почта: {member['email']}\n"
        f"💬 Telegram: {member['telegram']}\n"
        f"🚇 Станция метро: {member['metro']}"
    )
    bot.reply_to(message, info)
    
import re

@bot.message_handler(func=lambda message: re.search(r'\bдоброе\b.*\bутро\b.*\bквс\b', message.text, re.IGNORECASE))
def good_morning_kvs(message):
    user_telegram = f"@{message.from_user.username}" if message.from_user.username else None
    member = next((m for m in members if m["telegram"] == user_telegram), None)

    first_name = member["first_name"] if member else "Квасёныш"
    if member["telegram"] == "@Liiiiiidik":
        bot.reply_to(message, 
                 f"Доброе утро, {first_name} ❤️🖤\nЧертовски вкусного кофе!",
                 parse_mode="Markdown")
    elif member["telegram"] == "@davlugusya":
        bot.reply_to(message, 
                 f"Доброе утро, {first_name} ❤️🖤\nЧертовски... Найди девушку уже!",
                 parse_mode="Markdown")
    elif member["telegram"] == "@Mariia_Makh":
        bot.reply_to(message, 
                 f"Доброе утро, {first_name} ❤️🖤\nФедя всё ещё твой, и это чертовски классно!",
                 parse_mode="Markdown")
    elif member["telegram"] == "@sinevvvaa":
        bot.reply_to(message, 
                 f"Доброе утро, {first_name} ❤️🖤\nЧертовски синего дня!",
                 parse_mode="Markdown")
    elif member["telegram"] == "@shamonova_a":
        bot.reply_to(message, 
                 f"Доброе утро, любимый пред ❤️🖤\nЧертовски тёплых активистов!",
                 parse_mode="Markdown")
    elif member["telegram"] == "@just_scvorov":
        bot.reply_to(message, 
                 f"Доброе утро, мой главный юзер ❤️🖤\nНе мучай меня сегодня пожалуйста!",
                 parse_mode="Markdown")
    elif member["telegram"] == "@fzharkevich":
        bot.reply_to(message, 
                 f"Доброе утро, {first_name} ❤️🖤\nМаша всё ещё твоя, и это чертовски классно!",
                 parse_mode="Markdown")
    elif member["telegram"] == "@hue_moee":
        bot.reply_to(message, 
                 f"Доброе утро, {first_name} ❤️🖤\nПапа всегда рядом!",
                 parse_mode="Markdown")
    elif member["telegram"] == "@rn_iaa":
        bot.reply_to(message, 
                 f"Доброе утро, {first_name} ❤️🖤\nЧертовски хорошо, что ты проснулась, ведь теперь мир точно полон красоты и эстетики!",
                 parse_mode="Markdown")
    elif member["telegram"] == "@tyoma_sigeda":
        bot.reply_to(message, 
                 f"Доброе утро, {first_name} ❤️🖤\nОоо дед!!! Чертовски хорошо, что ты встал, я уже начал переживать.",
                 parse_mode="Markdown")
    elif member["telegram"] == "@feinsinn":
        bot.reply_to(message, 
                 f"Доброе утро, {first_name} ❤️🖤\nДОБРОЕ УТРО АРТЁМ!",
                 parse_mode="Markdown")
    else:
        bot.reply_to(message, 
                 f"Доброе утро, {first_name} ❤️🖤\nЧертовски хорошего дня!",
                 parse_mode="Markdown")

@bot.message_handler(func=lambda message: re.search(r'\bспокойной\b.*\bночи\b.*\bквс\b', message.text, re.IGNORECASE))
def good_morning_kvs(message):
    user_telegram = f"@{message.from_user.username}" if message.from_user.username else None
    member = next((m for m in members if m["telegram"] == user_telegram), None)

    first_name = member["first_name"] if member else "Квасёныш"

    bot.reply_to(message, f"Спокойной ночи, {first_name} ❤️🖤\nЧертовски сладких снов!")

import random

@bot.message_handler(commands=["хуй"])
def dick_size(message):
    sender_username = f"@{message.from_user.username}" if message.from_user.username else None
    member = next((m for m in members if m["telegram"] == sender_username), None)

    name = member["first_name"] if member else message.from_user.first_name
    size = random.randint(3, 35)  # Генерируем размер от 3 до 35 см
    if member["telegram"] == "@Liiiiiidik":
        bot.reply_to(message, "Чтооооооо Лида матерится!!! @melankolya она спалилась!!!")
    else:
        bot.reply_to(message, f"{name}, твой хуй {size} см 🍆")


@bot.message_handler(commands=["инфа", "info"])
def get_member_info(message):
    args = message.text.split(maxsplit=2)

    if len(args) == 1 and message.reply_to_message:  # Если команда отправлена в ответ на сообщение и без аргументов
        reply_user = message.reply_to_message.from_user.username
        if reply_user:
            member = next((m for m in members if m['telegram'].strip('@') == reply_user), None)
            if member:
                send_member_info(message, member)
                return

    if len(args) < 2:
        bot.reply_to(message, "Использование: /инфа Фамилия [Имя (необязательно)] или отправь команду в ответ на сообщение без дополнительных слов.")
        return

    last_name = args[1].strip().lower()
    first_name = args[2].strip().lower() if len(args) > 2 else None

    found_members = [
        m for m in members if (m["last_name"].lower() == last_name or m["formal_last_name"].lower() == last_name)
        and (first_name is None or m["first_name"].lower() == first_name or m["formal_first_name"].lower() == first_name)
    ]

    if not found_members:
        bot.reply_to(message, "Квасёныш не найден.")
        return

    if len(found_members) > 1 and first_name is None:
        # Формируем список доступных команд
        commands_list = "\n".join(f"`/инфа {m['last_name']} {m['first_name']}`" for m in found_members)
        bot.reply_to(message, f"Найдено несколько квасят с фамилией {last_name.capitalize()}.\n"
                              f"Выбери одного из них, введя одну из команд:\n{commands_list}", parse_mode="Markdown")
        return

    # Если найден ровно один квасёныш
    send_member_info(message, found_members[0])

        

# Храним время последнего вызова команды каждым пользователем
last_all_request = {}

moscow_tz = pytz.timezone("Europe/Moscow")


@bot.message_handler(commands=["all", "все"])
def mention_everyone(message):
    user_telegram = f"@{message.from_user.username}" if message.from_user.username else None

    # Проверяем, есть ли пользователь в списке разрешённых
    if user_telegram not in ALLOWED_USERS:
        bot.reply_to(message, "Только для руководителей!")
        return

    now = time.time()  # Текущее время в секундах
    last_request = last_all_request.get(user_telegram, 0)

    # Если прошло меньше 20 секунд с последнего вызова
    if now - last_request < 20:
        mentions = " ".join(m["telegram"] for m in members if m["telegram"])
        # mentions = "@melankolya"
        bot.send_message(message.chat.id, mentions)
    else:
        # Обновляем время вызова команды
        last_all_request[user_telegram] = now

        current_time = datetime.datetime.now(moscow_tz).strftime("%H:%M")
        bot.reply_to(
            message,
            f"Ты уверен(-а), что хочешь отметить всех участников чата? Сейчас {current_time}\n"
            f"Для подтверждения отправь команду ещё раз: `/all`",
        parse_mode="Markdown")

moscow_tz = pytz.timezone("Europe/Moscow")

def send_wakeup_message(chat_id, member):
    """Функция отправки сообщений пользователю."""
    wakeup_text = f"{member['telegram']} {member['telegram']} {member['telegram']}\n\n" \
                  f"Проснись! Вот номер телефона: {member['phone']}. Позвоните квасёнку!"
    bot.send_message(chat_id, wakeup_text)

@bot.message_handler(commands=["разбудить"])
def set_wakeup_call(message):
    """Обработчик команды /разбудить."""
    command_parts = message.text.split()
    if len(command_parts) != 2:
        bot.reply_to(message, "❌ Введите время в формате ЧЧ:ММ, например: /разбудить 08:30")
        return

    match = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", command_parts[1])
    if not match:
        bot.reply_to(message, "❌ Некорректное время! Введите в формате ЧЧ:ММ (например, 07:45).")
        return

    hours, minutes = map(int, match.groups())

    # Найти пользователя в members
    sender_username = f"@{message.from_user.username}" if message.from_user.username else None
    member = next((m for m in members if m["telegram"] == sender_username), None)

    if not member:
        bot.reply_to(message, "❌ Вас нет в базе, не могу вас разбудить.")
        return

    now = datetime.datetime.now(moscow_tz)
    wakeup_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)

    # Если время уже прошло сегодня — ставим будильник на следующий день
    if wakeup_time <= now:
        wakeup_time += datetime.timedelta(days=1)

    time_diff = (wakeup_time - now).total_seconds()

    bot.reply_to(message, f"✅ Будильник установлен на {wakeup_time.strftime('%H:%M')}. Чертовски сладких снов!")

    # Отложенный запуск
    threading.Thread(target=lambda: (time.sleep(time_diff), send_wakeup_message(message.chat.id, member))).start()


@bot.message_handler(commands=['шипперить', "ship"])
def ship_people(message):
    phrases = ['теперь пара ❤️', 'ебутся', 'геи']
    
    if message.reply_to_message:  # Проверяем, есть ли ответ на сообщение
        reply_user = message.reply_to_message.from_user.username
        if reply_user:
            person1 = next((m for m in members if m['telegram'].strip('@') == reply_user), None)
            if person1:
                person2 = random.choice([m for m in members if m != person1])  # Выбираем случайного второго
                ship_message = f"{person1['first_name']} {person1['last_name']} и {person2['first_name']} {person2['last_name']} {random.choice(phrases)}"
                bot.reply_to(message, ship_message)
                return
    
    # Если нет ответа на сообщение или не найден юзер — шипперим случайных людей
    person1, person2 = random.sample(members, 2)
    ship_message = f"{person1['first_name']} {person1['last_name']} и {person2['first_name']} {person2['last_name']} {random.choice(phrases)}"
    if "Жаркевич" in ship_message:
        ship_message = ship_message + ".. И куда только Маша смотрит!"
    bot.reply_to(message, ship_message)

@bot.message_handler(commands=['хардшипперить', "hardship"])
def hardship_people(message):
    phrases = ['практикуют анальный фистинг', 'провели ночь на КВСнике', 'уединились после собрания']
    
    if message.reply_to_message:  # Проверяем, есть ли ответ на сообщение
        reply_user = message.reply_to_message.from_user.username
        if reply_user:
            person1 = next((m for m in members if m['telegram'].strip('@') == reply_user), None)
            if person1:
                person2 = random.choice([m for m in members if m != person1])  # Выбираем случайного второго
                ship_message = f"{person1['first_name']} {person1['last_name']} и {person2['first_name']} {person2['last_name']} {random.choice(phrases)}"
                bot.reply_to(message, ship_message)
                return
    
    # Если нет ответа на сообщение или не найден юзер — шипперим случайных людей
    choiser = random.randint(0, 6)
    if choiser == 0:
        person1, person2 = random.sample(members, 2)
        ship_message = f"{person1['first_name']} {person1['last_name']} и {person2['first_name']} {person2['last_name']} {random.choice(phrases)}"
    elif choiser == 1:
        person1, person2, person3 = random.sample(members, 3)
        ship_message = f"{person1['first_name']} {person1['last_name']} изменяет {person2['first_name']} {person2['last_name']} с {person3['first_name']} {person3['last_name']}!"
    elif choiser == 2:
        person1, person2 = random.sample(members, 2)
        ship_message = f"{person1['first_name']} {person1['last_name']} сделал горловой, {person2['first_name']} {person2['last_name']} остался доволен!"
    elif choiser == 3:
        person1, person2 = random.sample(members, 2)
        ship_message = f"{person1['first_name']} {person1['last_name']} любит раздеваться, когда {person2['first_name']} {person2['last_name']} смотрит"
    else:
        person1, person2 = random.sample(members, 2)
        ship_message = f"{person1['first_name']} {person1['last_name']} и {person2['first_name']} {person2['last_name']} {random.choice(phrases)}"
    if "Жаркевич" in ship_message:
        ship_message = ship_message + ".. И куда только Маша смотрит!"
        
    bot.reply_to(message, ship_message)
    

@bot.message_handler(commands=["совместимость", "compat"])
def compatibility(message):
    if message.reply_to_message:  # Проверяем, есть ли ответ на сообщение
        reply_user = message.reply_to_message.from_user.username
        if reply_user:
            person1 = next((m for m in members if m['telegram'].strip('@') == reply_user), None)
            if person1:
                person2 = random.choice([m for m in members if m != person1])  # Выбираем случайного второго
                compatibility_score = random.randint(-100, 100)
                result_message = (
                    f"🔮 Совместимость {person1['first_name']} {person1['last_name']} и "
                    f"{person2['first_name']} {person2['last_name']}: {compatibility_score}!"
                )
                bot.reply_to(message, result_message)
                return

    # Если нет ответа на сообщение или не найден юзер — выбираем двух случайных людей
    person1, person2 = random.sample(members, 2)
    compatibility_score = random.randint(-100, 100)
    result_message = (
        f"🔮 Совместимость {person1['first_name']} {person1['last_name']} и "
        f"{person2['first_name']} {person2['last_name']}: {compatibility_score}!"
    )

    bot.reply_to(message, result_message)


@bot.message_handler(commands=['кто', "who"])
def who(message):
    person = random.sample(members, 1)[0]
    ret_message = f"{person['first_name']} {person['last_name']} {' '.join(message.text.split(' ')[1:]) if len(message.text.split(' ')) > 1 else ''}"
    bot.reply_to(message, ret_message)
    

moscow_tz = pytz.timezone("Europe/Moscow")

# Функция для загрузки данных
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_pidor": None, "last_date_p": None, "last_xozyain": None, "last_date_x": None}

# Функция для сохранения данных
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Загружаем сохраненные данные
data = load_data()

@bot.message_handler(commands=['пидор', "pidor"])
def get_activist_of_the_day(message):
    now = datetime.datetime.now(moscow_tz)
    today = str(now.date())  # Дата в строковом формате

    if data["last_date_p"] != today or data["last_pidor"] is None:
        chosen_pidor = random.choice(members)
        data["last_pidor"] = chosen_pidor
        data["last_date_p"] = today
        save_data(data)  # Сохраняем изменения

    last_pidor = data["last_pidor"]

    activist_message = (
        f"Пидор дня - {last_pidor['first_name']} {last_pidor['last_name']}! 🎉\n"
        f"Сосал {last_pidor['telegram']}?"
    )
    bot.reply_to(message, activist_message)

@bot.message_handler(commands=['хозяин', "hero"])
def get_hero_of_the_day(message):
    now = datetime.datetime.now(moscow_tz)
    today = str(now.date())  # Дата в строковом формате

    if data["last_date_x"] != today or data["last_xozyain"] is None:
        chosen_xozyain = random.choice(members)
        data["last_xozyain"] = chosen_xozyain
        data["last_date_x"] = today
        save_data(data)  # Сохраняем изменения

    last_xozyain = data["last_xozyain"]

    activist_message = (
        f"Хозяин болота - {last_xozyain['first_name']} {last_xozyain['last_name']}! 🎉\n"
        f"Поздравляем {last_xozyain['telegram']} {last_xozyain['telegram']} {last_xozyain['telegram']}!!!"
    )
    bot.reply_to(message, activist_message)

@bot.message_handler(func=lambda message: message.reply_to_message is not None)
def auto_respect(message):
    reply_user = message.reply_to_message.from_user.username
    sender_user = message.from_user.username

    if not reply_user or not sender_user or (reply_user == sender_user and sender_user != "melankolya"):
        return  # Игнорируем, если не удалось определить пользователей или это самореспект

    member = next((m for m in members if m['telegram'].strip('@') == reply_user), None)
    if not member:
        return  # Игнорируем, если пользователя нет в списке

    if "respect" not in member:
        member["respect"] = 0  
    
    text = message.text.lower()
    if any(word in text for word in ["+", "❤️", "пасиб", "спс", "благодар", "респект"]):
        member["respect"] += 1
        bot.reply_to(message, f"Спасибо на хлеб не намажешь, а дополнительный балл - это всегда приятно. {member['first_name']}, \nТеперь у тебя {member['respect']} балл(-ов)!")
    savee_data()

@bot.message_handler(commands=["+", "-", "respect", "disrespect"])
def change_respect(message):
    if not message.reply_to_message:  
        return  # Игнорируем, если нет ответа на сообщение

    reply_user = message.reply_to_message.from_user.username
    sender_user = message.from_user.username

    if not reply_user or not sender_user or (reply_user == sender_user and sender_user != "melankolya"):
        return  # Игнорируем, если не удалось определить пользователей или это самореспект

    member = next((m for m in members if m['telegram'].strip('@') == reply_user), None)
    if not member:
        return  # Игнорируем, если пользователя нет в списке

    if "respect" not in member:
        member["respect"] = 0  

    if message.text.startswith("/+") or message.text.startswith("/respect"):
        value = 1
        if sender_user == "melankolya":
            parts = message.text.split()
            if len(parts) > 1:
                try:
                    value = int(parts[1])
                except ValueError:
                    pass
        member["respect"] += value
        if value == 1:
            bot.reply_to(message, f"Ты жёстко респектнул(-а) доброму человеку! {member['first_name']}, ты - легенда! \nУ тебя уже {member['respect']} балл(-ов)!")
        else:
            bot.reply_to(message, f"ПАПОЧКА ХВАЛИТ!\nУ тебя уже {member['respect']} балл(-ов)!")
    elif message.text.startswith("/-") or message.text.startswith("/disrespect"):
        value = 1
        if sender_user == "melankolya":
            parts = message.text.split()
            if len(parts) > 1:
                try:
                    value = int(parts[1])
                except ValueError:
                    pass
        member["respect"] -= value
        if value == 1:
            bot.reply_to(message, f"Не недостаток, а зона роста! Развивайся, {member['first_name']}... \nТеперь у тебя {member['respect']} балл(-ов).")
        else:
            bot.reply_to(message, f"ГНЕВ ПАПОЧКИ! Развивайся, {member['first_name']}... \nТеперь у тебя {member['respect']} балл(-ов).")
    savee_data()


@bot.message_handler(commands=["рейтинг", "ranking"])
def show_respect_ranking(message):
    sorted_members = sorted(members, key=lambda m: m.get("respect", 0), reverse=True)

    ranking = "".join(
        f"{i + 1}. {m['first_name']} {m['last_name']} — {m.get('respect', 0)}\n" if m.get("respect") != 0 else ""
        for i, m in enumerate(sorted_members)
    )

    bot.reply_to(message, f"🏆 *Рейтинг респекта КВС:* 🏆\n\n{ranking}", parse_mode="Markdown")
    

@bot.message_handler(commands=['вероятность', "prob"])
def probability_command(message):
    text = message.text.replace('/вероятность', '').strip()  # Убираем команду из текста
    if not text.lower().startswith("что "):  # Проверяем, начинается ли текст с "что "
        bot.reply_to(message, "Напиши фразу после `/вероятность`, начиная со слова 'что'. Например: `/вероятность что я сдам сессию`")
        return
    text = text[4:].strip()  # Убираем слово "что " из текста
    probability = random.randint(0, 100)  # Генерируем случайное число от 0 до 100
    response = f"{text} с вероятностью {probability}%"
    bot.reply_to(message, response)
    

@bot.message_handler(commands=['топ', "top"])
def top_command(message):
    text = message.text.replace('/топ', '').replace('/top', '').strip()
    
    words = text.split()
    
    if words and words[0].isdigit():  # Если первое слово — число
        count = int(words[0])
        category = " ".join(words[1:]) if len(words) > 1 else "лучших"
    else:  # Если число не указано, ставим 5 по умолчанию
        count = 5
        category = text if text else "лучших"
    
    count = min(count, len(members))  # Ограничиваем количество участников

    top_members = random.sample(members, count)  # Берем случайных людей

    response = f"Топ {count} {category} в КВС:\n"
    response += "\n".join([f"{i+1}. {member['first_name']} {member['last_name']}" for i, member in enumerate(top_members)])

    bot.reply_to(message, response)
    

@bot.message_handler(commands=['монетка', "coin"])
def coin(message):
    response = random.choice(["Орел", "Решка"])
    bot.reply_to(message, response)
    
@bot.message_handler(commands=['sause', 'соус'])
def sous_dnya(message):
    if message.from_user.username == "davlugusya":
        bot.reply_to(message, "Лёш, задаёшь слишком много вопросов")
    elif message.from_user.username == "Liiiiiidik":
        bot.reply_to(message, "Лида, ты сегодня отлично выглядишь! Хорошего тебе дня!")
    elif message.from_user.username == "shamonova_a":
        bot.reply_to(message, "Шами любимый пред.")
    elif message.from_user.username == "Mariia_Makh":
        bot.reply_to(message, "Медово-горчичный конечно солнце, твой любимый!!!")
    elif message.from_user.username == "fzharkevich":
        bot.reply_to(message, "При Маше на такой вопрос не отвечаю.")
    else:
        bot.reply_to(message, "Медово-горчичный соус")
        
@bot.message_handler(commands=['sosal', 'сосал'])
def sosal(message):
    if message.from_user.username == "davlugusya":
        bot.reply_to(message, "Лёш, задаёшь слишком много вопросов")
    elif message.from_user.username == "Liiiiiidik":
        bot.reply_to(message, "А на вид культурная девушка... Выпьем кофе?")
    elif message.from_user.username == "shamonova_a":
        bot.reply_to(message, "Не выгоняй меня из чата пожааалуйста!")
    elif message.from_user.username == "Mariia_Makh":
        bot.reply_to(message, "Я конечно сосал, но ты лучше у @fzharkevich спроси...")
    elif message.from_user.username == "fzharkevich":
        bot.reply_to(message, "Я конечно сосал, но ты лучше у @Mariia_Makh спроси...")
    else:
        bot.reply_to(message, "ДААААААААААААААА")
        
@bot.message_handler(commands=['daddy', 'папочка'])
def daddy(message):
    if message.from_user.username == "davlugusya":
        bot.reply_to(message, "У тебя другой папочка! @just_scvorov")
    elif message.from_user.username == "Liiiiiidik":
        bot.reply_to(message, "Для тебя просто Коля. @melankolya")
    elif message.from_user.username == "shamonova_a":
        bot.reply_to(message, "Можно просто Николя. @melankolya")
    elif message.from_user.username == "hue_moee":
        bot.reply_to(message, "Что, любимая доченька? @melankolya")
    elif message.from_user.username == "sinevvvaa":
        bot.reply_to(message, "Какой папочка, я сын твой! @melankolya\n Папочка вот: @tyoma_sigeda")
    elif message.from_user.username == "tyoma_sigeda":
        bot.reply_to(message, "Твой любящий внук: @melankolya")
    elif message.from_user.username == "just_scvorov":
        bot.reply_to(message, "@melankolya дядя твой, а ты папочка @davlugusya.")
    else:
        bot.reply_to(message, "@melankolya")

def load_right_now():
    if os.path.exists(RIGHT_NOW_FILE):
        with open(RIGHT_NOW_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}

def save_right_now(data):
    with open(RIGHT_NOW_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

@bot.message_handler(func=lambda message: message.caption and "#райтнау" in message.caption.lower())
def handle_right_now(message):
    right_now_data = {
        "message_id": message.message_id,
        "user_id": message.from_user.id
    }
    save_right_now(right_now_data)

@bot.message_handler(commands=["райтнау", "rightnow"])
def send_last_right_now(message):
    right_now_data = load_right_now()
    if not right_now_data:
        bot.reply_to(message, "Пока никто не отправлял #райтнау.")
        return
    
    message_id = right_now_data["message_id"]
    user_id = right_now_data["user_id"]
    
    # Ищем автора в members (замени members на свой список)
    author = next((m for m in members if str(m.get("telegram", "")).strip("@") == str(user_id)), None)
    author_name = author["first_name"] + " " + author["last_name"] if author else "Неизвестный автор"
    
    bot.reply_to(message, f"Автором последнего #райтнау был {author_name}.")
    bot.send_message(message.chat.id, "Вот оно:", reply_to_message_id=message_id)


@bot.message_handler(commands=["help"])
def show_help(message):
    help_text = (
        "🤖 *Список команд бота КВС:*\n\n"
        "📌 */инфа [фамилия] [имя]* – вся информация о нужном квасёнке.\n"
        "📌 */шипперить* – случайным образом объединяет двух людей в пару.\n"
        "📌 */мысль* – выводит случайную цитату.\n"
        "📌 */пидор дня* – определяет пидора дня.\n"
        "📌 */хозяин болота* – определяет хозяина болота на день.\n"
        "📌 */вероятность что [фраза]* – проверь вероятность какого-то события.\n"
        "📌 */топ [число] [категория]* – выводит отличившихся квасят в какой-то сфере.\n"
        "📌 */цитата* – делает красивую картинку из высказывания квасёнка.\n"
        "📌 */когда* – предсказывает будущее.\n"
        "📌 */рейтинг* – показывает рейтинг респекта среди квасят.\n"
        "📌 */колесо [мальчики|девочки]* – ПИВНОЕ КОЛЕСО.\n"
        "📌 */совместимость* – показывает совместимость двух активистов.\n"
        "📌 */+* – респектнуть квасёнка, ответив командой на его сообщение.\n"
        "📌 */-* – дизреспектнуть квасёнка, ответив командой на его сообщение.\n"
        "📌 */help* – показывает этот список команд.\n"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")



@bot.message_handler(commands=["мысль", "think"])
def send_random_photo(message):
    """Выбирает и отправляет случайное фото из сохраненных."""
    files = [f for f in os.listdir(MEDIA_FOLDER) if f.endswith(".jpg")]
    
    if not files:
        bot.reply_to(message, "В базе пока нет изображений.")
        return
    
    random_file = random.choice(files)
    file_path = os.path.join(MEDIA_FOLDER, random_file)
    with open(file_path, "rb") as file:
        bot.send_photo(message.chat.id, file)


@bot.message_handler(commands=["когда", "when"])
def when_command(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "Использование: /когда [ваш вопрос]")
        return
    if args[1] in ['собра', 'собрашка', 'собрание комитета', 'собрание']:
        bot.reply_to(message, "Следующее собрание Комитета Внешних Связей состоится:\n`14 марта в 19:30`", parse_mode="Markdown")
    else:
        user_text = args[1].strip('?')

        # Заменяем "я" на "ты"
        user_text = re.sub(r'\bЯ\b', 'Ты', user_text, flags=re.IGNORECASE)

        # Заменяем глаголы совершенного вида на второе лицо единственного числа
        user_text = re.sub(r'\b(смогу|сделаю|куплю|узнаю|увижу|найду|пойму|закончу|начну|позову|скажу|напишу|пойду|приеду|прочитаю|выучу|построю|получу|добьюсь|расскажу|стану|возьму)\b', 
                        lambda m: {
                            'смогу': 'сможешь',
                            'сделаю': 'сделаешь',
                            'куплю': 'купишь',
                            'узнаю': 'узнаешь',
                            'увижу': 'увидишь',
                            'найду': 'найдёшь',
                            'пойму': 'поймёшь',
                            'закончу': 'закончишь',
                            'начну': 'начнёшь',
                            'позову': 'позовёшь',
                            'скажу': 'скажешь',
                            'напишу': 'напишешь',
                            'пойду': 'пойдёшь',
                            'приеду': 'приедешь',
                            'прочитаю': 'прочитаешь',
                            'выучу': 'выучишь',
                            'построю': 'построишь',
                            'получу': 'получишь',
                            'добьюсь': 'добьёшься',
                            'расскажу': 'расскажешь',
                            'стану': 'станешь',
                            'возьму': 'возьмёшь'
                        }[m.group()], user_text)

        # Другие возможные замены
        user_text = re.sub(r'\bмой\b', 'твой', user_text)
        user_text = re.sub(r'\bмоя\b', 'твоя', user_text)
        user_text = re.sub(r'\bмои\b', 'твои', user_text)
        random_time = random.choice(TIME_VARIANTS)
        
        bot.reply_to(message, f"{user_text} {random_time}.")
        

@bot.message_handler(commands=["колесо", "wheel"])
def spin_wheel(message):
    args = message.text.split()
    if len(args) != 2 or args[1] not in ["мальчики", "девочки"]:
        bot.reply_to(message, "Использование: /колесо мальчики|девочки")
        return

    # Фильтруем участников по полу
    gender = "Male" if args[1] == "мальчики" else "Female"
    filtered_members = [m for m in members if m.get("sex") == gender]

    if not filtered_members:
        bot.reply_to(message, "Кажется, в списке нет подходящих кандидатов 🤷‍♂️")
        return

    chat_id = message.chat.id

    # Отправляем 3-4 случайных задумчивых сообщения с интервалом 3 секунды
    thoughtful_messages = random.sample(THOUGHTFUL_PHRASES, k=3)
    for phrase in thoughtful_messages:
        bot.send_message(chat_id, phrase)
        time.sleep(3)

    # Ждём ещё немного перед финальным объявлением
    time.sleep(1)

    # Выбираем победителя
    winner = random.choice(filtered_members)
    winner_tag = winner["telegram"] if winner["telegram"] else f"{winner['first_name']} {winner['last_name']}"

    # Отправляем финальное сообщение
    bot.send_message(chat_id, f"🎉 Победитель — {winner_tag}! Он(а) выиграл(а) пиво! 🍺")


@bot.message_handler(commands=['faculty', 'факультет'])
def filter_by_faculty(message):
    faculty_name = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ''
    filtered_members = [member for member in members if member["faculty"].lower() == faculty_name.lower()]
    
    if not filtered_members:
        bot.reply_to(message, "Никого не найдено на этом факультете.")
        return
    
    response = "Активисты КВС с факультета {}:\n".format(faculty_name)
    for member in filtered_members:
        response += "{} {} ({})\n".format(
            member["first_name"], member["last_name"], member["group"]
        )
    
    bot.reply_to(message, response)
    

def get_zodiac_sign(day, month):
    zodiac_dates = [
        ((1, 20), (2, 18), "Водолей"),
        ((2, 19), (3, 20), "Рыбы"),
        ((3, 21), (4, 19), "Овен"),
        ((4, 20), (5, 20), "Телец"),
        ((5, 21), (6, 20), "Близнецы"),
        ((6, 21), (7, 22), "Рак"),
        ((7, 23), (8, 23), "Лев"),
        ((8, 24), (9, 22), "Дева"),
        ((9, 23), (10, 22), "Весы"),
        ((10, 23), (11, 21), "Скорпион"),
        ((11, 22), (12, 21), "Стрелец"),
        ((12, 22), (1, 19), "Козерог")
    ]
    for start, end, sign in zodiac_dates:
        if (month == start[0] and day >= start[1]) or (month == end[0] and day <= end[1]):
            return sign
    return "Неизвестный знак"

@bot.message_handler(commands=['zodiac', 'знак'])
def filter_by_zodiac(message):
    zodiac_name = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ''
    
    if zodiac_name.lower() == "водолея":
        lyrics = [
            "ВСЁ ОТДАЛА И НИ О ЧЁМ НЕ ЖАЛЕЮ",
            "ВСЁ ОТДАЛА И НИЧЕГО НЕ ОСТАЛОСЬ",
            "А РЯДОМ СТОЛЬКО ЧЕЛОВЕК ПОТЕРЯЛОСЬ",
            "Я ЭТИМ ЧУВСТВОМ УЖЕ ВЕК НЕ БОЛЕЮ",
            "ВСЁ ОТДАЛА И НИ О ЧЁМ НЕ ЖАЛЕЮ",
            "И ВОПРЕКИ ЛЕЧУ ВСЕМ АВТОПИЛОТАМ",
            "ЖИВУ НАЗЛО ГОРОСКОПАМ"
        ]
        for line in lyrics:
            bot.send_message(message.chat.id, line)
            time.sleep(7)
        return 
    
    filtered_members = []
    
    for member in members:
        day, month, _ = map(int, member["birth_date"].split('.'))
        if get_zodiac_sign(day, month).lower() == zodiac_name.lower():
            filtered_members.append(member)
    
    if not filtered_members:
        bot.reply_to(message, "Никого не найдено с таким знаком зодиака.")
        return
    
    response = "Активисты КВС со знаком зодиака {}:\n".format(zodiac_name)
    for member in filtered_members:
        response += "{} {} ({})\n".format(
            member["first_name"], member["last_name"], member["birth_date"]
        )
    
    bot.reply_to(message, response)
    
while True:
    try:
        bot.polling(none_stop=True, timeout=60)
    except KeyboardInterrupt:
        print("Бот остановлен вручную.")
        break  # Выходим из цикла, если нажато Ctrl + C
    except:
        print(f"Ошибка соединения")
        time.sleep(10)  # Ждём 10 секунд перед новым запуском